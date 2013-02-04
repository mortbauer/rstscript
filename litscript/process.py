import sys
import os
import traceback
import argparse
import ast
from io import StringIO
from .colorlog import getlogger
from . import astvisitors
from . import hunks

logger = getlogger('litscript.process')

def optionconverter(options):
    rev = {}
    for opt in options:
        for alias in options[opt]:
            rev[alias] = opt
    return rev

class PythonProcessor(object):
    name = 'python'
    parser = argparse.ArgumentParser('python',description=('the python standard executer'))
    options = {'echo':['-e','--echo'],'autoprint':['-a','--autoprint']}
    aliases = optionconverter(options)

    def __init__(self):
        self.init = True
        self.globallocal = {}
        self.stderr = StringIO()
        self.stdout = StringIO()
        self.traceback = StringIO()
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

