"""Generic linux daemon base class for python 3.x."""

import os
import sys
import abc
import time
import atexit
import signal

from rstscript import utils

class DaemonizeError(Exception):
    pass
class DaemonizeAlreadyStartedError(Exception):
    pass
class DaemonizeNotRunningError(Exception):
    pass

class Daemon(object,metaclass=abc.ABCMeta):
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile):
        self.pidfile = pidfile

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
            self.run()

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
            # catch incoming interupts and stop gracefully
            signal.signal(signal.SIGINT, self.interupt)
            if self.foreground:
                sys.excepthook = utils.info
                self.run()
            else:
                self.daemonize()
            # just exit for all childs if they ever will get that far
            if os.getpid() != pid:
                sys.exit(0)
            return True

    def interupt(self,signum, frame):
        self.stop()

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
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.1)
            except OSError as err:
                if err.errno == os.errno.ESRCH:
                    pid = open(self.pidfile).read().strip()
                    os.remove(self.pidfile)
                    return True
                else:
                    raise DaemonizeError('failed to stop the daemon: {0}'
                            .format(err.args))

    @abc.abstractmethod
    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""
