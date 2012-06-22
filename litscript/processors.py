import abc


class classproperty(object):
     def __init__(self, getter):
         self.getter= getter
     def __get__(self, instance, owner):
         return self.getter(owner)


class PluginBase(metaclass=abc.ABCMeta):
    @classmethod
    def register(self):
        print(self)
        self.plugins[self.name] = self.process
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

class Proc_Python(Pre):

    @classproperty
    def name(self):
        return 'nothing'

    def process(self,code):
        pass


class Post_Nothing(Post):

    @classproperty
    def name(self):
        return 'Nothing'

    def process(self,code):
        pass

