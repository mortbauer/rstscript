import os
import argparse
import collections
import shlex
import pprint
import logging
from io import StringIO

from . import hunks
from . import processors


__all__ = ['read','pre_process','processors','post_process', 'write']

logger = logging.getLogger('rstscript.litrunner')

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

    def __init__(self,app_options) :
        self.processorClasses = {}
        self.processors = {}
        self.formatters = {}
        self.preargparser = {}
        self.postargparser = {}
        self.options = app_options
        # register all loaded plugins, at least try it
        for processor in processors.BaseProcessor.plugins.values():
            self.register_processor(processor)
        for formatter in processors.BaseFormatter.plugins.values():
            self.register_formatter(formatter)

    def get_figdir(self):
        """ to easily create the figdir on the fly if needed"""
        if not os.path.exists(self.figdir):
            os.mkdir(self.figdir)
        return self.figdir

    def get_processor(self,name):
        if name in self.processorClasses:
            if not name in self.processors:
                self.processors[name] = self.processorClasses[name](self.options)
                logger.info('instantiated processor "{0}"'.format(name))
            return self.processors[name].process
        else:
            logger.error('there is no processor named "{0}",'
            'i will try the default one'.format(name))
            dname = self.def_proc
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
            self.preargparser[ProcessorClass.name] = ProcessorClass.make_parser(self.options.proc_args)
        else:
            logger.error('processor "{0}" already known'.format(ProcessorClass.name))

    def register_formatter(self,FormatterClass):
        # maybe a bit unusual, but seems to work
        if not FormatterClass.name in self.postargparser:
            self.formatters[FormatterClass.name] = FormatterClass()
            self.postargparser[FormatterClass.name] = FormatterClass.make_parser(self.options.form_args)
        else:
            logger.error('processor "{0}" already known'.format(FormatterClass.name))

    def test_readiness(self):
        if not self.options.processor in self.processorClasses:
            logger.error('command "{0}", set as default command is unknown,'
                    'won\'t do anything'.format(self.options.processor))
            return False
        if not self.options.formatter in self.formatters:
            logger.error('command "{0}", set as default formatter is unknown,'
                    'won\'t do anything'.format(self.options.formatter))
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
        Chunk = collections.namedtuple('Chunk', ['number','lineNumber',
            'type','pre_args','post_args','raw'])

        def buildchunk(number,linenumber,chunktype,pre,post,content):
            content.truncate()
            chunk = Chunk(number,linenumber,chunktype,pre,post,content.getvalue())
            content.seek(0)
            logger.info(chunk)
            return chunk

        def get_param(line,parsers,def_command,linen):
            unparsed = shlex.split(line)
            if len(unparsed):
                if unparsed[0][0] != '-':
                    lcommand = unparsed[0]
                    if lcommand in parsers:
                        parsed = parsers[lcommand](unparsed[1:],linen)
                        return lcommand,parsed
                    else:
                        logger.error('there is no processor named "{0}" '
                        'specified in line "{1}"'.format(lcommand,linen))
                else:
                    parsed = parsers[def_command](unparsed,linen)
                    return def_command,parsed
            return def_command,parsers[def_command]([],linen)

        def get_pre_param(line,linen):
            return get_param(line,self.preargparser,self.options.processor,linen)

        def get_post_param(line,linen):
            return get_param(line,self.postargparser,self.options.formatter,linen)

        for line in fileobject:
            line_start = line[:token_length]

            # on start of chunk delimiter yield text
            if line_start == chunk_start:
                if content.tell() != 0:
                    yield buildchunk(chunkn,linechunk,'text',None,None,content)
                pre_a = get_pre_param(line[token_length:],linecounter)
                delimtercounter += 1
                linechunk = linecounter
                chunkn += 1
            # on end of chunk delimiter yield code
            elif line_start == chunk_end:
                if content.tell() != 0:
                    post_a = get_post_param(line[token_length:],linecounter)
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
        """ takes the unprocessed chunks, how the reader chunks them, only
        needs information if the chunk is code or text, so minimal processing
        before. It writes the code chunks unchanged to the tangle output file
        and  yields the same chunks coming in unchanged."""
        for chunk in chunks:
            if chunk.type == 'code':
                self.options.toutput.write(chunk.raw)
            elif chunk.type == 'text':
                pass
            else:
                logger.error('unsupported chunk type {0}'.
                        format(chunk.type))
            yield chunk

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


    def run(self):
        if not self.test_readiness():
            logger.error('can\'t start to run, provide propper options')
            return False
        logger.info('Run Litrunner with options "{0}"'.
                format(pprint.pformat(vars(self.options))))
        if not self.options.noweave and not self.options.tangle:
            logger.info('starting to weave the document')
            # self.options.input is a list of open files returned by argparse,
            # maybe should be changed in the future
            for formatted in self.format(self.weave(self.read(self.options.input[0]))):
                self.options.woutput.write(formatted)
        elif not self.options.noweave and self.options.tangle:
            logger.info('starting to weave and tangle the document')
            for formatted in self.format(self.weave(self.tangle(self.read(self.options.input[0])))):
                self.options.woutput.write(formatted)
        elif self.options.noweave and self.options.tangle:
            logger.info('starting to tangle the document')
            for formatted in self.tangle(self.read(self.options.input[0])):
                pass
        else:
            logger.info('no job specified, don\'t do anything')

        return True

