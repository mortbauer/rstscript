import os
import argparse
import collections
import shlex
import logging
from io import StringIO
from . import hunks

__all__ = ['read','pre_process','processors','post_process', 'write']

logger = logging.getLogger('litscript.chunks')

class Litrunner(object):
    """ Litrunner main Class
    The following needs to be done in order to run it correct

    * instantiate it
    * register some processors ``register_processor``
    * register some formatters ``register_formatter``
    * set default processor and formatter with their options ``set_defaults``
    * test if conditions seem to be good `` test_readiness``, if it returns
      ``False`` the you provided bullshit.

    Now it should be fine to read or do whatever.
    """

    def __init__(self,options={}) :
        self.processorClasses = {}
        self.processors = {}
        self.formatters = {}
        self.preargparser = {}
        self.postargparser = {}
        self.options = options
        self.parser = argparse.ArgumentParser('litscript.chunks')
        self.parser.add_argument('command')

    def get_figdir(self):
        """ to easily create the figdir on the fly if needed"""
        if not os.path.exists(self.figdir):
            os.mkdir(self.figdir)
        return self.figdir

    def get_processor(self,name):
        if name in self.processorClasses:
            if not name in self.processors:
                self.processors[name] = self.processorClasses[name]()
                logger.info('instantiated processor "{0}"'.format(name))
            return self.processors[name].process
        else:
            logger.error('there is no processor named "{0}",'
            'i will try the default one'.format(name))
            dname = self.default_pre_command
            if not dname in self.processors:
                self.processors[dname] = self.processorClasses[dname]()
                logger.info('instantiated processor "{0}"'.format(dname))
            return self.processors[dname].process

    def get_formatter(self,name):
        return self.formatters[name].process

    def register_processor(self,ProcessorClass):
        # maybe a bit unusual, but seems to work
        if not ProcessorClass.name in self.processorClasses:
            self.processorClasses[ProcessorClass.name] = ProcessorClass
            self.preargparser[ProcessorClass.name] = ProcessorClass.parser
        else:
            logger.error('processor "{0}" already known'.format(ProcessorClass.name))

    def register_formatter(self,FormatterClass):
        # maybe a bit unusual, but seems to work
        if not FormatterClass.name in self.postargparser:
            self.postargparser[FormatterClass.name] = FormatterClass.parser
            self.formatters[FormatterClass.name] = FormatterClass()
        else:
            logger.error('processor "{0}" already known'.format(FormatterClass.name))

    def set_defaults(self,pre_command,pre_options,post_command,post_options):
        self.default_pre_command = pre_command
        self.default_pre_options = vars(self.preargparser[pre_command].parse_args(pre_options))
        self.default_post_command = post_command
        self.default_post_options = vars(self.postargparser[post_command].parse_args(post_options))

    def test_readiness(self):
        if not self.default_pre_command in self.processorClasses:
            logger.error('command "{0}", set as default command is unknown,'
                    'won\'t do anything'.format(self.default_pre_command))
            return False
        if not self.default_post_command in self.formatters:
            logger.error('command "{0}", set as default formatter is unknown,'
                    'won\'t do anything'.format(self.default_post_command))
            return False
        return True

    def read(self,fileobject):
        """This function returns a generator
        It produces pieces from a fileobject, delimited with *chunk_start* and
        *chunk_end* tokens.
        """

        #: holder of real content
        content = StringIO()
        #: counter for trvial error checking
        delimtercounter = 0
        #: informational counter
        chunkn = 0
        #: line number of chunk start
        linecounter = 1
        linechunk = linecounter
        #: delimiter, and escaped delimiters
        chunk_start = '%<<'
        chunk_end = '%>>'
        token_length = 3

        # fast way to store the info
        Chunk = collections.namedtuple('Chunk', ['number','lineNumber','type','pre_args','post_args','raw'])

        def buildchunk(number,linenumber,chunktype,pre,post,content):
            logger = logging.getLogger('litscript.chunks.read.buildchunk')
            content.truncate()
            chunk = Chunk(number,linenumber,chunktype,pre,post,content.getvalue())
            content.seek(0)
            logger.info(chunk)
            return chunk

        def get_pre_param(line):
            args,rargs = self.parser.parse_known_args(line)
            if args.command in self.preargparser:
                opts = self.preargparser[args.command].parse_args(rargs)
                return args.command,opts
            else:
                return self.default_pre_command,self.default_pre_options
        def get_post_param(line):
            args,rargs = self.parser.parse_known_args(line)
            if args.command in self.postargparser:
                opts = self.postargparser[args.command].parse_args(rargs)
                return args.command,opts
            else:
                return self.default_post_command,self.default_post_options

        for line in fileobject:
            line_start = line[:token_length]

            # on start of chunk delimiter yield text
            if line_start == chunk_start:
                if content.tell() != 0:
                    yield buildchunk(chunkn,linechunk,'text',None,None,content)
                pre_a = get_pre_param(line[token_length:])
                delimtercounter += 1
                linechunk = linecounter
                chunkn += 1
            # on end of chunk delimiter yield code
            elif line_start == chunk_end:
                if content.tell() != 0:
                    post_a = get_post_param(line[token_length:])
                    yield buildchunk(chunkn,linechunk,'code',pre_a,post_a,content)
                delimtercounter -= 1
                linechunk = linecounter + 1
                chunkn += 1
            # normal
            else:
                content.write(line)

            if delimtercounter > 1 or delimtercounter < 0:
                msg = 'missing delimiter before line {}'
                raise GeneratorExit(msg.format(linecounter))

            linecounter += 1

        content.truncate()
        if content.tell() != 0:
            yield buildchunk(chunkn,linechunk,'text',None,None,content)


    def weave(self,chunks):
        for chunk in chunks:
            if chunk.type == 'code':
                processor = self.get_processor(chunk.pre_args[0])
                for cchunk in processor(chunk):
                    yield cchunk
            elif chunk.type == 'text':
                yield hunks.CChunk(chunk,[hunks.Text(chunk.raw)])
            else:
                logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def tangle(self,chunks):
        for chunk in chunks:
            if chunk.type == 'code':
                yield chunk.raw
            elif chunk.type == 'text':
                continue
            else:
                logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def format(self,cchunks):
        for cchunk in cchunks:
            if cchunk.chunk.type == 'code':
                formatter = self.get_formatter(cchunk.chunk.post_args[0])
                yield from formatter(cchunk,cchunk.chunk.post_args[1])
            elif cchunk.chunk.type == 'text':
                yield cchunk.hunks[0].formatted
            else:
                logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

