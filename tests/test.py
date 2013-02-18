import unittest
import os
import sys
import logging
import ast
import logging
from io import StringIO

# Path hack.
sys.path.insert(0, os.path.abspath('..'))
from rstscript import litrunner
from rstscript import processors
from rstscript import main

def setup_base_litrunner():
    L = litrunner.Litrunner({},logging.getLogger('test'))
    return L

class LitTester(unittest.TestCase):
    testfile = os.path.join(os.path.split(__file__)[0],'testfile.nw')

    def test_readfile(self):
        L = litrunner.Litrunner({},logging.getLogger('test'))
        with open(self.testfile,'r') as f:
            for x in L.read(f):
                pass

    def test_weave(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            node_generator = L.weave(chunk_generator)
            for node in node_generator:
                pass

    def test_tangle(self):
        L = litrunner.Litrunner({},logging.getLogger('test'))
        L.toutput = StringIO()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            for node in chunk_generator:
                pass

    def test_format(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            cchunk_generator = L.weave(chunk_generator)
            string_generator = L.format(cchunk_generator)
            for node in string_generator:
                pass

    def test_astvisitor(self):
        a = "b= lambda x: x*5 +5\ndef hhh(u):\n    b=19\n    return u*b\nm=hhh(9*4+5)"
        tree = ast.parse(a)
        visitor = processors.LitVisitor()
        for node in visitor.visit(tree,1):
            pass

if '__main__' == __name__:
    #testify.run()
    unittest.main()

