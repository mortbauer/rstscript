from io import StringIO
import re
import logging

__all__ = ['read','default_args','pre_process','process','post_process',
           'print_args','write']


class LitscriptException(Exception):
    """Base class for exceptions in this module."""
    pass


def read(fileobject, chunk_start='%<<', chunk_end='%>>', opt_delim='='):
    """This function produces a generator, which is iterable.
    The pieces it produces from a readable file have to be delimited
    by a three character long token at the beginning of a line.
    It only chenks for the delimiters at the begining of each iterated piece.
    """

    content = StringIO()
    delimtercounter = 0
    chunkcounter = 0
    re_str = '([a-zA-Z_\-0-9]*)\s*{}\s*([a-zA-Z_\-0-9]*)'
    get_opts = re.compile(re_str.format(opt_delim))
    esc_chunk_start = '%{}'.format(chunk_start)
    esc_chunk_end = '%{}'.format(chunk_end)
    content = StringIO()

    if len(chunk_start) != len(chunk_end):
        raise ValueError("Length of the start and end tokens must be equal.")
    else:
        token_length = len(chunk_start)

    linecounter = 1
    linechunk = 0
    for line in fileobject:
        line_start = line[:token_length]
        line_startm = line[:token_length + 1]

        # start of chunk
        if line_start == chunk_start:
            content.truncate()
            pre_args = dict(get_opts.findall(line[token_length:]))
            yield {'type':'text','content_in':content,'number':chunkcounter,
                   'start':linechunk}
            content.seek(0)
            delimtercounter += 1
            chunkcounter += 1
            linechunk = linecounter
        # end of chunk
        elif line_start == chunk_end:
            content.truncate()
            post_args = dict(get_opts.findall(line[token_length:]))
            yield {'type':'code', 'content_in':content,
                   'pre_args':pre_args, 'post_args':post_args,
                   'number':chunkcounter,'start':linechunk}
            content.seek(0)
            delimtercounter -= 1
            chunkcounter += 1
            linechunk = linecounter
        # escaped
        elif (line_startm == esc_chunk_start or line_startm == esc_chunk_end):
            content.write(line[1:])
        # normal
        else:
            content.write(line)

        if delimtercounter > 1 or delimtercounter < 0:
            msg = 'line: {}: You may have forgotten a delimiter.'\
                    .format(linecounter)
            logging.error(msg)
            break

        linecounter += 1

    content.truncate()
    yield {'type':'text','content_in':content,'number':chunkcounter,
            'start':linechunk}


def default_args(fileobject,pre_def={'proc':'py'},post_def={}):
    for chunk in fileobject:
        if chunk['type'] == 'text':
            yield chunk
        else:
            for x in pre_def:
                chunk['pre_args'].setdefault(x,pre_def[x])
            for x in post_def:
                chunk['post_args'].setdefault(x,post_def[x])
            yield chunk


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
