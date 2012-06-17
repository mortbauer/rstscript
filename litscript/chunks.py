import traceback
from io import StringIO
import sys
import re


def testcase():
    f = open('test.nw', 'rt')
    c = chunker(f)
    e = executer(c)
    post_processor(e)


def post_processor(fileobject:'iterable'):
    for chunk in fileobject:
        print(chunk)


def processor(fileobject:'iterable'):
    """Executes the given expression in the given local namespace."""
    #:store the reference to the std's
    stdout = sys.stdout
    stderr = sys.stderr
    #:instantiate StringIO object
    stdout_ = StringIO()
    stderr_ = StringIO()
    namespace_global = {}
    namespace_local = {}

    for chunk in fileobject:
        if chunk['type'] == 'code':
            try:
                #:change std's
                sys.stdout = stdout_
                sys.stderr = stderr_
                exec(chunk['content'], namespace_global, namespace_local)
            except:
                #:get raised Exceptions into the faked stderr
                traceback.print_exc()
            finally:
                #:restore std's
                sys.stdout = stdout
                sys.stderr = stderr
            chunk['stdout'] = stdout_.getvalue()
            chunk['stderr'] = stderr_.getvalue()
        yield chunk


def chunker(fileobject:'iterable', chunk_start='%<<', chunk_end='%>>'):
    """This function produces a generator, which is iterable.
    The pieces it produces from a readable file have to be delimited
    by a three character long token at the beginning of a line.
    It only chenks for the delimiters at the begining of each iterated piece.
    """
    content = ''
    get_opts = re.compile('([a-zA-Z_\-0-9]*)\s*=\s*([a-zA-Z_\-0-9]*)')

    if len(chunk_start) != len(chunk_end):
        raise ValueError("The length of the start and end"
                         "tokens must be equal.")
    else:
        token_length = len(chunk_start)

    for line in fileobject:
        line_start = line[:token_length]

        if line_start == chunk_start or line_start == chunk_end:
            if line_start == chunk_start:
                pre_args = dict(get_opts.findall(line[token_length:]))
                yield {'type':'text','content':content}
                content = ''
            else:
                post_args = dict(get_opts.findall(line[token_length:]))
                yield {'type':'code', 'content':content,
                         'pre_args':pre_args, 'post_args':post_args}
                content = ''
        else:
            content += line

    yield {'type':'text','content':content}
