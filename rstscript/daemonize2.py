"""\
        Daemon base and control class.

This file contains the daemon base class for a UNIX daemon and the control
class for it. See test logic at the end of file and test_daemon.py to
understand how to use it.\
        """

import sys, os, time, atexit, signal

# -- generic daemon base class ------------------------------------------ #

class daemon_base:
    """A generic daemon base class.

    Usage: subclass this class and override the run() method.
    """
    def __init__(self, pidfile, workpath='/'):
        """Constructor.

        We need the pidfile for the atexit cleanup method.
        The workpath is the path the daemon will operate
        in. Normally this is the root directory, but can be some
        data directory too, just make sure it exists.
        """
        self.pidfile = pidfile
        self.workpath = workpath

    def perror(self, msg, err):
        """Print error message and exit. (helper method)
        """
        msg = msg + '\n'
        sys.stderr.write(msg.format(err))
        sys.exit(1)

    def daemonize(self):
        """Deamonize calss process. (UNIX double fork mechanism).
        """
        if not os.path.isdir(self.workpath):
            self.perror('workpath does not exist!', '')

        try: # exit first parent process
            pid = os.fork()
            #if pid > 0: sys.exit(0)
        except OSError as err:
            self.perror('fork #1 failed: {0}', err)
        # only run for child process
        if not pid:
            # decouple from parent environment
            try: os.chdir(self.workpath)
            except OSError as err:
                self.perror('path change failed: {0}', err)

            os.setsid()
            os.umask(0)

            try: # exit from second parent
                pid = os.fork()
                if pid > 0: sys.exit(0)
            except OSError as err:
                self.perror('fork #2 failed: {0}', err)

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
            atexit.register(os.remove, self.pidfile)
            pid = str(os.getpid())
            with open(self.pidfile,'w+') as f:
                f.write(pid + '\n')
            self.run()

    def run(self):
        """Worker method.

        It will be called after the process has been daemonized
        by start() or restart(). You'll have to overwrite this
        method with the daemon program logic.
        """
        while True:
            time.sleep(1)

# -- daemon control class ----------------------------------------------- #

class daemon_ctl:
    """Control class for a daemon.

    Usage:
        >>>	dc = daemon_ctl(daemon_base, '/tmp/foo.pid')
    >>>	dc.start()

    This class is the control wrapper for the above (daemon_base)
    class. It adds start/stop/restart functionality for it withouth
    creating a new daemon every time.
    """
    def __init__(self, daemon, pidfile, workdir='/'):
        """Constructor.

        @param daemon: daemon class (not instance)
        @param pidfile: daemon pid file
        @param workdir: daemon working directory
        """
        self.daemon = daemon
        self.pidfile = pidfile
        self.workdir = workdir

    def start(self):
        """Start the daemon.
        """
        try: # check for pidfile to see if the daemon already runs
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError: pid = None

        if pid:
            message = "pidfile {0} already exist. " + \
                    "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)

        # Start the daemon
        d = self.daemon(self.pidfile, self.workdir)
        d.daemonize()

    def stop(self):
        """Stop the daemon.

        This is purely based on the pidfile / process control
        and does not reference the daemon class directly.
        """
        try: # get the pid from the pidfile
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError: pid = None

        if not pid:
            message = "pidfile {0} does not exist. " + \
                    "Daemon not running?\n"
            sys.stderr.write(message.format(self.pidfile))
            return # not an error in a restart

        try: # try killing the daemon process
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print (str(err.args))
                sys.exit(1)

    def restart(self):
        """Restart the daemon.
        """
        self.stop()
        self.start()

# -- test logic --------------------------------------------------------- #

if __name__ == '__main__':
    """Daemon test logic.

    This logic must be called as seperate executable (i.e. python3
    daemon.py start/stop/restart).	See test_daemon.py for
    implementation.
    """
    usage = 'Missing parameter, usage of test logic:\n' + \
            ' % python3 daemon.py start|restart|stop\n'
    if len(sys.argv) < 2:
        sys.stderr.write(usage)
        sys.exit(2)

    pidfile = '/tmp/test_daemon.pid'
    dc = daemon_ctl(daemon_base, pidfile)

    if sys.argv[1] == 'start':
        dc.start()
    elif sys.argv[1] == 'stop':
        dc.stop()
    elif sys.argv[1] == 'restart':
        dc.restart()
