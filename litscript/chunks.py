from io import StringIO
import re
import pdb
import argparse
import collections
import shlex
from .colorlog import getlogger
from . import process
from . import hunks

__all__ = ['read','pre_process','process','post_process', 'write']

logger = getlogger('litscript.chunks')

def make_preparser():
    return preparser,processor


def optionparser(optionstring,default_subcommand=''):
    """ parses a string containing options into a dict
    Reference: http://stackoverflow.com/a/12013711/1607448
    """
    args = shlex.split(optionstring)
    options = {}
    if not args[0].startswith('-'):
        options['command'] = args[0]
        args = args[1:]
    else:
        options['command'] = default_subcommand

    skip = False
    for x,y in zip(args, args[1:]+["--"]):
        if skip:
            skip = False
            continue
        else:
            if y.startswith('-') and x.startswith('-'):
                options[x] = True
                skip = False
            elif x.startswith('-'):
                options[x] = y
                skip = True
            else:
                skip = False
                logger.error('invalid options {0}'.format(optionstring))
    return options

def testoptions(options,knownoptions):
    for opt in options:
        if not opt in knownoptions:
            logger.error('option "{0}" is unhandled'.format(opt))

class Litrunner(object):
    def __init__(self):
        self.processorClasses = {}
        self.processors = {}
        self.formatters = {}
        # setup chunk pre parser
        self.preparser = argparse.ArgumentParser()
        self.pre_subparser = self.preparser.add_subparsers(dest='processor')
        self.preparser.set_defaults(processor='python')
        self.preparser.add_argument('-e','--echo',action='store_true',help='echoes the commands')
        # setup chunk post parser
        self.postparser = argparse.ArgumentParser()
        self.postparser.set_defaults(formatter='compact')
        self.post_subparser = self.postparser.add_subparsers(dest='formatters')
        #self.subparserformatter = self.postparser.add_subparsers(dest='formatter')
        self.postparser.add_argument('-l','--label',help='label of the chunk')

    def init_processor(self,name):
        self.processors[name] = self.processorClasses[name]()

    def register_processor(self,ProcessorClass):
        # maybe a bit unusual, but seems to work
        if not ProcessorClass.name in self.pre_subparser.choices:
            self.pre_subparser.choices[ProcessorClass.name] = ProcessorClass.parser
            self.processorClasses[ProcessorClass.name] = ProcessorClass
        else:
            logger.error('processor "{0}" already known'.format(ProcessorClass.name))

    def register_formatter(self,FormatterClass):
        # maybe a bit unusual, but seems to work
        if not FormatterClass.name in self.post_subparser.choices:
            self.post_subparser.choices[FormatterClass.name] = FormatterClass.parser
            self.formatters[FormatterClass.name] = FormatterClass()
        else:
            logger.error('processor "{0}" already known'.format(FormatterClass.name))

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
            content.truncate()
            chunk = Chunk(number,linenumber,chunktype,pre,post,content.getvalue())
            content.seek(0)
            logger.info(chunk)
            return chunk

        def get_pre_param(line):
            """ get chunk pre arguments """
            return self.preparser.parse_args(shlex.split(line))

        def get_post_param(line):
            """ get chunk post arguments """
            return self.postparser.parse_args(shlex.split(line))

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
                if not chunk.pre_args.processor in self.processors:
                    self.init_processor(chunk.pre_args.processor)
                processor = self.processors[chunk.pre_args.processor]
                for cchunk in processor.process(chunk):
                    yield cchunk
            elif chunk.type == 'text':
                yield hunks.CChunk(chunk,chunk.raw,None,None,None,None,None)
            else:
                logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def format(self,cchunks):
        for cchunk in cchunks:
            formatter = self.formatters[cchunk.chunk.post_args.formatter]
            yield from formatter.format(cchunk)

def post_process(fileobject,procs_avail):
    proc_name = ''
    proc_ = None
    procs_init = {}
    for chunk in fileobject:
        if chunk['type'] != 'code':
            chunk['content_out'] = chunk['content_raw']
            proc_ = None
        elif chunk['type'] == 'code':
            if chunk['post_args']['post'] != proc_name:
                proc_name = chunk['post_args']['post']
            if not proc_ in procs_init:
                try:
                    procs_init[proc_name] = procs_avail[proc_name]()
                    proc_ = procs_init[proc_name].process
                except KeyError as e:
                    raise e
            else:
                proc_ = procs_init[proc_name].process

            #try:
                #chunk['content_out'] = proc_(chunk)
            #except Exception as e:
                #raise e
        chunk['post_processor'] = proc_
        yield chunk


def write(fileobject_in, fileobject_out):
    for chunk in fileobject_in:
        if chunk['post_processor'] != None:
            chunk['post_processor'](chunk,fileobject_out)
        else:
            fileobject_out.write(chunk['content_out'].getvalue())

