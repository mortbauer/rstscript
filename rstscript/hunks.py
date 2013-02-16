import abc
import collections
import textwrap

CHunk = collections.namedtuple('CHunk',['source','codeobject','stdout','stderr','traceback','globallocal'])
THunk = collections.namedtuple('THunk',['source'])


class Node(metaclass=abc.ABCMeta):

    @property
    def type(self):
        """ read only property, name of implementing class """
        return super().__self_class__.__name__

    @abc.abstractmethod
    def formatted(self):
        """ must be implemented in order to instantiate """
        pass

class Empty(Node):
    @property
    def formatted(self):
        return ''
    @property
    def simple(self):
        return ''


class Text(Node):
    template = '\n{text}\n'
    def __init__(self,text):
        self.text = text.strip()
    @property
    def formatted(self):
        return self.template.format(text=self.text)

class CodeBlock(Node):
    template = '\n.. code-block:: {lang}\n\n{code}\n'
    def __init__(self,code,label='',language='python'):
        self.code = textwrap.indent(code.strip(),'\t')
        self.lang = language
        self.label = label
    @property
    def formatted(self):
        if len(self.code) > 0:
            return self.template.format(lang=self.lang,code=self.code)
        else:
            return ''

    @property
    def simple(self):
        if len(self.code) > 0:
            return '\n{}\n'.format(self.code)
        else:
            return ''

class CodeResult(CodeBlock):
    pass


class CodeTraceback(CodeBlock):
    pass


class CodeStdErr(CodeBlock):
    pass

class CodeStdOut(CodeBlock):
    pass

class CodeIn(CodeBlock):
    pass


class Figure(Node):
    template = ('\n.. _{self.label}:\n\n.. figure:: {self.path}\n\t:alt: {self.alt}\n\t:width: {self.width}'
            '\n\t:height: {self.height}\n\n\t{self.desc}\n')
    def __init__(self,path,label='',alt='',width='100mm',height='100mm',desc=''):
        self.path = path
        self.label = label
        self.alt = alt
        self.width = width
        self.height = height
        self.desc = desc
    @property
    def formatted(self):
        return self.template.format(self=self)

    @property
    def simple(self):
        return self.template.format(self=self)
