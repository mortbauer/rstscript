import os
import io
import sys
import ast
import abc
import ipdb
#import meta # not needed anymore
import traceback
import collections

import rstscript
from . import hunks
from .interactive import IPythonConnection

CChunk = collections.namedtuple('CChunk',['chunk','hunks'])

class PluginBase(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def name(self):
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
                #self.logger.info('registered {0} "{1}" from module "{2}"'.
                        #format(self.plugtype,self.name,self.__module__))
            else:
                raise rstscript.RstscriptException('{0} "{1}" module file "{2}" is '
                'already registered,no effect'.
                format(self.plugtype,self.name,self.__module__))
            return True
    @abc.abstractmethod
    def process(self):
        pass

# idea, second visitor for all childs above the magic level
# which just pulls in the source code



class LitVisitor(ast.NodeTransformer):
    """ special ast visitor, parses code chunks from string into single code
    objects do not set maxdepth bigger than 1, except you know what you do, but
    probaly the compilation will fail"""

    def __init__(self,inputfilename,logger,maxdepth=1):
        self.maxdepth = maxdepth
        self.inputfilename = inputfilename
        self.logger = logger
        self.CodeChunk = collections.namedtuple('CodeChunk',['codeobject','source','assign'])

    def _get_last_lineno(self,node):
        maxlineno = 0
        for x in ast.walk(node):
            if hasattr(x,'lineno') and x.lineno > maxlineno:
                maxlineno = x.lineno
        return maxlineno

    def _autoprint(self,node):
        # implement autoprinting discovery
        if type(node) == ast.Assign:
            # test if simple assignement or trough some expression
            bmc = []
            for x in ast.iter_child_nodes(node):
                if not type(x) in (ast.Name,ast.Num,ast.Str):
                    bmc.append(x)
            if len(bmc)>0:
                if hasattr(node.targets[0],'id'):
                    return node.targets[0].id
                #else:
                    #return node.targets[0]

    def _compile(self,node):
        # fix linenumber, so it represents linenumber of original file
        codeobject = compile(ast.Module([node]),"{0}".format(self.inputfilename),'exec')
        #source = meta.asttools.dump_python_source(node)
        auto = self._autoprint(node)
        return self.CodeChunk(codeobject,node.source,auto)

    def _detect_matplotlib(self,node):
        for modpart in node.module.split('.'):
            if modpart in ['pyplot','pylab','sympy']:
                if not 'matplotlib.pyplot' in sys.modules:
                    self.logger.info('detected "{0}" and imported matplotlib'
                    ' before to choose backend "Agg"'.format(modpart))
                    return self.CodeChunk(
                            compile('import matplotlib;matplotlib.use("Agg")',
                                '<rstscript.dynamic>','exec'),'','')
                else:
                    self.logger.info('detected import of matplotlib.pyplot, '
                    'but backend was already choosen')

    def visit_Import(self,node):
        newnode = self._detect_matplotlib(node)
        if newnode:
            yield newnode
        yield self._compile(node)


    def visit_ImportFrom(self,node):
        newnode = self._detect_matplotlib(node)
        if newnode:
            yield newnode
        yield self._compile(node)

    def visit(self, node, start_lineno,raw,depth=0):
        """Visit a node."""
        if depth >= self.maxdepth:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, None)
            # get source code of the node, must be before the next statement
            startline = node.lineno-1
            endline = self._get_last_lineno(node)
            node.source = '\n'.join(raw[startline:endline])
            #print('last line',self._get_last_lineno(node),'source',node.source)
            node.lineno = node.lineno + start_lineno
            if visitor:
                yield from visitor(node)
            else:
                yield self._compile(node)
        else:
            depth += 1
            for child in ast.iter_child_nodes(node):
                yield from self.visit(child,start_lineno,raw,depth=depth)

class BaseProcessor(PluginBase):
    plugtype = 'processor'
    plugins = {}

    def __init__(self,appoptions,logger):
        self.options = appoptions
        self.logger = logger


class NoneProcessore(BaseProcessor):
    name = 'none'

    def process(self,chunk):
        yield CChunk(chunk,[hunks.CodeIn(chunk.raw)])

class PythonProcessor(BaseProcessor):
    name = 'python'
    defaults = {'af':False}

    def __init__(self,appoptions,logger):
        super().__init__(appoptions,logger)
        self.globallocal = {}
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.traceback = io.StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr
        self.inputfilename = appoptions.get('input','')
        self.visitor = LitVisitor(self.inputfilename,logger=self.logger)
        self.plt = False
        self.init = True
        if appoptions.get('ipython_connection'):
            try:
                self.ipc = IPythonConnection(appoptions['ipython_connection'])
                self.logger.info('also executing to ipython kernel "{0}"'
                        .format(os.path.split(self.ipc.cf)[1]))
            except:
                self.logger.exception('failed to connect to ipython kernel '
                '"{0}"'.format(appoptions['ipython_connection']))
                self.ipc = None

        else:
            self.ipc = None

    def get_figdir(self):
        """ to easily create the figdir on the fly if needed"""
        if not os.path.exists(self.options['figdir']):
            os.mkdir(self.options['figdir'])
        return self.options['figdir']

    def execute(self,codechunk,chunkoptions):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.stdout.seek(0)
        self.stderr.seek(0)
        self.traceback.seek(0)
        try:
            exec(codechunk.codeobject,self.globallocal,self.globallocal)
            if self.ipc:
                try:
                    self.ipc.run_cell(codechunk.source)
                except:
                    self.logger.exception('failed to execute "{0}" on ipython'
                    ' kernel "{1}"'.format(
                        codechunk.source,os.path.split(self.ipc.cf)[0]))
        except:
            tr = traceback.format_exc().strip()
            # remove all line until a line containing rstscript.dynamic except
            # the first
            st = tr.find('\n')+1
            en = tr.find('File "{0}"'.format(self.inputfilename))
            self.traceback.write(tr[:st])
            self.traceback.write(tr[en:])
            self.logger.warn('failed on line {0} with {1}'.
                    format(codechunk.codeobject.co_firstlineno,tr[tr.rfind('\n')+1:]))
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
        self.stdout.truncate()
        self.stderr.truncate()
        yield hunks.CodeIn(codechunk.source)
        #print(codechunk.source)
        yield hunks.CodeStdErr(self.stderr.getvalue())
        self.stderr.seek(0)
        self.stderr.truncate()
        yield hunks.CodeTraceback(self.traceback.getvalue())
        self.traceback.seek(0)
        self.traceback.truncate()
        yield hunks.CodeStdOut(self.stdout.getvalue())
        self.stdout.seek(0)
        self.stdout.truncate()
        # for autoprinting
        if codechunk.assign:
            coa = codechunk.assign
            try:
                res = self.globallocal[coa]
            except:
                self.logger.warn('failed to autoprint "{0}"'.format(coa))
                res = None
            try:
                res = float(res)
                yield hunks.CodeResult('{0} = {1:.{2}f}'.
                        format(coa,res,chunkoptions.get('prec',3)))
            except:
                # test if it can printed with latex
                if hasattr(res,'atoms') and 'sympy' in sys.modules:
                    import sympy
                    yield hunks.CodeResult('{0} = {1}'.format(
                        coa,res.evalf(n=chunkoptions.get('prec',3))))
                    #yield hunks.MathBlock('{0} = {1}'.format(
                        #coa,sympy.latex(res.evalf(n=chunkoptions.get('prec',3)))))
                else:
                    #self.logger.info('type is {0}:{1}'.format(coa,type(res)))
                    yield hunks.CodeResult('{0} = {1}'.format(coa,res))

        #return hunks.CHunk(cs,coo,cout,ce,ct,self.globallocal)

    def _saveallfigures(self,options,number):
        if not self.plt:
            try:
                if not 'matplotlib.pyplot' in sys.modules:
                    import matplotlib
                    matplotlib.use('Agg')
                from matplotlib import pyplot
                self.plt = pyplot
                self.logger.info('imported matplotlib.pyplot')
            except:
                raise rstscript.RstscriptException('you need matplotlib for using autofigure')
        for num in self.plt.get_fignums():
            if num > 1:
                self.logger.error('there are several figures in this chunks, not supported so far')
            else:
                label = options.get('label',number).replace(' ','_') # whitespace can't behandeled by sphinx currently
                fig = self.plt.figure(num)
                name = '{0}.png'.format(label)
                figpath =os.path.join(self.get_figdir(),name)
                fig.savefig(figpath)
                self.logger.info('saved figure "{0}" to "{1}"'.format(label,figpath))
                # write only path relative to file, otherwise sphinx will complain
                yield hunks.Figure(os.path.relpath(figpath,
                    os.path.split(self.options['woutput'])[0]),label=label,
                        desc=options.get('desc',''),
                        width=options.get('width','100%'),
                        height=options.get('height'),
                        alt=options.get('alt',''))

    def process(self,chunk):
        tree = ast.parse(chunk.raw)
        lhunks = []
        for codechunk in self.visitor.visit(tree,chunk.lineNumber,chunk.raw.splitlines()):
            for hunk in self.execute(codechunk,chunk.options):
                # test if hunk is empty or not, only append not empty
                if hunk.simple:
                    lhunks.append(hunk)
        # autosave figures TODO
        if chunk.options.get('af',False):
            try:
                for fig in self._saveallfigures(chunk.options,chunk.number):
                    lhunks.append(fig)
                self.plt.close('all')
            except Exception as e:
                self.logger.error('couldn\'t save figure, Exception {0}'.format(e))

        yield CChunk(chunk,lhunks)

class BaseFormatter(PluginBase):
    plugtype = 'formatter'
    plugins = {}

    def __init__(self,appoptions,logger):
        self.options = appoptions
        self.logger = logger


class NoneFormatter(BaseFormatter):
    name = 'none'

    def process(self,cchunk):
        for hunk in cchunk.hunks:
            yield [hunk.simple for hunk in cchunk.hunks if hunk.simple]

class CompactFormatter(BaseFormatter):
    name = 'compact'
    defaults = {'a':False,'e':True,'s':False,'l':False,
            'label':'','desc':''}

    def _decide(self,hunk,options):
        # needs to stay on top to silence output
        if options.get('s',False):
            if type(hunk)==hunks.CodeTraceback:
                return hunk
            else:
                return hunks.Empty()
        if type(hunk)==hunks.CodeResult:
            if options.get('a',False):
                return hunk
        elif type(hunk)==hunks.CodeIn:
            if options.get('e',False):
                return hunk
        else:
            return hunk
        # if not previously returned return now empty hunk
        return hunks.Empty()

    def process(self,cchunk):
        i = 0
        l = []
        options = cchunk.chunk.options
        decide = lambda i,hunk: hunk.formatted if i == 0 else hunk.simple
        for hunk in cchunk.hunks:
            t = type(hunk)
            if not hunk.simple or options.get('s',False):
                continue
            elif t == hunks.CodeResult and not options.get('a',False):
                continue
            elif t == hunks.CodeIn and not options.get('e',False):
                continue
            else:
                l.append(decide(i,hunk))
                i += 1

        yield cchunk.chunk.number,l



PythonProcessor.register()
CompactFormatter.register()
