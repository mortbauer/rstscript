import os
import sys
import yaml
import socket
import select
import pkgutil
import logging
import argparse
import colorama
import rstscript

from rstscript import daemonize
from rstscript import server

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

def make_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.yml'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--restart',action='store_true',help='start the server')
    group.add_argument('--stop',action='store_true',help='stop the server')

    parser.add_argument("--pdb",action='store_true', dest="pdb",
            help="debug with pdb")
    parser.add_argument('--plugindir',action='store',
            default=os.path.join(default_configdir,'plugins'),
            help='specify the plugin directory')
    parser.add_argument('--no-plugins',action='store_true',
            help='disable all plugins')
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                    help="Run in debugging mode.")
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                    help='Disable stdout logging')

    parser.add_argument("-f", "--force", action="store_true", default=False,
                    help="will override existing files without asking")
    parser.add_argument('-l','--log-level',dest='loglevel', default='WARNING',
                    help='Specify the logging level')
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
            f.write(pkgutil.get_data(__name__,'defaults/config.yml'))
        return True
    elif userinput == 'n':
        return False

def make_logger(logname,logfile=None,debug=False,quiet=True,loglevel='WARNING',
        logmaxmb=0,logbackups=1):
    logger = logging.getLogger(logname)
    # setup the app logger
    handlers = []
    if not logmaxmb:
        handlers.append(logging.FileHandler(logfile))
    else:
        from logging.handlers import RotatingFileHandler
        handlers.append(RotatingFileHandler(logfile,
            maxBytes=logmaxmb * 1024 * 1024, backupCount=logbackups))
    if not quiet or debug:
        # also log to stderr
        #handlers.append(logging.StreamHandler(sys.stdout))
        handlers.append(ColorizingStreamHandler(sys.stdout))
    formatter = logging.Formatter(
            '%(levelname)s %(asctime)s %(name)s: %(message)s')
    for handler in handlers:
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

def main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    configs.update(vars(parser.parse_args(remaining_argv)))
    # make the logger
    logger = make_logger('rstscript.server',configs['logfile'],
            loglevel=configs['loglevel'],debug=configs['debug'])

    d = daemonize.SocketServerDaemon(configs['socketfile'],configs['pidfile'],
            logger,server.RstscriptHandler)

    if configs['restart']:
        try:
            d.stop()
            d.start()
        except:
            raise
    elif configs['stop']:
        try:
            d.stop()
        except daemonize.DaemonizeNotRunningError as e:
            logger.info(e)
    else:
        try:
            d.start()
        except daemonize.DaemonizeAlreadyStartedError as e:
            logger.info(e)

        ## create the server object
    #rstscriptserver = RstScriptServer(**configs)
    #if configs['start']:
        #rstscriptserver.start()
    #elif configs['stop']:
        #rstscriptserver.stop()
    #elif configs['restart']:
        #rstscriptserver.stop()
        #rstscriptserver.start()


if '__main__' == __name__:
    main()
