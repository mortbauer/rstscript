import unittest
from litscript import glue
from litscript import dictdiffer
import numpy

class LitTester(unittest.TestCase):

    def test_dictdiffer(self):
        a = numpy.array([1,2,3,4])
        dnew = {'a',a}
        dold = {'a',a}
        diff = dictdiffer.DictDiffer(dnew,dold)
        diff.changed()

    #def test_basic(self):
        #L = glue.Litscript({'source':open('testfile.nw','r'),'woutput':'test.rst'},{})
        #L.main()
        #f = open('test.nw', 'rt')
        #c = glue.read(f)
        #p = glue.process(c)
        #pp = glue.post_process(p)
        #out = open('test.rst', 'wt')
        #glue.write(pp,out)
        #out.close()
        #f.close()

if '__main__' == __name__:
    unittest.main()

