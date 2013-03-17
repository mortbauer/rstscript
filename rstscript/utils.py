
import os
import sys
import logging
from logging import INFO, DEBUG, WARN, ERROR, FATAL
import zmq

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

TOPIC_DELIM="::" # delimiter for splitting topics on the receiving end.


class PUSHHandler(logging.Handler):
    """A basic logging handler that emits log messages through a PUB socket.

    Takes a PUB socket already bound to interfaces or an interface to bind to.

    Example::

    sock = context.socket(zmq.PUB)
    sock.bind('inproc://log')
    handler = PUBHandler(sock)

    Or::

    handler = PUBHandler('inproc://loc')

    These are equivalent.

    Log messages handled by this handler are broadcast with ZMQ topics
    ``this.root_topic`` comes first, followed by the log level
    (DEBUG,INFO,etc.), followed by any additional subtopics specified in the
    message by: log.debug("subtopic.subsub::the real message")
    """
    root_topic=""
    socket = None

    formatters = {
        logging.DEBUG: logging.Formatter(
        "%(levelname)s %(name)s:%(lineno)d - %(message)s\n"),
        logging.INFO: logging.Formatter("%(message)s\n"),
        logging.WARN: logging.Formatter(
        "%(levelname)s %(name)s:%(lineno)d - %(message)s\n"),
        logging.ERROR: logging.Formatter(
        "%(levelname)s %(name)s:%(lineno)d - %(message)s - %(exc_info)s\n"),
        logging.CRITICAL: logging.Formatter(
        "%(levelname)s %(name)s:%(lineno)d - %(message)s\n")}

    def __init__(self, socket, context=None):
        logging.Handler.__init__(self)
        self.socket = socket

    def format(self,record):
        """Format a record."""
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        """Emit a log message on my socket."""

        self.socket.send_json(['log', self.format(record)])

def info(type, value, tb):
    # http://stackoverflow.com/a/242531/1607448
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
    # we are in interactive mode or we don't have a tty-like
    # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback
        # we are NOT in interactive mode, print the exception…
        traceback.print_exception(type, value, tb)

def import_plugins(plugindir,logger):
    if os.path.exists(plugindir):
        sys.path.insert(0, plugindir)
        # get all py files and strip the extension
        pyfiles = [x[:-3] for x in os.listdir(plugindir) if x.endswith('.py')]
        # import the modules which we found in the plugin path
        plugin_modules = {}
        for module in pyfiles:
            try:
                mod = __import__(module)
                if not hasattr(mod, 'setup'):
                    logger.warn('plugin %r has no setup() function; '
                            'won\'t load it' % extension)
                else:
                    mod.setup()
                    plugin_modules[module] = mod
            except Exception as e:
                logger.error('skipping plugin "{0}": {1}'.format(module,e))

        # remove added paths again
        sys.path.remove(plugindir)
        logger.info('loaded "{1}" plugins from "{0}"'.format(plugindir,len(plugin_modules)))
        return plugin_modules
    else:
        logger.warning('plugindir "{0}" doesn\'t exist'.format(plugindir))
        return {}

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


def enum(**enums):
    return type('Enum', (), enums)

class Logger(object):
    LEVELS = enum(DEBUG=0,INFO=1,WARN=2,ERROR=3,EXCEPTION=4)
    def __init__(self,socket,loglevel='WARN'):
        self.socket = socket
        self.loglevel = loglevel
        self.level = getattr(self.LEVELS,loglevel,2)

    def debug(self,msg):
        if self.level <= self.LEVELS.DEBUG:
            self.socket.send_json(['log','DEBUG::{0}'.format(msg)])
    def info(self,msg):
        if self.level <= self.LEVELS.INFO:
            self.socket.send_json(['log','INFO::{0}'.format(msg)])
    def warn(self,msg):
        if self.level <= self.LEVELS.WARN:
            self.socket.send_json(['log','WARN::{0}'.format(msg)])
    def error(self,msg):
        if self.level <= self.LEVELS.ERROR:
            self.socket.send_json(['log','ERROR::{0}'.format(msg)])
    def exception(self,msg):
        if self.level <= self.LEVELS.EXCEPTION:
            self.socket.send_json(['log','EXCEPTION::{0}'.format(msg)])

