import sys
import os
import abc
import traceback
from io import StringIO
from dictdiffer import dictdiffer
from .colorlog import getlogger

__all__ = ['Pre','Proc','Post','Pre_Nothing','Proc_Python','Post_Nothing']


logger = getlogger('litscript.processors')

class classproperty(object):
     def __init__(self, getter):
         self.getter= getter
     def __get__(self, instance, owner):
         return self.getter(owner)

class PluginBase(metaclass=abc.ABCMeta):
    @classmethod
    def register(self):
        self.plugins[self.name] = self
    @abc.abstractproperty
    def name(self):
        pass
    @abc.abstractmethod
    def process(self):
        pass

class Pre(PluginBase):
    plugins = {}


class Proc(PluginBase):
    plugins = {}


class Post(PluginBase):
    plugins = {}


class Pre_Nothing(Pre):

    @classproperty
    def name(self):
        return 'nothing'

    def process(self,code):
        return code

class Proc_Python(Proc):

    def __init__(self):
        self.olddict = {}
        self.localnm = {}
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.traceback = StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr
        self.figurecounter = 0

    @classproperty
    def name(self):
        return 'py'

    def process(self,fileobject,preargs,args):
        self.stdout.seek(0)
        self.stderr.seek(0)
        self.traceback.seek(0)
        code = fileobject.getvalue()
        self.figpath = None
        #logger.warning('local namespace: {0}'.format(self.localnm))
        #logger.info('executeing {0}'.format(code))
        #logger.info('global namespace: {1}'.format(self.globalnm))
        tb = ''
        try:
            if preargs['fig']:
                # import pylab
                c = compile('import pylab','litscript.processors','exec')
                exec(c,self.localnm,self.localnm)
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            c = compile(code,'litscript.dynamic.code','exec')
            #exec(c, self.globalnm, self.localnm)
            exec(code, self.localnm, self.localnm)
            if preargs['fig']:
                figname = '{0}_figure.png'.format(self.figurecounter)
                self.figpath = os.path.join(args['figdir'],figname)
                c = compile("pylab.savefig('{0}')\npylab.close()".format(self.figpath),'litscript.processors','exec')
                exec(c,self.localnm,self.localnm)
                #exec('pylab.show()',self.localnm,self.localnm)
                self.figurecounter += 1
                self.figpath = os.path.relpath(self.figpath,start=os.path.split(args['woutput'])[0])
                logger.info('figure code {0}'.format(code))
        except:
            tb = traceback.format_exc().splitlines()
            self.traceback.write(tb[0])
            self.traceback.write('\n')
            self.traceback.write('\n'.join(tb[3:]))
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
            #self.globalnm.update(self.localnm)
        diff = dictdiffer.DictDiffer(self.localnm,self.olddict)
        self.autoprint(diff.added(),self.localnm)
        try:
            self.autoprint(diff.changed(),self.localnm)
        except Exception as e:
            logger.error('Unresolved error: {0}'.format(e))
        self.olddict.update(self.localnm)
        #logger.info('changes {0}'.format(d.added()))
        self.stdout.truncate()
        self.stderr.truncate()
        self.traceback.truncate()
        return (self.stdout,self.stderr,self.traceback,self.figpath)

    def autoprint(self,diff,d):
        self.stdout.write('\n#summary of chunk\n')
        for x in diff:
            try:
                self.stdout.write('\n{0} = {1:.5g}'.format(x,d[x]))
            except Exception as e:
                logger.warning(e)

class Post_Python(Post):

    @classproperty
    def name(self):
        return 'python'

    def process(self,chunk,fileobject):
        fileobject.write('\n.. code-block:: python\n\n')
        #fileobject.write('\n::\n\n')
        def mwrite(x):
            x.seek(0)
            for line in x:
                fileobject.write('\t')
                fileobject.write(line)

        for p in ('content_in','stdout','stderr','traceback'):
            mwrite(chunk[p])
        fileobject.write('\n')

        if chunk['figpath']:
            fileobject.write('\n.. figure:: {0}\n\n'.format(chunk['figpath']))
            print(chunk['figpath'])

class Post_Nothing(Post):

    @classproperty
    def name(self):
        return 'nothing'

    def process(self,stdout,stderr):
        return (stdout,stderr)

