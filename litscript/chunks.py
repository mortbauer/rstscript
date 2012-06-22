import traceback
from io import StringIO
import sys
import re
import abc


class LitscriptException(Exception):
    """Base class for exceptions in this module."""
    pass

class mbase(type):
    def __new__(meta,clsname,bases,clsdict):
        print('mbase new',meta,clsname,bases,clsdict)
        if not hasattr(meta,'list'):
            meta.list = []
        meta.list.append(clsname)
        return type.__new__(meta, clsname, bases, clsdict)

    def __init__(meta,clsname,bases,clsdict):
        print('mbase init',meta,clsname,bases,clsdict)

class fmbase(object,metaclass=mbase):
    def __new__(cls):
        print(cls)
class rmbase(object,metaclass=mbase):
    def __new__(cls):
        print(cls)

class tt(fmbase):
    pass

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

class Pre_Pass(Pre):

    @classproperty
    def name(self):
        return 'default'

    def process(self,code):
        pass

class Post(PluginBase):
    plugins = {}

class Post_Pass(Post):

    @classproperty
    def name(self):
        return 'default'

    def process(self,code):
        pass

def testcase():
    f = open('test.nw', 'rt')
    c = read(f)
    p = process(c)
    pp = post_process(p)
    out = open('test.rst', 'wt')
    write(pp,out)
    out.close()
    f.close()


def read(fileobject, chunk_start='%<<', chunk_end='%>>', opt_delim='='):
    """This function produces a generator, which is iterable.
    The pieces it produces from a readable file have to be delimited
    by a three character long token at the beginning of a line.
    It only chenks for the delimiters at the begining of each iterated piece.
    """

    content = StringIO()
    delimtercounter = 0
    re_str = '([a-zA-Z_\-0-9]*)\s*{}\s*([a-zA-Z_\-0-9]*)'
    get_opts = re.compile(re_str.format(opt_delim))
    esc_chunk_start = '%{}'.format(chunk_start)
    esc_chunk_end = '%{}'.format(chunk_end)
    content = StringIO()

    if len(chunk_start) != len(chunk_end):
        raise ValueError("Length of the start and end tokens must be equal.")
    else:
        token_length = len(chunk_start)

    for line in fileobject:
        line_start = line[:token_length]
        line_startm = line[:token_length + 1]
        # start of chunk
        if line_start == chunk_start:
            pre_args = dict(get_opts.findall(line[token_length:]))
            yield {'type':'text','content_in':content}
            content.seek(0)
            delimtercounter += 1
        # end of chunk
        elif line_start == chunk_end:
            content.truncate()
            post_args = dict(get_opts.findall(line[token_length:]))
            yield {'type':'code', 'content_in':content,
                        'pre_args':pre_args, 'post_args':post_args}
            content.seek(0)
            delimtercounter -= 1
        # escaped
        elif (line_startm == esc_chunk_start or line_startm == esc_chunk_end):
            content.write(line[1:])
        # normal
        else:
            content.write(line)

    if delimtercounter != 0:
        raise LitscriptException('You may have forgotten to end a code chunk.')
    else:
        content.truncate()
        yield {'type':'text','content_in':content}


def pre_process(fileobject):
    for chunk in fileobject:
        yield chunk


def process(fileobject):
    """Executes the given expression in the given local namespace."""
    #:store the reference to the std's
    stdout = sys.stdout
    stderr = sys.stderr
    namesp_global = {}
    namesp_local = {}

    for chunk in fileobject:
        #:instantiate StringIO object
        stdout_ = StringIO()
        stderr_ = StringIO()
        if chunk['type'] == 'code':
            code = chunk['content_in'].getvalue()
            #print('CODE: ',code,type(code),repr(code))
            try:
                #:change std's
                sys.stdout = stdout_
                sys.stderr = stderr_
                exec(code, namesp_global, namesp_local)
            except:
                #:get raised Exceptions into the faked stderr
                traceback.print_exc()
            finally:
                #:restore std's
                sys.stdout = stdout
                sys.stderr = stderr

            chunk['stdout'] = stdout_
            chunk['stderr'] = stderr_
        yield chunk


def post_process(fileobject):
    for chunk in fileobject:
        if chunk['type'] == 'text':
            chunk['content_out'] = (chunk['content_in'],)
        else:
            chunk['content_out'] = (chunk['content_in'],chunk['stdout'])
        yield chunk


def write(fileobject_in, fileobject_out):
    for chunk in fileobject_in:
        for stream in chunk['content_out']:
            fileobject_out.write(stream.getvalue())
