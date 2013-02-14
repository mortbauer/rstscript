import os
import sys
import socket
import select
import argparse
import rstscript


def make_parser():
    default_configdir = os.path.join(os.getenv("XDG_CONFIG_HOME",''),"rstscript")
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--start',action='store_true',help='start the server')
    group.add_argument('--stop',action='store_true',help='stop the server')

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

    parser.add_argument("-f", "--force", action="store_true", default=False,
                    help="will override existing files without asking")
    parser.add_argument('-l','--log-level',dest='loglevel', default='WARNING',
                    help='Specify the logging level')
    parser.add_argument('--version', action='version', version=rstscript.__version__)

    parser.add_argument('-i','--input', dest='input',type=argparse.FileType('rt'), nargs=1,
                    required=True,default=[sys.stdin], help='rstscript source file')

    parser.add_argument('-t',action='store_true',dest='tangle',help='tangle the document')

    parser.add_argument("-ot", dest="toutput",
                        type=argparse.FileType('wt'), nargs='?',
                    help="output file for tangling")

    parser.add_argument('--noweave',action='store_true',dest='noweave',
            help='don\'t weave the document')

    parser.add_argument("-ow", dest="woutput",
                        type=argparse.FileType('wt'), nargs='?',
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
    return parser


# Connect to the server
#address = '/tmp/socketserver.sock'

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
    parser = make_parser()
    configs.update(vars(parser.parse_args(argv)))
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


def main(argv=None,address='/tmp/rstscript.sock'):
    # invoked from commandline or through import
    if not argv:
        argv = sys.argv[1:]
    # make the parser
    parser = make_parser()
    # parse the options
    options = vars(parser.parse_args(argv))
    # create the socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.setblocking(0)
    try:
        sock.connect(address)
    #except socket.ConnectionRefusedError:
    except Exception as e:
        print('exception',e)
        # server seems down
        start_server()
        sock.connect(address)

    len_sent = sock.send(b'hello server')

    # Receive a response
    ready = select.select([sock], [], [], 6)
    if ready:
        response = sock.recv(1024)
        print('Received: "%s"' % response)
        # Clean up
        sock.close()




if '__main__' == __name__:
    main()
