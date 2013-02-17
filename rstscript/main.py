import os
import sys
import time
import yaml
import ujson
import socket
import select
import pkgutil
import argparse
import rstscript

from rstscript import daemonize
from rstscript import server

def make_color_handler():
    import logging
    import colorama
    class ColorizingStreamHandler(logging.StreamHandler):
        # Courtesy http://plumberjack.blogspot.com/2010/12/colorizing-logging-output-in-terminals.html
        # Tweaked to use colorama for the coloring

        """
        Sets up a colorized logger, which is used ltscript
        """
        color_map = {
            logging.INFO: colorama.Fore.WHITE,
            logging.DEBUG: colorama.Style.DIM + colorama.Fore.CYAN,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Back.RED,
            logging.FATAL: colorama.Back.RED,
        }

        def __init__(self, stream, color_map=None):
            logging.StreamHandler.__init__(self,
                                        colorama.AnsiToWin32(stream).stream)
            if color_map is not None:
                self.color_map = color_map

        @property
        def is_tty(self):
            isatty = getattr(self.stream, 'isatty', None)
            return isatty and isatty()

        def format(self, record):
            message = logging.StreamHandler.format(self, record)
            if self.is_tty:
                # Don't colorize a traceback
                parts = message.split('\n', 1)
                parts[0] = self.colorize(parts[0], record)
                message = '\n'.join(parts)
            return message

        def colorize(self, message, record):
            try:
                return (self.color_map[record.levelno] + message +
                        colorama.Style.RESET_ALL)
            except KeyError:
                return message
    return ColorizingStreamHandler(sys.stdout)

def make_server_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])

    subparsers = parser.add_subparsers(dest='command')
    start = subparsers.add_parser('start',help='start the server')
    stop = subparsers.add_parser('stop',help='stop the server')
    restart = subparsers.add_parser('restart',help='restart the server')

    parser.add_argument("--pdb",action='store_true', dest="pdb",
            help="debug with pdb or ipdb")
    parser.add_argument( "--foreground", action="store_true", default=False,
                    help="don\'t detach from terminal")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
            help="run in debugging mode, equivalent to -l debug")
    parser.add_argument('-l','--loglevel',dest='loglevel', default='WARNING',
            help='specify the logging level')
    parser.add_argument('--version', action='version', version=rstscript.__version__)

    return pre_parser,parser


def make_client_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('-i','--input', required=True,
            help='rstscript source file')
    parser.add_argument("-ow", dest="woutput", nargs='?',
            help="output file for weaving")
    parser.add_argument('--noweave',action='store_true',dest='noweave',
            help='don\'t weave the document')
    parser.add_argument('-t',action='store_true',dest='tangle',
            help='tangle the document')
    parser.add_argument("-ot", dest="toutput", nargs='?',
            help="output file for tangling")
    parser.add_argument("--figure-directory", dest='figdir',
                    action="store", default='_figures',
                    help="path to store produced figures")
    parser.add_argument('--plugindir',action='store',
            default=os.path.join(default_configdir,'plugins'),
            help='specify the plugin directory')

    parser.add_argument("-d", "--debug", action="store_true", default=False,
            help="run in debugging mode, equivalent to -l debug")
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
            help='disable all output, won\'t guarante that i won\'t crash though')
    parser.add_argument('-l','--loglevel',dest='loglevel', default='WARNING',
            help='specify the logging level')
    parser.add_argument('--no-plugins',action='store_true',
            help='don\'d load any plugin')
    parser.add_argument('--version', action='version', version=rstscript.__version__)
    parser.add_argument('options', default=None,nargs=argparse.REMAINDER,
            help='a valid json dictionary set as default chunk options')
    return pre_parser,parser


def make_initial_setup(configfilename):
    """ copies the default config file
    should only be run if the "configfilename is not existent
    """
    print('The configuration file "{0}" is not existent'.format(configfilename))
    userinput = input('should I create it with the default values (y/n): ').lower()
    i = 0
    while not userinput in ['y','n'] and i < 5:
        userinput = input('type exactly "y" for yes or "n" for no: ').lower()
        i += 1
    if not userinput in ['y','n']:
        print('are you nuts, I said exactly "y" or "n", I will give up')
        return False
    elif userinput == 'y':
        with open(configfilename,'wb') as f:
            f.write(pkgutil.get_data(__name__,'defaults/config.json'))
        return True
    elif userinput == 'n':
        return False


def server_main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_server_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    # parse main args
    configs.update(vars(parser.parse_args(remaining_argv)))
    # lazy create a daemonizedserver object
    daemon = daemonize.SocketServerDaemon(configs,server.RstscriptHandler)
    # start/stop the server
    if configs['command'] == 'restart':
        try:
            daemon.stop()
            daemon.start()
        except:
            raise
            sys.exit(1)
    elif configs['command'] == 'stop':
        try:
            daemon.stop()
        except daemonize.DaemonizeNotRunningError as e:
            sys.stderr.write(str(e))
            sys.exit(1)
    elif configs['command'] == 'start':
        if not os.path.exists(configs['socketfile']):
            try:
                daemon.start()
            except daemonize.DaemonizeAlreadyStartedError as e:
                sys.stderr.write(str(e))
                sys.exit(1)
        else:
            sys.stderr.write('the socketfile "{0}" exists already, if you are'
                    'sure the server is down you can run "rstscriptd clean" to'
                    'remove it'.format(configs['socketfile']))
            sys.exit(1)


def client_main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_client_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    # parse main args
    mainopts, throughargs = parser.parse_known_args(remaining_argv)
    configs.update(vars(mainopts))
    # add the source directory to the config
    configs['rootdir'] = os.path.abspath('.')
    # make the file paths absolute
    for x in ('input','woutput','toutput'):
        if configs[x] and not os.path.isabs(configs[x]) :
            configs[x] = os.path.join(configs['rootdir'],configs[x])
    # additional options are in a list we don't want that
    if configs['options']:
        configs['options'] = configs['options'][0]
    # add current tty info
    for std in ('stdin','stdout','stderr'):
        fileno = getattr(sys,std).fileno()
        if os.isatty(fileno):
            configs[std] = os.ttyname(fileno)

    # Connect to the server
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(configs['socketfile'])
    except:
        sys.stderr.write('it seems like the server is down')
        sys.exit(1)

    sock.setblocking(0)

    # Send the data
    message = ujson.dumps(configs)
    #print('\nSending : "%s"' % message)
    len_sent = sock.send(message.encode('utf-8'))

    # Receive a response
    ready = select.select([sock], [], [], 6)
    if ready:
        response = sock.recv(1024)
        #print('\nReceived: "%s"' % response.decode('utf-8'))
        # Clean up
    sock.close()

