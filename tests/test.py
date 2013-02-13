import unittest
import os
import logging
import ast
from rstscript import litrunner
from rstscript import processors
from rstscript import main
from argparse import Namespace
from io import StringIO

def setup_base_litrunner():
    L = litrunner.Litrunner(Namespace(toutput=StringIO(),processor='python',formatter='compact'))
    return L

class LitTester(unittest.TestCase):
    testfile = os.path.join(os.path.split(__file__)[0],'testfile.nw')

    def test_readfile(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            for ch in L.read(f):
                pass

    def test_weave(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            node_generator = L.weave(chunk_generator)
            for node in node_generator:
                print(node)

    def test_tangle(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            node_generator = L.tangle(chunk_generator)
            for node in node_generator:
                print(node)
        print(L.options.toutput.getvalue())

    def test_format(self):
        L = setup_base_litrunner()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            cchunk_generator = L.weave(chunk_generator)
            string_generator = L.format(cchunk_generator)
            for node in string_generator:
                print(node)

    def test_astvisitor(self):
        a = "b= lambda x: x*5 +5\ndef hhh(u):\n    b=19\n    return u*b\nm=hhh(9*4+5)"
        tree = ast.parse(a)
        visitor = processors.LitVisitor()
        for node in visitor.visit(tree,1):
            pass

if '__main__' == __name__:
    #testify.run()
    unittest.main()

