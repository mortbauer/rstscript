import os
import sys
import ipdb
import time
import socket
import logging
import argparse
import colorama
import rstscript
import threading
import socketserver

from rstscript import simpledaemon

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

class ThreadedEchoRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        # Echo the back to the client
        data = self.request.recv(1024)
        cur_thread = threading.currentThread()
        response = '%s: %s' % (cur_thread.getName(), data)
        time.sleep(5)
        self.request.send(response.encode('utf-8'))
        return

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
    daemonize = True

    def __init__(self,options,defaults,adress='/tmp/rstscript.sock'):
        self.options = options
        self.defaults = defaults
        self.logger = make_logger(options)
        self.sockfile = adress
        self.server = socketserver.ThreadingUnixStreamServer(self.sockfile,ThreadedEchoRequestHandler)
        #self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)

    def run(self):
        self.server.serve_forever()
        #self.thread.start()
        #self.logger.info('Server loop running in thread: {0}'.format(self.thread.getName()))

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
    # setup the logger
    rstscriptserver = RstScriptServer(options,soft_defaults)
    rstscriptserver.start()

if __name__ == '__main__':
    main()
