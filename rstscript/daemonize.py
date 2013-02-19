"""Generic linux daemon base class for python 3.x."""

import os
import sys
import abc
import time
import copy
import atexit
import signal
import socket
import logging
import socketserver

from rstscript import main

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

class DaemonizeError(Exception):
    pass
class DaemonizeAlreadyStartedError(Exception):
    pass
class DaemonizeNotRunningError(Exception):
    pass

class Daemon(object,metaclass=abc.ABCMeta):
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile,logger=None,foreground=False):
        self.pidfile = pidfile
        self.logger = logger
        self.debug = foreground

    def daemonize(self):
        try:
            pid = os.fork()
        except OSError as err:
            raise DaemonizeError('fork #1 failed: {0}\n'.format(err.args))

        # instead of exiting the parent process, just shield the further
        # daemonizing from it, so it can continue in foreground
        if not pid:
            # decouple from parent environment
            os.chdir('/')
            os.setsid()
            os.umask(0)

            # do second fork
            try:
                pid = os.fork()
                if pid > 0:
                    # exit from second parent
                    sys.exit(0)
            except OSError as err:
                raise DaemonizeError('fork #2 failed: {0}\n'.format(err.args))

            # redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            si = open(os.devnull, 'r')
            so = open(os.devnull, 'a+')
            se = open(os.devnull, 'a+')

            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())

            # write pidfile
            with open(self.pidfile,'w+') as f:
                f.write(str(os.getpid())+ '\n')
            # if daemon process end from alone we want the pid file removed
            # therefore let's register with atexit
            atexit.register(os.remove,self.pidfile)
            try:
                self.run()
            except Exception as e:
                self.logger.error(e)
    def start(self):
        """Starts a daemonized process

        returns the pid of the child for the parent process on success
        and False on fail and for the child process
        """

        # Check for a pidfile to see if the daemon already runs
        if os.path.exists(self.pidfile):
            msg = "pidfile {0} already exist".format(self.pidfile)
            raise DaemonizeAlreadyStartedError(msg)
        else:
            # Start the daemon
            pid = os.getpid()
            if not self.foreground:
                self.daemonize()
            else:
                sys.excepthook = info
                self.run()
            # only execute for parent
            if os.getpid() == pid:
                # wait until pidfile is written, which means that the daemon is
                # launched, or timeout reached, could be some race condition or
                # so, since what happens if the daemon run ends before I got
                # it?
                for i in range(5):
                    try:
                        child_pid = open(self.pidfile,'r').read().strip()
                        if self.logger:
                            self.logger.info('run succesfully daemonized, running on pid "{0}"'.
                                    format(child_pid))
                        return child_pid
                    except OSError:
                        time.sleep(0.01)
                raise DaemonizeError('daemon couldn\'t be launched, timeout reached')
            else:
                sys.exit(0) # just exit for all childs if they ever will get that far

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            msg = "pidfile {0} does not exist".format(self.pidfile)
            # though we hadn't to do anything the daemon seems done so we can
            # start a new one or whatever
            raise DaemonizeNotRunningError(msg)
        else:
            # Try killing the daemon process
            try:
                for i in range(5):
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError as err:
                if err.errno == os.errno.ESRCH:
                    pid = open(self.pidfile).read().strip()
                    os.remove(self.pidfile)
                    if self.logger:
                        self.logger.info('stopped the daemon "{0}" succesfully'
                                .format(pid))
                    return True
                else:
                    raise DaemonizeError('failed to stop the daemon: {0}'
                            .format(err.args))

    @abc.abstractmethod
    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""
class RstscriptServer(socketserver.ThreadingMixIn,socketserver.TCPServer):
    def __init__(self, configs, RequestHandlerClass, logger):
        self.logger = logger
        self.plugins = main.import_plugins(
                configs['plugindir'],self.logger)
        self.projects = {}
        self.configs = configs
        socketserver.TCPServer.__init__(self,
                (configs['host'],configs['port']),
                RequestHandlerClass)
        # import maplotlib if not disabled, because backend must be choosen
        # before pyplot get's imported
        if not self.configs['nomatplotlib']:
            try:
                import matplotlib
                matplotlib.use('Agg')
            except:
                self.logger.error('couldn\'t import matplotlib')
class SocketServerDaemon(Daemon):

    def __init__(self,configs,handler):
        self.logger = make_logger('rstscript.server',configs['logfile'],
            loglevel=configs['loglevel'],debug=configs['debug'])
        self.sockfile = configs['socketfile']
        self.pidfile = configs['pidfile']
        self.handler = handler
        self.foreground = configs['foreground']
        self.configs = configs

    def start(self):
        if super().start():
            self.logger.info('listening on "{0}"'.format(self.sockfile))

    def stop(self):
        if super().stop():
            pass

    def _del(self,path):
        try:
            os.remove(path)
        except:
            pass

    def run(self):
        # hook up to remove the socket if the server ends regulary, won't
        # happen if you just kill the process
        atexit.register(self._del,self.sockfile)
        self.server = RstscriptServer(self.configs,self.handler,self.logger)
        self.server.serve_forever()
