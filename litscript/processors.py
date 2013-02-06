import io
import sys
import ast
import meta
import traceback
import logging
import collections
import pprint


from . import hunks
from . import utils

logger = logging.getLogger('litscript.process')

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
        codeobject = compile(ast.Module([node]),"<litscript.dynamic>",'exec')
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

class BaseProcessor(utils.PluginBase):
    plugtype = 'processor'
    plugins = {}


class PythonProcessor(BaseProcessor):
    name = 'python'
    options = {'echo':['-e','--echo'],'autoprint':['-a','--autoprint']}
    aliases = utils.optionconverter(options)

    def __init__(self):
        self.init = True
        self.globallocal = {}
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.traceback = io.StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr
        self.visitor = LitVisitor()

    def execute(self,codechunk):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.stdout.seek(0)
        self.stderr.seek(0)
        self.traceback.seek(0)
        try:
            exec(codechunk.codeobject,self.globallocal,self.globallocal)
        except:
            tr = traceback.format_exc().strip()
            # remove all line until a line containing litscript.dynamic except
            # the first
            st = tr.find('\n')+1
            en = tr.find('File "<litscript.dynamic>"')
            self.traceback.write(tr[:st])
            self.traceback.write(tr[en:])
            logger.warning('failed on line {0} with {1}'.
                    format(codechunk.codeobject.co_firstlineno,tr[tr.rfind('\n')+1:]))
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
        self.stdout.truncate()
        self.stderr.truncate()
        yield hunks.CodeStdErr(self.stderr.getvalue())
        yield hunks.CodeTraceback(self.traceback.getvalue())
        yield hunks.CodeStdOut(self.stdout.getvalue())
        yield hunks.CodeIn(codechunk.source)
        if codechunk.assign:
            coa = codechunk.assign
            try:
                yield hunks.CodeResult('{0} = {1}'.format(coa,self.globallocal[coa]))
            except KeyError:
                pass

        #return hunks.CHunk(cs,coo,cout,ce,ct,self.globallocal)

    def process(self,chunk):
        tree = ast.parse(chunk.raw)
        lhunks = []
        for codechunk in self.visitor.visit(tree,chunk.lineNumber):
            for hunk in self.execute(codechunk):
                if hunk.simple:
                    lhunks.append(hunk)
        yield hunks.CChunk(chunk,lhunks)

class BaseFormatter(utils.PluginBase):
    plugtype = 'formatter'
    plugins = {}


class CompactFormatter(BaseFormatter):
    name = 'compact'
    options = {'linewise':['--linewise'],'autoprint':['--autoprint']}
    aliases = utils.optionconverter(options)

    def process(self,cchunk,options):
        yield cchunk.hunks[0].formatted
        for hunk in cchunk.hunks[1:]:
            if type(hunk)==hunks.CodeResult:
                if options.setdefault('--autoprint',False):
                    yield hunk.simple
                else:
                    print(options)

            else:
                yield hunk.simple
