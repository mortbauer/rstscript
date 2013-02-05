import sys
import os
import traceback
import argparse
import ast
import logging
import io

from . import astvisitors
from . import hunks
from . import utils

logger = logging.getLogger('litscript.process')

class BaseProcessor(utils.PluginBase):
    plugins = {}

class PythonProcessor(object):
    _options = {'echo':['-e','--echo'],'autoprint':['-a','--autoprint']}
    _aliases = utils.optionconverter(_options)

    @property
    def aliases(self):
        return self._aliases

    @property
    def options(self):
        return self._options

    @property
    def name(self):
        return 'python'

    def __init__(self):
        self.init = True
        self.globallocal = {}
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.traceback = io.StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr
        self.visitor = astvisitors.LitVisitor()

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
        ce = hunks.CodeError(self.stderr.getvalue())
        ct = hunks.CodeTraceback(self.traceback.getvalue())
        cout = hunks.CodeResult(self.stdout.getvalue())
        cs = hunks.CodeIn(codechunk.source)
        coo = codechunk.codeobject
        return hunks.CHunk(cs,coo,cout,ce,ct,{})

    def process(self,chunk):
        tree = ast.parse(chunk.raw)
        lhunks = []
        for codechunk in self.visitor.visit(tree,chunk.lineNumber):
            lhunks.append(self.execute(codechunk))
        yield hunks.CChunk(chunk,lhunks)

