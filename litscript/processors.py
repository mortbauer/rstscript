from copy import deepcopy
from threading import Thread
from subprocess import Popen,PIPE
from time import sleep
from tempfile import NamedTemporaryFile
import re
import sys, cStringIO, traceback

#{{{OLD
#def _read_nowait(iterable,out):
    #for line in iter(iterable, b''):
        #out.append(line)
#class Executer(object):
    #WAIT = 'LITSCRIPT-END-CHUNK-'

    #def __init__(self,name,cmd_start,cmd_print,cmd_CR='\n'):
        #self.name = name
        #self._counter = 0
        #self._cmd_start = cmd_start #Popen compatible
        #self._cmd_print = cmd_print #command which prints 'LITSCRIPT-END-MAKER'
        #self._cmd_CR = cmd_CR
        #self._started = False
        #self._startup()
    #def __repr__(self):
        #return 'litscript-executer-'+self.name

    #def _startup(self):
        #if self._started == False :
            #self._tmpfile = NamedTemporaryFile(suffix='-litscript-'
                    #+self.name+'.py')
            #self._tmpfilename = self._tmpfile.name
            #self._process = Popen(self._cmd_start,
                    #stdin=PIPE,stdout=PIPE,stderr=PIPE)
            #self._output_raw = []
            #self._reader_raw = Thread(target=_read_nowait,
                    #args=(self._process.stdout.readline,self._output_raw))
            #self._reader_raw.start()
            #self._started = True

    #def _cleanup(self):
        ##self._tmpfile.close()
        #self._process.kill()
        #self._started = False

    #@property
    #def started(self):
        #"""Returns True if started."""
        #return self._started

    #def stop(self):
        #self._cleanup()

    #def execute(self,chunk):
        ##print chunk.content
        #self._tmpfile.write(chunk.content)
        #self._tmpfile.write(self._cmd_print(Executer.WAIT+str(chunk.id))+'\n\n')
        #self._tmpfile.flush()

    ##def execute(self,chunk):
        ##self._counter +=1
        ##self._process.stdin.write(chunk.content+self._cmd_CR)
        ##self._process.stdin.write(self._cmd_print(Executer.WAIT+str(chunk.id))+self._cmd_CR)
        ##return True

    #def get_result(self):
        #result =[]
        #if self._started == True :
            #while ''.join(self._output_raw).count(Executer.WAIT)!=self._counter:
                #sleep(0.01)
            #result = deepcopy(self._output_raw)
            #del self._output_raw[:]
        #return result
#class ChunkProcessor(object):
    #def __init__(self):
        #self.default = {}

    #def __repr__(self):
        #return self.name

    #def execute(self, chunk):
        #if self._check_executer:
            #return self.executer.execute(chunk)
    #def _check_executer(self):
        #if self.__dict__.has_key('executer'):
            #if self.executer.started :
                #return True
    #def unload(self):
        #if self._check_executer():
            #self.executer.stop()

#class IPython2Processor(ChunkProcessor):
    #name = 'ipython2'

    #def __init__(self):
        #self.executer = Executer('ipython2',
                #['python2','-u'], self._ipy_print)

    #def _ipy_print(self,x):
        #return 'print(\'{}\')'.format(x)


#}}}OLD



def execute(expression,namespace_local):
    """
    Executes the given expression in the given local namespace.

    :important: the given namespaces will be changed due to this
                operation

    """
    stdout_ = cStringIO.StringIO()
    stderr_ = cStringIO.StringIO()
    namespace_global = {'__builtins__':None}
    if (type(expression) == str and type(namespace_global) == dict and
    type(namespace_local) == dict):
        stdout, stderr = sys.stdout, sys.stderr # keep original
        sys.stdout = stdout_
        sys.stderr = stderr_
        try:
            exec(expression, namespace_global, namespace_local)
        except:
            traceback.print_exc()
        finally:
            sys.stdout = stdout
            sys.stderr = stderr
    else:
        print("modul '{}' of package litscript, couldn't execute expression: "
        '{}'.format(__file__,expression))
    return (stdout_.getvalue(), stderr_.getvalue())

class Processor(object):
    pass
