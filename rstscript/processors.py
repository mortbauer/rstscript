import os
import io
import sys
import ast
import abc
import meta
import traceback
import logging
import collections
import copy
import getopt

import rstscript
from . import hunks

logger = logging.getLogger('rstscript.process')

class PluginBase(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def name(self):
        pass
    @property
    @abc.abstractmethod
    def short_options(self):
        pass
    @property
    @abc.abstractmethod
    def long_options(self):
        pass
    @property
    @abc.abstractmethod
    def defaults(self):
        pass
    @classmethod
    def register(self):
        if ('__abstractmethods__' in self.__dict__ and
                len(self.__dict__['__abstractmethods__'])>0):
            raise rstscript.RstscriptException('{0} "{1}" from module "{2}"'
            'is abstract, disabling it'
            .format(self.plugtype,self.name,self.__module__))
            return False
        else:
            if not hasattr(self.plugins,self.name):
                self.plugins[self.name] = self
                logger.info('registered {0} "{1}" from module "{2}"'.
                        format(self.plugtype,self.name,self.__module__))
            else:
                raise rstscript.RstscriptException('{0} "{1}" module file "{2}" is '
                'already registered,no effect'.
                format(self.plugtype,self.name,self.__module__))
            return True
    @abc.abstractmethod
    def process(self):
        pass
    @classmethod
    def make_parser(cls,defaults):
        opts = copy.deepcopy(cls.defaults)
        def parser(largs,linenumber=0):
            try:
                tuples = getopt.getopt(largs,cls.short_options,cls.long_options)
                if len(tuples[1]):
                    logger.warning('unhandeled argument "{0}" in linenumber "{1}"'.format(tuples[1],linenumber))
                opts.update([(x[0].strip('-'),x[1] if x[1] else True) for x in tuples[0]])
            except getopt.GetoptError as e:
                logger.warning('{0} in line "{1}"'.format(e,linenumber))
            return opts
        opts.update(parser(defaults))
        return parser

class LitVisitor(ast.NodeTransformer):
    """ special ast visitor, parses code chunks from string into single code
    objects do not set maxdepth bigger than 1, except you know what you do, but
    probaly the compilation will fail"""

    def __init__(self,maxdepth=1):
        self.maxdepth = maxdepth
        self.CodeChunk = collections.namedtuple('CodeChunk',['codeobject','source','assign'])

    def _autoprint(self,node):
        # implement autoprinting discovery
        if type(node) == ast.Assign:
            # test if simple assignement or trough some expression
            bmc = []
            for x in ast.iter_child_nodes(node):
                if not type(x) in (ast.Name,ast.Num,ast.Str):
                    bmc.append(x)
            if len(bmc)>0:
                return node.targets[0].id

    def _compile(self,node,start_lineno):
        # fix linenumber, so it represents linenumber of original file
        node.lineno = node.lineno + start_lineno
        codeobject = compile(ast.Module([node]),"<rstscript.dynamic>",'exec')
        source = meta.asttools.dump_python_source(node)
        auto = self._autoprint(node)
        return self.CodeChunk(codeobject,source,auto)

    def visit(self, node, start_lineno, depth=0):
        """Visit a node."""

        if depth >= self.maxdepth:
            yield self._compile(node,start_lineno)
        else:
            depth += 1
            for child in ast.iter_child_nodes(node):
                yield from self.visit(child,start_lineno,depth=depth)

class BaseProcessor(PluginBase):
    plugtype = 'processor'
    plugins = {}


class PythonProcessor(BaseProcessor):
    name = 'python'
    short_options = 'a'
    long_options = ['autofigure']
    defaults = {'a':False,'autofigure':False}

    def __init__(self,appoptions):
        self.init = True
        self.globallocal = {}
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.traceback = io.StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr
        self.visitor = LitVisitor()
        self.options = appoptions
        self.plt = False

    def get_figdir(self):
        """ to easily create the figdir on the fly if needed"""
        if not os.path.exists(self.options['figdir']):
            os.mkdir(self.options['figdir'])
        return self.options['figdir']

    def execute(self,codechunk,options):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.stdout.seek(0)
        self.stderr.seek(0)
        self.traceback.seek(0)
        try:
            exec(codechunk.codeobject,self.globallocal,self.globallocal)
        except:
            tr = traceback.format_exc().strip()
            # remove all line until a line containing rstscript.dynamic except
            # the first
            st = tr.find('\n')+1
            en = tr.find('File "<rstscript.dynamic>"')
            self.traceback.write(tr[:st])
            self.traceback.write(tr[en:])
            logger.warning('failed on line {0} with {1}'.
                    format(codechunk.codeobject.co_firstlineno,tr[tr.rfind('\n')+1:]))
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
        self.stdout.truncate()
        self.stderr.truncate()
        yield hunks.CodeIn(codechunk.source)
        yield hunks.CodeStdErr(self.stderr.getvalue())
        yield hunks.CodeTraceback(self.traceback.getvalue())
        yield hunks.CodeStdOut(self.stdout.getvalue())
        # for autoprinting
        if codechunk.assign:
            coa = codechunk.assign
            try:
                yield hunks.CodeResult('{0} = {1}'.format(coa,self.globallocal[coa]))
            except KeyError:
                pass

        #return hunks.CHunk(cs,coo,cout,ce,ct,self.globallocal)

    def _saveallfigures(self,label,desc):
        if not self.plt:
            try:
                import matplotlib.pyplot
                self.plt = matplotlib.pyplot
            except:
                raise rstscript.RstscriptException('you need matplotlib for using autofigure')
        for num in self.plt.get_fignums():
            fig = self.plt.figure(num)
            name = '{0}_{1}.png'.format(label,num)
            figpath =os.path.join(self.get_figdir(),name)
            fig.savefig(figpath)
            yield hunks.Figure(figpath,label=os.path.splitext(name)[0],desc=desc)

    def process(self,chunk):
        tree = ast.parse(chunk.raw)
        lhunks = []
        for codechunk in self.visitor.visit(tree,chunk.lineNumber):
            for hunk in self.execute(codechunk,chunk.pre_args[1]):
                # test if hunk is empty or not, only append not empty
                if hunk.simple:
                    lhunks.append(hunk)
        # autosave figures
        if chunk.pre_args[1]['autofigure']:
            try:
                label = '{0}_{1}'.format(chunk.post_args[1]['label'],chunk.number)
                for fig in self._saveallfigures(label,
                        chunk.post_args[1]['desc']):
                    lhunks.append(fig)
                self.plt.close('all')
            except Exception as e:
                logger.error('couldn\'t save figure, Exception {0}'.format(e))

        yield hunks.CChunk(chunk,lhunks)

class BaseFormatter(PluginBase):
    plugtype = 'formatter'
    plugins = {}


class CompactFormatter(BaseFormatter):
    name = 'compact'
    short_options = 'aesl'
    long_options = ['autofigure','label=','desc=']
    defaults = {'a':False,'e':True,'s':False,'l':False,
            'autofigure':False,'label':'','desc':''}

    def _decide(self,hunk,options):
        # needs to stay on top to silence output
        if options.setdefault('s',False):
            if type(hunk)==hunks.CodeTraceback:
                return hunk
            else:
                return hunks.Empty()
        if type(hunk)==hunks.CodeResult:
            if options.setdefault('a',False):
                return hunk
        elif type(hunk)==hunks.CodeIn:
            if options.setdefault('e',False):
                return hunk
        else:
            return hunk
        # if not previously returned return now empty hunk
        return hunks.Empty()

    def process(self,cchunk,options):
        i = 0
        for hunk in cchunk.hunks:
            if i == 0:
                yield self._decide(hunk,options).formatted
            else:
                yield self._decide(hunk,options).simple
            i += 1

