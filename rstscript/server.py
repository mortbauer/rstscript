import os
import sys
import time
import yaml
import ipdb
import logging
import pkgutil
import argparse
import rstscript
import threading
import socketserver

from rstscript import simpledaemon

class ThreadedEchoRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        # Echo the back to the client
        data = self.request.recv(1024)
        cur_thread = threading.currentThread()
        response = '%s: %s' % (cur_thread.getName(), data)
        time.sleep(5)
        self.request.send(response.encode('utf-8'))
        return

class RstScriptServer(simpledaemon.Daemon):

    def __init__(self,socketfile=None,pidfile=None,logfile=None,
            debug=False,quiet=False,loglevel='info',logmaxmb=0,
            foreground=False,uid=os.getuid(),gid=os.getgid(),**args):
        self.uid = uid
        self.gid = gid
        self.logmaxmb = logmaxmb
        self.daemonize = not foreground
        self.logger = make_logger(logfile=logfile,debug=debug,quiet=quiet,loglevel=loglevel)
        self.loglevel = loglevel
        self.logfile = logfile
        self.sockfile = socketfile
        self.pidfile = pidfile
        self.started = False
        #self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)

    def start(self):
        for f in (self.pidfile,self.sockfile):
            if os.path.exists(f):
                self.started = True
                self.logger.info('server seems already running, found "{0}"'.format(f))
                break
        if not self.started:
            self.server = socketserver.ThreadingUnixStreamServer(self.sockfile,ThreadedEchoRequestHandler)
            super(self.__class__,self).start()

    def stop(self):
        if super(self.__class__,self).stop():
            if os.path.exists(self.sockfile):
                os.remove(self.sockfile)
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

    def run(self):
        self.server.serve_forever()
        #self.thread.start()
        #self.logger.info('Server loop running in thread: {0}'.format(self.thread.getName()))

def make_preparser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.yml'),
            help="specify config file")
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
    group.add_argument('--start',action='store_true',help='start the server')
    group.add_argument('--stop',action='store_true',help='stop the server')
    group.add_argument('--restart',action='store_true',help='restart the server')
    return parser


def make_logger(logfile=None,debug=False,quiet=False,loglevel='WARNING',logmaxmb=0,logbackups=1):
    logger = logging.getLogger('rstscript.server')
    # setup the app logger
    handlers = []
    if not logmaxmb:
        handlers.append(logging.FileHandler(logfile))
    else:
        from logging.handlers import RotatingFileHandler
        handlers.append(RotatingFileHandler(logfile, maxBytes=logmaxmb * 1024 * 1024, backupCount=logbackups))
    if not quiet:
        # also log to stderr
        handlers.append(logging.StreamHandler())
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(name)s: %(message)s')
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

def main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser = make_preparser()
    configs.update(vars(pre_parser.parse_args(argv)))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    # create the server object
    rstscriptserver = RstScriptServer(**configs)
    if configs['start']:
        rstscriptserver.start()
    elif configs['stop']:
        rstscriptserver.stop()
    elif configs['restart']:
        rstscriptserver.stop()
        rstscriptserver.start()


if __name__ == '__main__':
    main()
