import sys
import abc
import traceback
from io import StringIO

__all__ = ['Pre','Proc','Post','Pre_Nothing','Proc_Python','Post_Nothing']


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
        pass

class Proc_Python(Proc):

    def __init__(self):
        self.globalnm = {}
        self.localnm = {}
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.stdout_sys = sys.stdout
        self.stderr_sys = sys.stderr

    @classproperty
    def name(self):
        return 'py'

    def process(self,fileobject):
        self.stdout.seek(0)
        self.stderr.seek(0)
        code = fileobject.getvalue()
        try:
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            exec(code, self.globalnm, self.localnm)
        except:
            traceback.print_exc()
        finally:
            sys.stdout = self.stdout_sys
            sys.stderr = self.stderr_sys
        self.stdout.truncate()
        self.stderr.truncate()
        return (self.stdout,self.stderr)


class Post_Nothing(Post):

    @classproperty
    def name(self):
        return 'Nothing'

    def process(self,code):
        pass

