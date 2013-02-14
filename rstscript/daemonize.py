"""Generic linux daemon base class for python 3.x."""

import os
import sys
import time
import atexit
import signal

class Daemon:
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self, pidfile,logger):
        self.pidfile = pidfile
        self.logger = logger

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""

        try:
            pid = os.fork()
        except OSError as err:
            self.logger.error('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)

        # instead of exiting the parent process, just shield the further
        # daemonizing from it, so it can continue in foreground
        if not pid:
            self.logger.info('fork #1 done')
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
                self.logger.error('fork #2 failed: {0}\n'.format(err))
                sys.exit(1)

            self.logger.info('fork #2 done')

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
            atexit.register(os.remove,self.pidfile)

            pid = str(os.getpid())
            with open(self.pidfile,'w+') as f:
                f.write(pid + '\n')

            self.logger.info('redirection of std\'s done')
            self.run()

    def start(self):
        """Starts the run method daemonized

        returnes True for the parent process on success
        and False on fail and for the child process
        """

        # Check for a pidfile to see if the daemon already runs
        if os.path.exists(self.pidfile):
            self.logger.warning("pidfile {0} already exist".format(self.pidfile))
            return False
        else:
            # Start the daemon
            pid = os.getpid()
            self.daemonize()
            # only execute for parent
            if os.getpid() == pid:
                # wait until pidfile is written, which means that the daemon is
                # launched
                while not os.path.exists(self.pidfile):
                    time.sleep(0.01)
                self.logger.info('run succesfully daemonized, running on pid "{0}"'.
                        format(open(self.pidfile,'r').read()))
                return True
            else:
                return False

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            self.logger.warning("pidfile {0} does not exist".format(self.pidfile))
            # though we hadn't to do anything the daemon seems done so we can
            # start a new one or whatever
            return True
        else:
            # Try killing the daemon process
            try:
                for i in range(5):
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError as err:
                if err.errno == os.errno.ESRCH:
                    os.remove(self.pidfile)
                    self.logger.info('killed the daemon succesfully')
                    return True
                else:
                    self.logger.error('failed to kill the daemon: {0}'.format(err))
                    return False

    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""

