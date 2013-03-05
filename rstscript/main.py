import os
import sys
import yaml
import ujson
import pkgutil
import argparse
import rstscript
import platform


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

def make_server_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])

    subparsers = parser.add_subparsers(dest='command')
    start = subparsers.add_parser('start',help='start the server')
    stop = subparsers.add_parser('stop',help='stop the server')
    clean = subparsers.add_parser('clean',
            help='clean up the pid file if something went wrong')
    restart = subparsers.add_parser('restart',help='restart the server')

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
    from rstscript import server
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
    daemon = daemonize.SocketServerDaemon(configs,server.RstscriptHandler)
    # start/stop the server
    if configs['command'] == 'restart':
        try:
            daemon.stop()
            daemon.start()
        except:
            raise
            sys.exit(1)
    elif configs['command'] == 'stop':
        try:
            daemon.stop()
        except daemonize.DaemonizeNotRunningError as e:
            sys.stderr.write(str(e))
            sys.exit(1)
    elif configs['command'] == 'start':
        if not os.path.exists(configs['socketfile']):
            try:
                daemon.start()
            except daemonize.DaemonizeAlreadyStartedError as e:
                sys.stderr.write(str(e))
                sys.exit(1)
        else:
            sys.stderr.write('the socketfile "{0}" exists already, if you are'
                    'sure the server is down you can run "rstscriptd clean" to '
                    'remove it'.format(configs['socketfile']))
            sys.exit(1)
    elif configs['command'] == 'clean':
        sys.stderr.write('not implemented yet')

def run_locally(options):
    import logging
    from rstscript.daemonize import ColorizingStreamHandler
    from rstscript.litrunner import Litrunner
    if not options['quiet']:
        # getlogger
        logger = logging.getLogger('rstscript')
        handler = ColorizingStreamHandler(sys.stderr)
        formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if options['debug']:
            logger.setLevel('DEBUG')
        else:
            logger.setLevel(getattr(logging,options['loglevel'].upper(),'WARNING'))
        logger.addHandler(handler)
    # load plugins
    plugins = import_plugins(options['plugindir'],logger)
    # do the work
    try:
        L = Litrunner(options,logger)
        # now run the project
        L.run()
    except Exception as e:
        logger.error('an unexpected error occured "{0}"'.format(e))
        raise e


def client_main(argv=None):
    # read deafult configs
    configs = yaml.load(pkgutil.get_data(__name__,'defaults/config.yml').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    print(argv)
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
            o = ujson.loads(configs['options'])
            if type(o) == str:
                raise ValueError
            configs['options'] = o
        except ValueError:
            sys.stderr.write('couldn\'t parse default options '
            '"--defaults", please check again\n')
            configs['options'] = {}
    # add the source directory to the config
    configs['rootdir'] = os.path.abspath('.')
    # make the file paths absolute
    for x in ('input','woutput','toutput'):
        if configs[x] and not os.path.isabs(configs[x]) :
            configs[x] = os.path.join(configs['rootdir'],configs[x])
    # if no input or output provided use stdin and stdout
    if not configs['input']:
        if os.isatty(0) or platform.system() == 'Windows': # i think there are no pipes in windows
            raise rstscript.RstscriptException('you need to specify a input filename with "-i"')
        configs['input'] = '/proc/{0}/fd/0'.format(os.getpid())
    if not configs['woutput']:
        configs['woutput'] = '/proc/{0}/fd/1'.format(os.getpid())
        configs['quiet'] = True # well we pipe already something here so logger shut up

    if not configs['nodaemon']: # Connect to the server
        if platform.system() == 'Windows':
            sys.stderr.write('you can\'t run rstscript as a daemon'
            'on windows, use the "--no-daemon" option\n')
            sys.exit(1)
        import socket
        import select
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((configs['host'],configs['port']))
        except:
            sys.stderr.write('it seems like the server is down')
            sys.exit(1)

        sock.setblocking(0)

        # Send the data
        message = ujson.dumps([os.getpid(),configs])
        #print('\nSending : "%s"' % message)
        len_sent = sock.send(message.encode('utf-8'))

        # Receive a response
        ready = select.select([sock], [], [], 6)
        if ready:
            response = sock.recv(1024)
            #print('\nReceived: "%s"' % response.decode('utf-8'))
            # Clean up
        sock.close()
    else: # process locally
        sys.stderr.write('without a daemon, no caching will happen\n')
        run_locally(configs)


