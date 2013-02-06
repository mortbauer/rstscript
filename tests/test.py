import unittest
import testify
import os
import logging
import numpy
import ast
from litscript import chunks
from litscript import processors
from litscript import main

def setup_base_litrunner():
    L = chunks.Litrunner()
    L.register_processor(processors.PythonProcessor)
    L.register_formatter(processors.CompactFormatter)
    L.set_defaults(processors.PythonProcessor.name,[],processors.CompactFormatter.name,[])
    L.test_readiness()
    return L

class LitTester(unittest.TestCase):
    testfile = os.path.join(os.path.split(__file__)[0],'testfile.nw')

    def test_basic_argparsing(self):
        pre = main.make_pre_parser()
        parser = main.make_parser(pre)
        args = parser.parse_args(['-d','weave','-itestfile.nw','--args','-a'])
        self.assertTrue(args.debug)

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

