import os
import sys
import time
import ujson
import socket
import select
import pkgutil
import argparse
import rstscript

from rstscript import daemonize
from rstscript import server

def make_color_handler():
    import logging
    import colorama
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
    return ColorizingStreamHandler(sys.stdout)
def make_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-c", "--conf", dest="conf",
            default=os.path.join(default_configdir,'config.json'),
            help="specify config file")

    parser = argparse.ArgumentParser(parents=[pre_parser])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--restart',action='store_true',help='start the server')
    group.add_argument('--stop',action='store_true',help='stop the server')

    parser.add_argument("--pdb",action='store_true', dest="pdb",
            help="debug with pdb")
    parser.add_argument('--plugindir',action='store',
            default=os.path.join(default_configdir,'plugins'),
            help='specify the plugin directory')
    parser.add_argument('--no-plugins',action='store_true',
            help='disable all plugins')
    parser.add_argument( "--foreground", action="store_true", default=False,
                    help="don\'t detach")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                    help="Run in debugging mode.")
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                    help='Disable stdout logging')

    parser.add_argument("-f", "--force", action="store_true", default=False,
                    help="will override existing files without asking")
    parser.add_argument('-l','--log-level',dest='loglevel', default='WARNING',
                    help='Specify the logging level')
    parser.add_argument('--version', action='version', version=rstscript.__version__)

    parser.add_argument('input', nargs='?', help='rstscript source file')

    parser.add_argument('-t',action='store_true',dest='tangle',help='tangle the document')

    parser.add_argument("-ot", dest="toutput", nargs='?',
                    help="output file for tangling")

    parser.add_argument('--noweave',action='store_true',dest='noweave',
            help='don\'t weave the document')

    parser.add_argument("-ow", dest="woutput", nargs='?',
                    help="output file for weaving")

    parser.add_argument("--processor", dest="processor",default='python',
                    help="default code processor")
    parser.add_argument("--formatter", dest="formatter",default='compact',
                    help="default code formatter")
    parser.add_argument("--figure-directory", dest='figdir',
                    action="store", default='_figures',
                    help="path to store produced figures")
    parser.add_argument("-g","--figure-format", dest="figfmt",
                    action="store", default="png",
                    help="Figure format for matplolib graphics: Defaults to"
                        "'png' for rst and Sphinx html documents and 'pdf' "
                        "for tex")
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

def parse_through_args(proc_form_args):
    if '--formatter-opts' in proc_form_args:
        i_f = proc_form_args.index('--formatter-opts')
    else:
        i_f = 0
    if '--processor-opts' in proc_form_args:
        i_p = proc_form_args.index('--processor-opts')
    else:
        i_p = 0
    # if there are remaining arguments but non of the keys is specified i will
    # take them for both
    proc_args = []
    form_args = []
    if i_f == 0 and i_p == 0:
        proc_args = proc_form_args
        form_args = proc_form_args
    elif i_f > i_p:
        proc_args = proc_form_args[i_p+1:i_f]
        form_args = proc_form_args[i_f+1:]
    elif i_f < i_p:
        proc_args = proc_form_args[i_p+1:]
        form_args = proc_form_args[i_f+1:i_p]
    proc_args.extend(proc_form_args[:min(i_f,i_p)])
    form_args.extend(proc_form_args[:min(i_f,i_p)])
    return proc_args,form_args

def main(argv=None):
    # read deafult configs
    configs = ujson.loads(pkgutil.get_data(__name__,'defaults/config.json').decode('utf-8'))
    if not argv:
        argv = sys.argv[1:]
    # parse the arguments
    pre_parser, parser = make_parser()
    options, remaining_argv = pre_parser.parse_known_args(argv)
    configs.update(vars(options))
    # read configfile
    if not os.path.exists(configs['conf']):
        make_initial_setup(configs['conf'])
    else:
        configs.update(ujson.load(open(configs['conf'],'r')))
    # parse main args
    mainopts, throughargs = parser.parse_known_args(remaining_argv)
    configs.update(vars(mainopts))
    # parse through passing args
    configs['proc_args'], configs['form_args'] = ([],[])
    #configs['proc_args'], configs['form_args'] = parse_through_args(throughargs)
    # add the source directory to the config
    configs['rootdir'] = os.path.abspath('.')
    # make the file paths absolute
    for x in ('input','woutput','toutput'):
        if configs[x] and not os.path.isabs(configs[x]) :
            configs[x] = os.path.join(configs['rootdir'],configs[x])

    # add current tty info
    for std in ('stdin','stdout','stderr'):
        fileno = getattr(sys,std).fileno()
        if os.isatty(fileno):
            configs[std] = os.ttyname(fileno)

    # lazy create a daemonizedserver object
    daemon = lambda configs: daemonize.SocketServerDaemon(configs,server.RstscriptHandler)

    # start/stop the server
    if configs['restart']:
        d = daemon(configs)
        try:
            d.stop()
            d.start()
        except:
            raise
    elif configs['stop']:
        d = daemon(configs)
        try:
            d.stop()
        except daemonize.DaemonizeNotRunningError as e:
            sys.stderr.write(str(e))
    else:
        if not os.path.exists(configs['socketfile']):
            d = daemon(configs)
            try:
                d.start()
            except daemonize.DaemonizeAlreadyStartedError as e:
                sys.stderr.write(str(e))

    if not configs['stop']:
        # Connect to the server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(configs['socketfile'])
        sock.setblocking(0)

        # Send the data
        message = ujson.dumps(configs)
        #print('\nSending : "%s"' % message)
        len_sent = sock.send(message.encode('utf-8'))

        # Receive a response
        ready = select.select([sock], [], [], 6)
        if ready:
            response = sock.recv(1024)
            #print('\nReceived: "%s"' % response.decode('utf-8'))
            # Clean up
        sock.close()

        ## create the server object
    #rstscriptserver = RstScriptServer(**configs)
    #if configs['start']:
        #rstscriptserver.start()
    #elif configs['stop']:
        #rstscriptserver.stop()
    #elif configs['restart']:
        #rstscriptserver.stop()
        #rstscriptserver.start()

if '__main__' == __name__:
    t1 = time.time()
    main()
    #print('took me "{0}" sec in main'.format(time.time()-t1))
