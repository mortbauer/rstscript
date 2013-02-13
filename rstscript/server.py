import os
import sys
import ipdb
import socket
import logging
import argparse
import colorama
import rstscript
import threading

from rstscript import simpledaemon

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

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

class RstScriptServer(simpledaemon.Daemon):
    logmaxmb = 0
    logbackups = 0
    loglevel = 'info'
    pidfile = './HelloDaemon.pid'
    logfile = './HelloDaemon.log'
    uid = os.getuid()
    gid = os.getgid()
    sockfile = '.communication.sock'
    daemonize = True

    def __init__(self,options,parser,logger):
        self.options = options
        self.parser = parser
        self.logger = logger
    def make_socket(self):
        if os.path.exists( self.sockfile ):
            self.logger.info('socket already found, won\'t start the server again')
            return False
        s = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
        self.logger.info('created socket "{0}"'.format(self.sockfile))
        try:
            s.bind(self.sockfile)
        except socket.error as msg:
            self.logger.error('bind failed. {0}'.format(msg))
            return False
        self.logger.info('bound socket to "{0}"'.format(self.sockfile))
        return s

    #Function for handling connections. This will be used to create threads
    def clientthread(self,conn):
        #Sending message to connected client
        self.logger.info('connection "{0}" established'.format(conn))
        try:
            #Receiving from client
            data = conn.recv(1024)
            self.logger('received "{0}"'.format(data))
        except socket.BlockingIOError as e:
            print('BlockingIOError',e)
        conn.shutdown()
        ##came out of loop
        #conn.close()
    def run(self):
        sock = self.make_socket()
        if sock:
            try:
                #Start listening on socket
                sock.listen(10)
                self.logger.info('Socket now listening')
                #now keep talking with the client
                while 1:
                    #wait to accept a connection - blocking call
                    conn, addr = sock.accept()
                    #print('Connected with ' + addr[0] + ':' + str(addr[1]))

                    #start new thread takes 1st argument as a funcqion name to be
                    #run, second is the tuple of arguments to the function.
                    thread = threading.Thread(target=self.clientthread,args=(conn,))
                    thread.start()
            finally:
                sock.close()

def make_preparser():
    pre_parser = argparse.ArgumentParser()
    pre_parser.add_argument("-c", "--conf", dest="conf",
                            help="specify config file")
    pre_parser.add_argument("--pdb",action='store_true', dest="pdb",
                            help="debug with pdb")

    hard_defaults = {"conf":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript","config"),
        "conf.d":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript"),
        "plugindir":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript","plugindir")}
    # create default configuration directory and files if not there
    if not os.path.exists(hard_defaults['conf.d']):
        os.mkdir(hard_defaults['conf.d'])
        print('created configuration directory "{0}"'
                .format(hard_defaults['conf.d']))
    if not os.path.exists(hard_defaults['plugindir']):
        os.mkdir(hard_defaults['plugindir'])
        print('created plugin directory "{0}"'
                .format(hard_defaults['plugindir']))
    if not os.path.exists(hard_defaults['conf']):
        with open(hard_defaults['conf'],'wb') as f:
            f.write(pkgutil.get_data(__name__, 'defaults/config'))
        print('created configuration file "{0}"'
                .format(hard_defaults['conf']))
    pre_parser.set_defaults(**hard_defaults)
    return pre_parser

def make_configparser(conf_file):
    config_parser = SafeConfigParser()
    abspath = os.path.abspath(conf_file)
    if os.path.exists(abspath):
        config_parser.read([abspath])
        return config_parser
    else:
        logger.warning('The given path: %s does not exist' % abspath)
        return config_parser

def make_logger(debug=False,quiet=False,loglevel='WARNING'):
    logger = logging.getLogger('rstscript.server')
    # setup the app logger
    if quiet:
        handler = logging.NullHandler()
    else:
        handler = ColorizingStreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if debug:
        logger.setLevel('DEBUG')
    else:
        if hasattr(logging,loglevel):
            logger.setLevel(getattr(logging,loglevel.upper()))
        else:
            logger.setLevel('WARNING')
            logger.error('invalid logging level "{0}"'.format(loglevel))
    return logger

def make_parser(defaults):
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                    action="store", default='',
                    help="Optional directory containing rstscript plugin"
                        " files.")
    parser.add_argument('--no-plugins',action='store_true',
                    help='disable all plugins')
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                    help="Run in debugging mode.")
    parser.add_argument("-f", "--force", action="store_true", default=False,
                    help="will override existing files without asking")
    parser.add_argument('-l','--log-level',dest='loglevel', default='WARNING',
                    help='Specify the logging level')
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                    help='Disable stdout logging')
    parser.add_argument('--version', action='version', version=rstscript.__version__)

    parser.add_argument('-i','--input', dest='input',type=argparse.FileType('rt'), nargs=1,
                    required=True,default=[sys.stdin], help='rstscript source file')

    parser.add_argument('-t',action='store_true',dest='tangle',help='tangle the document')

    parser.add_argument("-ot", dest="toutput",
                        type=argparse.FileType('wt'), nargs='?',
                    help="output file for tangling")

    parser.add_argument('--noweave',action='store_true',dest='noweave',
            help='don\'t weave the document')

    parser.add_argument("-ow", dest="woutput",
                        type=argparse.FileType('wt'), nargs='?',
                    help="output file for weaving")

    parser.add_argument("--processor", dest="processor",default='python',
                    help="default code processor")
    parser.add_argument("--formatter", dest="formatter",default='compact',
                    help="default code formatter")
    parser.add_argument("--figure-directory", dest='figdir',
                    action="store", default='_figures',
                    help="path to store produced figures")
    parser.add_argument("-g","--figure-format", dest="figfmt",
                    action="store", default="png",
                    help="Figure format for matplolib graphics: Defaults to"
                        "'png' for rst and Sphinx html documents and 'pdf' "
                        "for tex")
    # set the defaults
    parser.set_defaults(**defaults)
    return parser

def main(argv=None):
    if not argv:
        argv = sys.argv[1:]
    pre_parser = make_preparser()
    options = pre_parser.parse_args(argv)
    # read configfile
    config_parser = make_configparser(options.conf)
    if config_parser.has_section('default'):
        soft_defaults = dict(config_parser.items("default"))
    else:
        soft_defaults = {}
    # parse the rest
    parser = make_parser(soft_defaults)
    # setup the logger
    logger = make_logger(options)
    rstscriptserver = RstScriptServer(options,parser,logger)
    rstscriptserver.start()

if __name__ == '__main__':
    main()
