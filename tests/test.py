import unittest
import testify
import os
import logging
import numpy
import ast
from litscript import chunks
from litscript import process
from litscript import dictdiffer
from litscript import astvisitors
from litscript import formatter
from litscript import worker

class LitTester(unittest.TestCase):
    testfile = os.path.join(os.path.split(__file__)[0],'testfile.nw')

    def test_dictdiffer(self):
        a = numpy.array([1,2,3,4])
        dnew = {'a':a}
        dold = {'a':a}
        diff = dictdiffer.DictDiffer(dnew,dold)
        self.assertTrue(diff.changed())

    def test_readfile(self):
        L = worker.main()
        with open(self.testfile,'r') as f:
            for ch in L.read(f):
                pass

    def test_weave(self):
        L = worker.main()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            node_generator = L.weave(chunk_generator)
            for node in node_generator:
                print(node)

    def test_format(self):
        L = worker.main()
        with open(self.testfile,'r') as f:
            chunk_generator = L.read(f)
            cchunk_generator = L.weave(chunk_generator)
            string_generator = L.format(cchunk_generator)
            for node in string_generator:
                print(node)


    def test_astvisitor(self):
        a = "b= lambda x: x*5 +5\ndef hhh(u):\n    b=19\n    return u*b\nm=hhh(9*4+5)"
        tree = ast.parse(a)
        visitor = astvisitors.LitVisitor()
        for node in visitor.visit(tree,1):
            pass

if '__main__' == __name__:
    #testify.run()
    unittest.main()

