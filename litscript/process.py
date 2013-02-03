import sys
import os
import traceback
import argparse
import ast
from io import StringIO
from .colorlog import getlogger
from . import astvisitors
from . import nodes


logger = getlogger('litscript.process')

class PythonProcessor(object):
    name = 'python'
    parser = argparse.ArgumentParser('python',description=('the python standard executer'))

    def __init__(self):
        self.init = True
        self.globallocal = {}
        self.traceback = StringIO()
        self.stderr = StringIO()
        self.stdout = StringIO()
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
            exec(codechunk,self.globallocal,self.globallocal)
        except:
            self.traceback.write(traceback.format_exc())
            logger.warning('failed on {0}'.format(tb[:10]))
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
        self.stdout.truncate()
        self.stderr.truncate()
        self.traceback.truncate()
        if self.stderr.tell():
            yield nodes.error_node(self.stderr.getvalue())
        if self.traceback.tell():
            yield nodes.traceback_node(self.traceback.getvalue())
        if self.stdout.tell():
            yield nodes.result_node_node(self.stdout.getvalue())

    def process(self,chunk):
        tree = ast.parse(chunk.raw)
        for codechunk in self.visitor.visit(tree):
            yield from self.execute(codechunk)

