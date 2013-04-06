import os
import sys
import yaml
import time
import socket
import select
import pkgutil
import argparse
import rstscript
import platform
import threading

from rstscript import kernel
from rstscript import client
from rstscript.utils import import_plugins, ColorizingStreamHandler

def make_server_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser],add_help=False)

    parser.add_argument("--nomatplotlib",action='store_true', dest="nomatplotlib",
            help="disable the import of matplotlib, can cause problems if plot nevertheless then")
    parser.add_argument("--pdb",action='store_true', dest="pdb",
            help="debug with pdb or ipdb")
    parser.add_argument( "--foreground", action="store_true", default=False,
                    help="don\'t detach from terminal")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
            help="run in debugging mode, equivalent to -l debug")
    parser.add_argument('-l','--loglevel',dest='loglevel', default='WARNING',
            help='specify the logging level')
    parser.add_argument('--version', action='version', version=rstscript.__version__)

    subparsers = parser.add_subparsers(dest='command')
    start = subparsers.add_parser('start',help='start the server')
    stop = subparsers.add_parser('stop',help='stop the server')
    restart = subparsers.add_parser('restart',help='retstart the server')
    status = subparsers.add_parser('status',help='get the server status')

    return pre_parser,parser


def make_client_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('-i','--input', nargs='?',
            help='rstscript source file')
    parser.add_argument("-ow", dest="woutput", nargs='?',
            help="output file for weaving")
    parser.add_argument('--noweave',action='store_true', default=False,
            dest='noweave', help='don\'t weave the document')
    parser.add_argument("-ot", dest="toutput", default=None, nargs='?',
            help="output file for tangling")
    parser.add_argument("--figure-directory", dest='figdir',
                    action="store", default='_figures',
                    help="path to store produced figures")
    parser.add_argument('--plugindir',action='store',
            default=os.path.join(default_configdir,'plugins'),
            help='specify the plugin directory')

    parser.add_argument("--ipython-connection",default=None, nargs='?',
            help="connect to running ipython kernel")

    parser.add_argument("-r", "--rebuild", action="store_true", default=False,
            help="force a rebuild of the project although it might be already stored")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
            help="run in debugging mode, equivalent to -l debug")
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
            help='disable all output, won\'t guarante that i won\'t crash though')
    parser.add_argument('-l','--loglevel',dest='loglevel', default='WARNING',
            help='specify the logging level')
    parser.add_argument('--no-plugins',action='store_true',
            help='don\'d load any plugin')
    parser.add_argument('--no-daemon',dest='nodaemon',default=False,action='store_true',
            help='don\'d query the daemon, but process locally')
    parser.add_argument('--version', action='version', version=rstscript.__version__)
    parser.add_argument('--defaults',dest='options', default=None,nargs='?',
            help='a valid json value will be used as default chunk options')
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
            f.write(pkgutil.get_data(__name__,'defaults/config.json'))
        return True
    elif userinput == 'n':
        return False


def server_main(argv=None):
    from rstscript import daemonize
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_server_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    # parse main args
    configs.update(vars(parser.parse_args(remaining_argv)))
    # lazy create a daemonizedserver object
    daemon = kernel.RSTDaemon(configs)
    # create the client
    mclient = client.Client(configs['host'],configs['port'])
    mclient.connect()

    def startserver():
        try:
            daemon.start()
            if mclient.ping():
                return True
        except daemonize.DaemonizeAlreadyStartedError as e:
            raise

    def stopserver():
        # innproc communication
        mclient.stop()
        return True

    if configs['command'] == 'stop':
        stopserver()
    elif configs['command'] == 'start':
        startserver()
    elif configs['command'] == 'restart':
        print('not implemented yes, run sto and start manually')
    elif configs['command'] == 'status':
        if mclient.ping():
            print('server is running')
        else:
            print('server seems down')

    mclient.close()

def run_locally(options):
    import logging
    from rstscript.litrunner import Litrunner
    if not options.get('quiet'):
        # getlogger
        logger = logging.getLogger('rstscript')
        def testhandlers(logger):
            for handler in logger.handlers:
                if isinstance(handler,ColorizingStreamHandler):
                    return True
        # don't add the handler a second time if somebody calls this function a
        # second time
        if not testhandlers(logger):
            handler = ColorizingStreamHandler(sys.stderr)
            formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        if options.get('debug'):
            logger.setLevel('DEBUG')
        else:
            logger.setLevel(getattr(logging,options.get(
                'loglevel','WARNING').upper(),'WARNING'))
    # load plugins
    plugins = import_plugins(options.get('plugindir',''),logger)
    # do the work
    try:
        L = Litrunner(options,logger)
    except Exception as e:
        logger.exception('an unexpected error occured')

    return L



def client_main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_client_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(yaml.load(open(configs['conf'],'r')))
    # parse main args
    mainopts = parser.parse_args(remaining_argv)
    configs.update(vars(mainopts))
    # parse default options
    if configs['options']:
        try:
            o = eval(configs['options'])
            if type(o) != dict:
                raise ValueError
            configs['options'] = o 
        except ValueError:
            print('couldn\'t evaluate defaults please check again\n',file=sys.stderr)
            configs['options'] = {}
    # add the source directory to the config
    configs['rootdir'] = os.path.abspath('.')
    # make the file paths absolute
    for x in ('input','woutput','toutput'):
        if configs[x] and not os.path.isabs(configs[x]) :
            configs[x] = os.path.join(configs['rootdir'],configs[x])
    # make the figdir absolute to the weaveing output if not already absolute
    if not os.path.isabs(configs['figdir']):
        configs['figdir'] = os.path.join(os.path.split(
            configs['woutput'])[0],configs['figdir'])
    # if no input or output provided use stdin and stdout
    if not configs['input']:
        if os.isatty(0) or platform.system() == 'Windows': # i think there are no pipes in windows
            raise rstscript.RstscriptException('you need to specify a input filename with "-i"')

    if configs['debug']:
        configs['loglevel'] = 'DEBUG'

    if not configs['nodaemon']: # Connect to the server
        if platform.system() == 'Windows':
            print('you can\'t run rstscript as a daemon'
            'on windows, use the "--no-daemon" option\n',file=sys.stderr)
            sys.exit(1)

        mclient = client.Client(configs['host'],configs['port'])
        mclient.connect()

        # Send the data
        t1 = time.time()
        mclient.run(configs)
        print('elapsed time',time.time()-t1)

        mclient.close()
    else: # process locally
        return run_locally(configs)


