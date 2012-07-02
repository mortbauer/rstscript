from io import StringIO
import re
import logging

__all__ = ['read','pre_process','process','post_process',
           'print_args','write']


def read(fileobject, key='%', start='<<', end='>>', opt_delim='=',
         pre_def={'proc':'py'},post_def={}):
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
            'content':c
            }
        content.seek(0)
        return d

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
        line_start = line[:token_length]
        line_startm = line[:(token_length + len(key))]

        # on start of chunk delimiter yield text
        if line_start == chunk_start:
            if content.tell() != 0:
                c = buildchunk('text',None,None,chunkn,linechunk,content)
                yield c
            pre_a = get_pre_param(line[token_length:])
            delimtercounter += 1
            linechunk = linecounter
        # on end of chunk delimiter yield code
        elif line_start == chunk_end:
            if content.tell() != 0:
                post_a = get_post_param(line[token_length:])
                c = buildchunk('code',pre_a,post_a,chunkn,linechunk,content)
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
        c = buildchunk('text',None,None,chunkn,linechunk,content)
        yield c


def pre_process(fileobject):
    for chunk in fileobject:
        yield chunk


def process(fileobject,procs_avail):
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
            chunk['stdout'],chunk['stderr'] = proc_(chunk['content_in'])
        except Exception as e:
            raise e

        yield chunk


def post_process(fileobject):
    for chunk in fileobject:
        if chunk['type'] == 'text':
            chunk['content_out'] = (chunk['content_in'],)
        else:
            chunk['content_out'] = (chunk['content_in'],
                                    chunk['stdout'],
                                    chunk['stderr'])
        yield chunk


def print_args(fileobject):
    msg = 'chunk: {} line: {} pre_args: {} post_args: {}'
    for chunk in fileobject:
        if chunk['type'] == 'code':
            logging.info(msg.format(chunk['number'],chunk['start'],
                                   chunk['pre_args'],chunk['post_args']))
        yield chunk


def print_chunk(chunk):
    msgc = 'content_in: {} stdout: {} stderr: {}'
    msgt = 'content_in: {}'
    logging.debug('chunk: {}'.format(chunk['number']))
    if chunk['type'] == 'code':
        logging.debug(msgc.format(repr(chunk['content_in'].getvalue()),
                          repr(chunk['stdout'].getvalue()),
                          repr(chunk['stderr'].getvalue())))
    else:
        logging.debug(msgt.format(repr(chunk['content_in'].getvalue())))


def write(fileobject_in, fileobject_out):
    for chunk in fileobject_in:
        for stream in chunk['content_out']:
            fileobject_out.write(stream.getvalue())
