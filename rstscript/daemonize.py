"""Generic linux daemon base class for python 3.x."""

import os
import sys
import abc
import time
import atexit
import signal
import socketserver

class DaemonizerException(Exception):
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
            raise DaemonizerException('fork #1 failed: {0}\n'.format(err.args))

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
                raise DaemonizerException('fork #2 failed: {0}\n'.format(err.args))

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
            raise DaemonizerException(msg)
        else:
            # Start the daemon
            pid = os.getpid()
            if not self.foreground:
                self.daemonize()
            else:
                from rstscript import debug
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
                raise DaemonizerException('daemon couldn\'t be launched, timeout reached')
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
            raise DaemonizerException(msg)
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
                    raise DaemonizerException('failed to stop the daemon: {0}'
                            .format(err.args))

    @abc.abstractmethod
    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""
class SocketServerDaemon(Daemon):

    def __init__(self,socketfile,pidfile,logger,handler,foreground=False):
        self.logger = logger
        self.sockfile = socketfile
        self.pidfile = pidfile
        self.started = False
        self.handler = handler
        self.foreground = foreground

    def start(self):
        # Check for a sockfile to see if the daemon already runs
        if os.path.exists(self.sockfile):
            msg = "sockfile {0} already exist".format(self.sockfile)
            self.logger.warning(msg)
            raise DaemonizerException(msg)
        else:
            if super().start():
                self.logger.info('listening on "{0}"'.format(self.sockfile))

    def stop(self):
        # Check for a sockfile to see if the daemon already runs
        if not os.path.exists(self.sockfile):
            msg = "sockfile {0} doesn\'t exist".format(self.sockfile)
            self.logger.warning(msg)
            raise DaemonizerException(msg)
        else:
            # register cleanup on exit
            if super().stop():
                os.remove(self.sockfile)

    def run(self):
        self.server = socketserver.ThreadingUnixStreamServer(self.sockfile,self.handler)
        atexit.register(os.remove,self.sockfile)
        self.server.serve_forever()
