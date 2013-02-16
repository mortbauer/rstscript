import os
import ujson
import collections
import pprint
from io import StringIO

from . import hunks
from . import processors

Chunk = collections.namedtuple('Chunk',
        ['number','lineNumber', 'type','options','raw'])

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

    def __init__(self,app_options,logger) :
        self.processorClasses = {}
        self.processors = {}
        self.formatters = {}
        self.options = app_options
        self.logger = logger
        self.defaults = self.set_defaults()
        self.logger.info(self.defaults)
        self.register_plugins()

    def set_defaults(self):
        try:
            if self.options['options']:
                return ujson.loads(self.options['options'])
            else:
                return {}
        except Exception as e:
            self.logger.warning('default chunk options "{0}" are invalid "{1}"'
                    .format(self.options['options'],e))
            return {}

    def register_plugins(self):
        # register all loaded plugins, at least try it
        for processor in processors.BaseProcessor.plugins.values():
            self.register_processor(processor)
        for formatter in processors.BaseFormatter.plugins.values():
            self.register_formatter(formatter)

    def register_processor(self,ProcessorClass):
        # maybe a bit unusual, but seems to work
        if not ProcessorClass.name in self.processorClasses:
            self.processorClasses[ProcessorClass.name] = ProcessorClass
        else:
            self.logger.error('processor "{0}" already known'.format(ProcessorClass.name))

    def register_formatter(self,FormatterClass):
        # maybe a bit unusual, but seems to work
        if not FormatterClass.name in self.formatters:
            self.formatters[FormatterClass.name] = FormatterClass()
        else:
            self.logger.error('formatter "{0}" already known'.format(FormatterClass.name))

    def get_processor(self,name):
        if name in self.processorClasses:
            if not name in self.processors:
                self.processors[name] = self.processorClasses[name](self.options)
                self.logger.info('instantiated processor "{0}"'.format(name))
            return self.processors[name].process
        else:
            self.logger.error('there is no processor named "{0}",'
            'i will skip the chunk'.format(name))
            return self.processors['none'].process

    def get_formatter(self,name):
        if name in self.formatters:
            return self.formatters[name].process
        else:
            self.logger.error('there is no formatter named "{0}",'
            'i will try the default one, will skip the chunk'.format(name))
            return self.formatters['none'].process

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

        def buildchunk(number,linenumber,chunktype,options,content):
            content.truncate()
            chunk = Chunk(number,linenumber,chunktype,options,content.getvalue())
            content.seek(0)
            self.logger.info(chunk)
            return chunk

        def getoptions(line,linenumber):
            try:
                if line.strip():
                    d = ujson.loads(line.strip())
                    for key in self.defaults:
                        d.setdefault(key,self.defaults[key])
                    self.logger.info(d)
                    return d
                else:
                    return self.defaults
            except Exception as e:
                self.logger.warning('couldn\'t parse options {2} in line "{0}", "{1}"'
                        .format(linenumber,e,repr(line.strip())))
                return self.defaults

        options = {}
        for line in fileobject:
            line_start = line[:token_length]

            # on start of chunk delimiter yield text
            if line_start == chunk_start:
                if content.tell() != 0:
                    yield buildchunk(chunkn,linechunk,'text',{},content)
                options = getoptions(line[token_length:],linecounter)
                delimtercounter += 1
                linechunk = linecounter
                chunkn += 1
            # on end of chunk delimiter yield code
            elif line_start == chunk_end:
                if content.tell() != 0:
                    yield buildchunk(chunkn,linechunk,'code',options,content)
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
            yield buildchunk(chunkn,linechunk,'text',{},content)


    def weave(self,chunks):
        for chunk in chunks:
            if chunk.type == 'code':
                processor = self.get_processor(
                        chunk.options.get('proc',self.options.get('proc','python')))
                for cchunk in processor(chunk):
                    yield cchunk
            elif chunk.type == 'text':
                yield processors.CChunk(chunk,[hunks.Text(chunk.raw)])
            else:
                self.logger.error('unsupported chunk type {0}'.

                        format(chunk.type))

    def tangle(self,chunks):
        """ takes the unprocessed chunks, how the reader chunks them, only
        needs information if the chunk is code or text, so minimal processing
        before. It writes the code chunks unchanged to the tangle output file
        and  yields the same chunks coming in unchanged."""
        for chunk in chunks:
            if chunk.type == 'code':
                self.toutput.write(chunk.raw)
            elif chunk.type == 'text':
                pass
            else:
                self.logger.error('unsupported chunk type {0}'.
                        format(chunk.type))
            yield chunk

    def format(self,cchunks):
        for cchunk in cchunks:
            if cchunk.chunk.type == 'code':
                formatter = self.get_formatter(
                        cchunk.chunk.options.get('form',self.options.get('form','compact')))
                yield from formatter(cchunk)
            elif cchunk.chunk.type == 'text':
                yield cchunk.hunks[0].formatted
            else:
                self.logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def run(self):
        self.logger.info('Run Litrunner with options "{0}"'.
                format(pprint.pformat(self.options)))

        self.input = open(self.options['input'],'r')
        if not self.options['noweave'] and not self.options['tangle']:
            self.woutput = open(self.options['woutput'],'w')
            self.logger.info('starting to weave the document')
            try:
                for formatted in self.format(self.weave(self.read(self.input))):
                    self.woutput.write(formatted)
            finally:
                self.woutput.close()
        elif not self.options['noweave'] and self.options['tangle']:
            self.woutput = open(self.options['woutput'],'w')
            self.toutput = open(self.options['toutput'],'w')
            self.logger.info('starting to weave and tangle the document')
            try:
                for formatted in self.format(self.weave(self.tangle(self.read(self.input)))):
                    self.woutput.write(formatted)
            finally:
                self.woutput.close()
                self.toutput.close()
        elif self.options['noweave'] and self.options['tangle']:
            self.toutput = open(self.options['toutput'],'w')
            self.logger.info('starting to tangle the document')
            try:
                for formatted in self.tangle(self.read(self.options['input'][0])):
                    pass
            finally:
                self.toutput.close()
        else:
            self.logger.info('no job specified, don\'t do anything')
        self.input.close()

        return True

