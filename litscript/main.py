import re
import os
import sys
import logging
import colorama
import argparse

from . import utils
from . import chunks
from . import formatters
from . import processors

from .__init__ import __version__
from .utils import LitscriptException

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser


class HelpParser(argparse.ArgumentParser):
    """ creates a modified parser
    which will print the help message if
    an error occurs

    Note: from Stackoverflow answer http://stackoverflow.com/a/4042861/1607448
    """
    def error(self, message):
        #sys.stderr.write('error: %s\n' % message)
        self.print_help()
        raise LitscriptException(message)

class ColorizingStreamHandler(logging.StreamHandler):
    # Courtesy http://plumberjack.blogspot.com/2010/12/colorizing-logging-output-in-terminals.html
    # Tweaked to use colorama for the coloring

    """
    Sets up a colorized logger, which is used ltscript
    """
    color_map = {
        logging.DEBUG: colorama.Style.DIM + colorama.Fore.CYAN,
        logging.WARNING: colorama.Fore.YELLOW,
        logging.ERROR: colorama.Fore.RED,
        logging.CRITICAL: colorama.Back.RED,
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
                             help="Specify config file", metavar="FILE")
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
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                      help="Run in debugging mode.")
    parser.add_argument('-l','--log-level',dest='loglevel', default='ERROR',
                      help='Specify the logging level')
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                      help='Disable stdout logging')
    parser.add_argument('--version', action='version', version=__version__)

    #subparsers = parser.add_subparsers(dest='command',description='',help='specify a subcommand')

    #weaveparser = subparsers.add_parser('weave', help='weave the document')

    parser.add_argument('-i', dest='source',type=argparse.FileType('rt'), nargs=1,
                      default=[sys.stdin], help='litscript source file')
    parser.add_argument("-o", "--output", dest="output",
                        type=argparse.FileType('wt'), nargs=1,
                      help="Specify the output file for the weaved content.")
    #weaveparser.add_argument("--figure-directory", dest='figdir',
                      #action="store", default='_figures',
                      #help="Directory path for matplolib graphics:"
                        #" Default 'figures'")
    #weaveparser.add_argument("-g","--figure-format", dest="figfmt",
                      #action="store", default="png",
                      #help="Figure format for matplolib graphics: Defaults to"
                        #"'png' for rst and Sphinx html documents and 'pdf' "
                        #"for tex")

   # tangleparser = subparsers.add_parser('tangle', help='tangle the document')
    #tangleparser.add_argument('-i', dest='source',type=argparse.FileType('rt'), nargs=1,
                      #default=[sys.stdin], help='litscript source file')
    #tangleparser.add_argument("-o", "--output", dest="output", nargs=1,
                        #type=argparse.FileType('wt'),
                      #help="Specify the output file for the tangled content.")
    return parser


def main():
    """Litscript Main
    can be either called from commandline, if you want to use it as libary
    use directly the ``run`` function.

    cmd_example::

        litscript -w rst helloworld.lit

    interactive_example::

        from litscript import main
        main.run(['-w rst','helloworld.lit'])

    """
    try:
        run(sys.argv[1:])
        sys.exit(0)
    except LitscriptException as e:
        sys.exit(1)

def run(argv):
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
        logger.setLevel(getattr(logging,args['loglevel'].upper()))
    except:
        raise LitscriptException('invalid logging level "{0}"'.format(args['loglevel']))
    # my first logging task
    logger.info('parsed options {0}'.format(args))
    # default figdir
    if not os.path.isabs(args['figdir']) and args['output']:
        outputdir = os.path.split(args['output'])[0]
        args['figdir'] = os.path.join(os.path.abspath(outputdir),args['figdir'])
    # load the default processors and formatter
    processors.PythonProcessor.register()
    formatters.CompactFormatter.register()
    # import plugin modules,if they can register themself on module level
    plugin_moduls = utils.import_plugins(args['plugindir'])
    # create the Litrunner object
    L = chunks.Litrunner(options=args)
    # register all loaded processors and formatters in the Litrunner object
    for processor in processors.BaseProcessor.plugins.values():
        L.register_processor(processor)
    for formatter in formatters.BaseFormatter.plugins.values():
        L.register_formatter(formatter)
    # set default processor and formatter and options
    L.set_defaults(processors.PythonProcessor.name,{},formatters.CompactFormatter.name,{})
    # test if Litrunner is ready
    if L.test_readiness():
        logger.info('Litrunner "{0}" ready'.format(L))
    # now lets look what we have to do
    if args['command'] == 'weave':
        args['output'].write(L.format(L.weave(L.read(args['source']))))

    return


# vim: set ts=4 sw=4 tw=79 :
