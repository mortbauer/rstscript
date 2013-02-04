import abc


class Hunk(metaclass=abc.ABCMeta):
    @classmethod
    def register(self):
        self.plugins[self.name] = self
    @abc.abstractproperty
    def type(self):
        pass
    @abc.abstractmethod
    def format(self):
        pass

class TextNode(Hunk):
    def __init__(self,text):
        self.text = text
    @abc.abstractproperty
    def type(self):
        return 'text'
    @abc.abstractmethod
    def format(self):
        return self.text
