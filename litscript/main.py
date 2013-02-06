import os
import sys
import logging
import pprint
import colorama
import argparse

from litscript import utils
from litscript import chunks
from litscript import processors

from litscript.__init__ import __version__
from litscript.utils import LitscriptException

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

logger = logging.getLogger('litscript')

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

def guess_outputfile(inputpath,basenamein,ext,force=False):
    basename = os.path.splitext(basenamein)[0]+os.path.extsep+ext
    outputfile = os.path.join(inputpath,basename)
    # test if outputfile existing, won't touch it if it does
    if os.path.exists(outputfile):
        if not force:
            raise LitscriptException('outputfile "{0}" existing, provide'
            'name explicit or force me'.format(outputfile))
        else:
            logger.warning('will override existing file "{0}"'
                    .format(outputfile))
            return open(outputfile,'wt')
    else:
        logger.info('tryed to be smart and guessed output file to "{0}"'
                .format(outputfile))
        return open(outputfile,'wt')


def read_config(conf_file):
    config_parser = SafeConfigParser()
    abspath = os.path.abspath(conf_file)
    if os.path.exists(abspath):
        config_parser.read([abspath])
        return config_parser
    else:
        print('The given path: %s does not exist' % abspath)
        return


def make_pre_parser():
    conf_parser = argparse.ArgumentParser(
    #conf_parser = HelpParser(
    # Turn off help, so we print all options in response to -h
        add_help=False
        )
    conf_parser.add_argument("-c", "--conf", dest="conf",
                             help="Specify config file")
    return conf_parser


def make_parser(pre_parser):
    #parser = HelpParser(
    parser = argparse.ArgumentParser(
    # Inherit options from config_parser
    parents=[pre_parser],
    # version
    )

    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                      action="store", default='',
                      help="Optional directory containing litscript plugin"
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
    parser.add_argument('--version', action='version', version=__version__)


    subparsers = parser.add_subparsers(dest='command',description='',help='specify a subcommand')

    weaveparser = subparsers.add_parser('weave', help='weave the document')

    weaveparser.add_argument('-i','--input', dest='input',type=argparse.FileType('rt'), nargs=1,
                      required=True,default=[sys.stdin], help='litscript source file')
    weaveparser.add_argument("-o", "--output", dest="output",
                        type=argparse.FileType('wt'), nargs='?',
                      help="output file for weaving")
    weaveparser.add_argument("--figure-directory", dest='figdir',
                      action="store", default='_figures',
                      help="path to store produced figures")
    weaveparser.add_argument("-g","--figure-format", dest="figfmt",
                      action="store", default="png",
                      help="Figure format for matplolib graphics: Defaults to"
                        "'png' for rst and Sphinx html documents and 'pdf' "
                        "for tex")
    # pass remaining args on
    weaveparser.add_argument('--args',default=[],action='store',nargs=argparse.REMAINDER)

    tangleparser = subparsers.add_parser('tangle', help='tangle the document')
    tangleparser.add_argument('-i', dest='input',type=argparse.FileType('rt'), nargs=1,
                      required=True, default=[sys.stdin], help='litscript source file')
    tangleparser.add_argument("-o", "--output", dest="output", nargs='?',
                        type=argparse.FileType('wt'),
                      help="Specify the output file for the tangled content.")
    tangleparser.add_argument('--args',default=[],action='store',nargs=argparse.REMAINDER)
    return parser


def run():
    """Litscript Main Wrapper for catching unexpected Errors
    can be either called from commandline, if you want to use it as libary
    use directly the ``main`` function.

    cmd_example::

        litscript -w rst helloworld.lit

    interactive_example::

        from litscript import main
        main.main(['-w rst','helloworld.lit'])

    """
    if sys.argv[1] and sys.argv[1]=='-d':
        # Debugging Mode with PDB
        print('\nEnter Debbuging Mode:\n')
        import pdb
        import traceback
        try:
            main(sys.argv[1:])
        except:
            print('\n Traceback:\n')
            errortype, value, tb = sys.exc_info()
            traceback.print_exc()
            print('\n Enter post_mortem Debugging:\n')
            pdb.post_mortem(tb)
            sys.exit(1)
    else:
        # silent mode
        try:
            main(sys.argv[1:])
        except LitscriptException as e:
            print(e)
            sys.exit(1)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print('\nI\'m sorry but an unhandeled exception occured, '
            'maybe try the debugging switch "-d" as first argument')
            sys.exit(1)

    sys.exit(0)

def main(argv):
    ## read configfile argument
    pre_parser = make_pre_parser()

    hard_defaults = {"conf":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
                                              "litscript","config"
                                             )
                    }
    pre_parser.set_defaults(**hard_defaults)
    args, remaining_argv = pre_parser.parse_known_args(argv)
    # read configfile
    config_parser = read_config(args.conf)
    if config_parser.has_section('default'):
        soft_defaults = dict(config_parser.items("default"))
    else:
        soft_defaults = {}

    # parse the rest
    parser = make_parser(pre_parser)
    # set the defaults
    parser.set_defaults(**soft_defaults)
    # parse remaining args
    args = vars(parser.parse_args(remaining_argv))
    # setup the logger
    logger = logging.getLogger('litscript')
    if args['quiet']:
        handler = logging.NullHandler()
    else:
        handler = ColorizingStreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    try:
        if args['debug']:
            logger.setLevel('DEBUG')
        else:
            logger.setLevel(getattr(logging,args['loglevel'].upper()))
    except:
        raise LitscriptException('invalid logging level "{0}"'.format(args['loglevel']))
    # my first logging task
    logger.info('parsed options \n{0}'.format(pprint.pformat(args)))
    # set some paths
    args['inputpath'], args['basename'] = os.path.split(os.path.abspath(args['input'][0].name))
    # try to gues output if not specified
    if not args['output']:
        if args['command'] == 'weave':
            args['output'] = guess_outputfile(args['inputpath'],
                    args['basename'],'rst',force=args['force'])
        elif args['command'] == 'tangle':
            args['output'] = guess_outputfile(args['inputpath'],
                    args['basename'],'py',force=args['force'])
    # default figdir
    if  args['command'] == 'weave' and not os.path.isabs(args['figdir']):
        args['outputpath'] = os.path.split(args['output'].name)[0]
        args['figdir'] = os.path.join(args['outputpath'],args['figdir'])
    # load the default processors and formatter
    processors.PythonProcessor.register()
    processors.CompactFormatter.register()
    # import plugin modules,if they can register themself on module level
    if not args['no_plugins']:
        plugin_moduls = utils.import_plugins(args['plugindir'])
    # create the Litrunner object
    L = chunks.Litrunner(options=args)
    # register all loaded processors and formatters in the Litrunner object
    for processor in processors.BaseProcessor.plugins.values():
        L.register_processor(processor)
    for formatter in processors.BaseFormatter.plugins.values():
        L.register_formatter(formatter)
    # set default processor and formatter and options
    L.set_defaults(processors.PythonProcessor.name,args['args'],
            processors.CompactFormatter.name,args['args'])
    # test if Litrunner is ready
    if L.test_readiness():
        logger.info('Litrunner "{0}" ready'.format(L))
    # now lets look what we have to do
    if args['command'] == 'weave':
        for formatted in L.format(L.weave(L.read(args['input'][0]))):
            args['output'].write(formatted)
    elif args['command'] == 'tangle':
        for formatted in L.tangle(L.read(args['input'][0])):
            args['output'].write(formatted)

    return

if __name__ == '__main__':
    main()

# vim: set ts=4 sw=4 tw=79 :
