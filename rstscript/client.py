import os
import sys
import socket
import select
import argparse
import rstscript


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                    action="store", default='',
                    help="Optional directory containing rstscript plugin"
                        " files.")
    parser.add_argument('--no-plugins',action='store_true',
                    help='disable all plugins')
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                    help="Run in debugging mode.")
    parser.add_argument("-f", "--force", action="store_true", default=False,
                    help="will override existing files without asking")
    parser.add_argument('-l','--log-level',dest='loglevel', default='WARNING',
                    help='Specify the logging level')
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                    help='Disable stdout logging')
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


def start_server(adress='/tmp/rstscript.sock'):
    from rstscript import server
    rstscriptserver = server.RstScriptServer({},{})
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
