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
        self.formatterClasses = {}
        self.formatters = {}
        self.options = app_options
        self.logger = logger
        self.defaults = self.set_defaults()
        self.register_plugins()
        self.woutput = StringIO()
        # set up a memory of chunks
        self.chunks = []

    def openfiles(self):
        try:
            self.input = open(self.options['input'],'r')
            if self.options['toutput']:
                self.toutput = open(self.options['toutput'],'w')
            if not self.options['noweave']:
                self.woutput.seek(0)
            return True
        except Exception as e:
            self.logger.warn(e)
            return False

    def closefiles(self):
        try:
            self.input.close()
            if self.options['toutput']:
                self.toutput.close()
            if not self.options['noweave']:
                with open(self.options['woutput'],'w') as f:
                    f.write(self.woutput.getvalue())
            return True
        except Exception as e:
            self.logger.warn(e)
            return False

    def set_defaults(self):
        try:
            if 'options' in self.options and self.options['options']:
                return self.options['options']
            else:
                return {}
        except Exception as e:
            self.logger.warn('default chunk options "{0}" are invalid "{1}"'
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
        if not FormatterClass.name in self.formatterClasses:
            self.formatterClasses[FormatterClass.name] = FormatterClass
        else:
            self.logger.error('formatter "{0}" already known'.format(FormatterClass.name))

    def get_processor(self,name):
        if name in self.processorClasses:
            if not name in self.processors:
                self.processors[name] = self.processorClasses[name](
                        self.options,self.logger)
                self.logger.info('instantiated processor "{0}"'.format(name))
            return self.processors[name].process
        else:
            self.logger.error('there is no processor named "{0}",'
            'i will skip the chunk'.format(name))

    def get_formatter(self,name):
        if name in self.formatterClasses:
            if not name in self.formatters:
                self.formatters[name] = self.formatterClasses[name](
                        self.options,self.logger)
                self.logger.info('instantiated formatter "{0}"'.format(name))
            return self.formatters[name].process
        else:
            self.logger.error('there is no formatter named "{0}",'
            'i will skip the chunk'.format(name))

    def read(self,fileobject,start='%<',end='%>',comment='%%'):
        """This function returns a generator
        It produces pieces from a fileobject, delimited with *chunk_start* and
        *chunk_end* tokens.
        """

        if len(start) != len(end) != len(comment):
            raise RstscriptException('start end end tokens must have equal length')

        #: holder of real content
        content = StringIO()
        #: counter for trvial error checking
        delimtercounter = 0
        #: informational counter
        chunkn = 0
        #: line number of chunk start
        linecounter = 1
        linen_of_chunkstart = linecounter
        #: delimiter, and escaped delimiters
        token_length = len(start)

        def same(chunkn,content):
            chunkhash = hash(content.getvalue())
            if len(self.chunks) > chunkn and self.chunks[chunkn][0] == chunkhash:
                return True
            elif len(self.chunks) > chunkn:
                self.chunks = self.chunks[:chunkn] # reset all further chunks
                self.chunks.append([chunkhash,-1])
                return False
            else:
                self.chunks.append([chunkhash,-1])
                return False

        def buildchunk(number,linenumber,chunktype,content):
            content.truncate()
            content.seek(0)
            if not same(number,content):
                if chunktype == 'code':
                    options = getoptions(content.readline().strip(),linenumber)
                    raw = content.read()
                    if hasattr(self,'toutput'):
                        self.toutput.write(raw)
                else:
                    raw = content.read()
                    options = {}
                chunk = Chunk(number,linenumber,chunktype,options,raw)
                content.seek(0)
                self.logger.info(chunk)
                yield chunk
            else:
                # tangling doens't care about caching
                if self.options['toutput']:
                    # skip options
                    if chunktype == 'code':
                        content.readline()
                        self.toutput.write(content.read())
                content.seek(0)
                self.logger.info('chunk "{0}" is unchanged'.format(number))

        def getoptions(line,linenumber):
            try:
                if line:
                    d = ujson.loads(line)
                    for key in self.defaults:
                        d.setdefault(key,self.defaults[key])
                    self.logger.info(d)
                    return d
                else:
                    return self.defaults
            except Exception as e:
                self.logger.warn('couldn\'t parse options {2} in line "{0}", "{1}"'
                        .format(linenumber,e,repr(line.strip())))
                return self.defaults

        for line in fileobject:
            line_start = line[:token_length]
            # on start of chunk delimiter yield text
            if line_start == start:
                if content.tell() != 0:
                    yield from buildchunk(chunkn,linen_of_chunkstart,'text',content)
                delimtercounter += 1
                linen_of_chunkstart = linecounter
                chunkn += 1
                content.write(line[token_length:])
            # on end of chunk delimiter yield code
            elif line_start == end:
                if content.tell() != 0:
                    yield from buildchunk(chunkn,linen_of_chunkstart,'code',content)
                delimtercounter -= 1
                linen_of_chunkstart = linecounter + 1
                chunkn += 1
            # remove the comment
            elif line_start == comment:
                content.write(line[token_length:])
            else:
                content.write(line)

            # delimiter counter is 0 in text chunks and 1 in code chunks
            # if it is smaller or bigger it must be an error
            if delimtercounter > 1 or delimtercounter < 0:
                msg = 'missing delimiter before line {}'
                raise GeneratorExit(msg.format(linecounter))

            linecounter += 1

        if content.tell() != 0:
            yield from buildchunk(chunkn,linen_of_chunkstart,'text',content)

    def weave(self,chunks):
        for chunk in chunks:
            if chunk.type == 'code':
                processor = self.get_processor(
                        chunk.options.get('proc',self.options.get('proc','python')))
                if processor:
                    for cchunk in processor(chunk):
                        yield cchunk
            elif chunk.type == 'text':
                yield processors.CChunk(chunk,[hunks.Text(chunk.raw)])
            else:
                self.logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def format(self,cchunks):
        for cchunk in cchunks:
            if cchunk.chunk.type == 'code':
                formatter = self.get_formatter(
                        cchunk.chunk.options.get('form',self.options.get('form','compact')))
                if formatter:
                    yield from formatter(cchunk)
            elif cchunk.chunk.type == 'text':
                yield cchunk.chunk.number,[cchunk.hunks[0].formatted]
            else:
                self.logger.error('unsupported chunk type {0}'.
                        format(chunk.type))

    def run(self):
        if self.openfiles():
            try:
                self.logger.info('Run Litrunner with options "{0}"'.
                        format(pprint.pformat(self.options)))

                if not self.options['noweave']:
                    for chunkn,formatted in self.format(self.weave(self.read(self.input))):
                        if chunkn > 0 and self.chunks[chunkn-1][1] > 0:
                            self.woutput.seek(self.chunks[chunkn-1][1])
                        for hunk in formatted:
                            self.woutput.write(hunk)
                            self.chunks[chunkn][1] = self.woutput.tell()
                    if self.woutput.tell():
                        self.woutput.truncate()
                elif self.options['noweave'] and self.options['toutput']:
                    for formatted in self.read(self.input):
                        pass
                else:
                    self.logger.warn('no job specified, don\'t do anything')
                self.closefiles()
                return True
            except Exception as e:
                self.logger.error(e)
                self.closefiles()
                raise e
                return False
        else:
            return False


class LitServer(object):
    def __init__(self,logger):
        self.projects = {}
        self.logger = logger

    def run(self,data,logger=None):
        if not logger:
            logger = self.logger
        # test if project is new
        try:
            project_id = (data['input'],data['woutput'],data['toutput'])
        except KeyError:
            logger.error('there needs to be at least the "input" key in the data')
        # do the work
        try:
            if project_id in self.projects and not data.get('rebuild',False):
                # test if default options changed
                if self.projects[project_id].options['options'] != data['options']:
                    self.projects[project_id] = Litrunner(data,logger)
                else:
                    # the logger needs to be renewed, has info from old thread
                    # and so on
                    self.projects[project_id].logger = logger
            else:
                # completely new
                self.projects[project_id] = Litrunner(data,logger)
            # now run the project
            self.projects[project_id].run()
        except Exception as e:
            logger.error('an unexpected error occured "{0}"'.format(e))
        finally:
            pass
        return ['done',{}]
