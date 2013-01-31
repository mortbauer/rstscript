from io import StringIO
import re
from .colorlog import getlogger

__all__ = ['read','pre_process','process','post_process', 'write']

logger = getlogger('litscript.chunks')

def read(fileobject, key='%', start='<<', end='>>', opt_delim='=',
        pre_def={'fig':False,'proc':'py','pre':'nothing'},post_def={'post':'python'}):
    """This function returns a generator
    It produces pieces from a fileobject, delimited with *chunk_start* and
    *chunk_end* tokens.
    """

    #: holder of real content
    content = StringIO()
    #: counter for trvial error checking
    delimtercounter = 0
    #: informational counter
    chunkn = 0
    #: line number of chunk start
    linecounter = 1
    linechunk = linecounter
    #: allowed option characters
    opt_str = '([a-zA-Z_\-0-9]*)\s*{}\s*([a-zA-Z_\-0-9]*)'
    get_opts = re.compile(opt_str.format(opt_delim))
    #: delimiter, and escaped delimiters
    chunk_start = '{}{}'.format(key,start)
    chunk_end = '{}{}'.format(key,end)
    esc_chunk_start = '{}{}'.format(key,chunk_start)
    esc_chunk_end = '{}{}'.format(key,chunk_end)

    if len(start) != len(end):
        raise ValueError("Length of the start and end tokens must be equal!")
    elif key == start or key == end or start == end:
        raise ValueError("start,end and key delimiters must be distinguished!")
    else:
        token_length = len(chunk_start)

    def buildchunk(t,pre,post,n,l,c):
        c.truncate()
        d = {'type':t,
            'pre_args':pre,
            'post_args':post,
            'number':n,
            'line':l,
            'content_raw':c
            }
        c.seek(0)
        logger.info('reading chunk: type:{t} pre:{pre} post:{post}'.format(t=t,pre=pre,post=post))
        return d,StringIO()

    def get_pre_param(line):
        args = dict(get_opts.findall(line))
        for arg in pre_def:
            args.setdefault(arg,pre_def[arg])
        return args

    def get_post_param(line):
        args = dict(get_opts.findall(line))
        for arg in post_def:
            args.setdefault(arg,post_def[arg])
        return args

    for line in fileobject:
        #logger.info('new line {0}'.format(line))
        line_start = line[:token_length]
        line_startm = line[:(token_length + len(key))]

        # on start of chunk delimiter yield text
        if line_start == chunk_start:
            if content.tell() != 0:
                c,content = buildchunk('text',None,{'post':'python'},chunkn,linechunk,content)
                yield c
            pre_a = get_pre_param(line[token_length:])
            delimtercounter += 1
            linechunk = linecounter
        # on end of chunk delimiter yield code
        elif line_start == chunk_end:
            if content.tell() != 0:
                post_a = get_post_param(line[token_length:])
                c,content = buildchunk('code',pre_a,post_a,chunkn,linechunk,content)
                yield c
            delimtercounter -= 1
        # escaped
        elif (line_startm == esc_chunk_start or line_startm == esc_chunk_end):
            content.write(line[len(key):])
        # normal
        else:
            content.write(line)

        if delimtercounter > 1 or delimtercounter < 0:
            msg = 'missing delimiter before line {}'
            raise GeneratorExit(msg.format(linecounter))

        linecounter += 1

    content.truncate()
    if content.tell() != 0:
        c,content = buildchunk('text',None,None,chunkn,linechunk,content)
        yield c

def pre_process(fileobject, procs_avail):
    proc_name = ''
    proc_ = None
    procs_init = {}
    for chunk in fileobject:

        if chunk['type'] != 'code':
            yield chunk
            continue
        if chunk['pre_args']['pre'] != proc_name:
            proc_name = chunk['pre_args']['pre']
            if not proc_ in procs_init:
                try:
                    procs_init[proc_name] = procs_avail[proc_name]()
                    proc_ = procs_init[proc_name].process
                except KeyError as e:
                    raise e
            else:
                proc_ = procs_init[proc_name].process

        try:
            chunk['content_in'] = proc_(chunk['content_raw'])
        except Exception as e:
            raise e

        yield chunk


def process(fileobject,procs_avail,args):
    proc_name = ''
    proc_ = None
    procs_init = {}
    for chunk in fileobject:
        if chunk['type'] != 'code':
            yield chunk
            continue
        if chunk['pre_args']['proc'] != proc_name:
            proc_name = chunk['pre_args']['proc']
            if not proc_ in procs_init:
                try:
                    procs_init[proc_name] = procs_avail[proc_name]()
                    proc_ = procs_init[proc_name].process
                except KeyError as e:
                    raise e
            else:
                proc_ = procs_init[proc_name].process

        try:
            chunk['stdout'],chunk['stderr'],chunk['traceback'],chunk['figpath']  = proc_(chunk['content_in'],chunk['pre_args'],args)
        except Exception as e:
            raise e

        yield chunk


def post_process(fileobject,procs_avail):
    proc_name = ''
    proc_ = None
    procs_init = {}
    for chunk in fileobject:
        if chunk['type'] != 'code':
            chunk['content_out'] = chunk['content_raw']
            proc_ = None
        elif chunk['type'] == 'code':
            if chunk['post_args']['post'] != proc_name:
                proc_name = chunk['post_args']['post']
            if not proc_ in procs_init:
                try:
                    procs_init[proc_name] = procs_avail[proc_name]()
                    proc_ = procs_init[proc_name].process
                except KeyError as e:
                    raise e
            else:
                proc_ = procs_init[proc_name].process

            #try:
                #chunk['content_out'] = proc_(chunk)
            #except Exception as e:
                #raise e
        chunk['post_processor'] = proc_
        yield chunk


def write(fileobject_in, fileobject_out):
    for chunk in fileobject_in:
        if chunk['post_processor'] != None:
            chunk['post_processor'](chunk,fileobject_out)
        else:
            fileobject_out.write(chunk['content_out'].getvalue())

