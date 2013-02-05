import re
import os
import sys
import logging
import colorama
import argparse

from . import chunks
from . import formatters

from .__init__ import __version__
from .utils import LitscriptException

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

logger = logging.getLogger('litscript.main')

class HelpParser(argparse.ArgumentParser):
    """ creates a modified parser
    which will print the help message if
    an error occurs

    Note: from Stackoverflow answer http://stackoverflow.com/a/4042861/1607448
    """
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

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

def import_plugins(plugindir):
    if plugindir:
        sys.path.insert(0, plugindir)
        # get all py files and strip the extension
        pyfiles = [x[:-3] for x in os.listdir(plugindir) if x.endswith('.py')]
        # import the modules which we found in the plugin path
        plugin_modules = {}
        for module in pyfiles:
            try:
                plugin_modules[module] = __import__(module)
            except Exception as e:
                logger.error('skipping plugin "{0}": {1}'.format(module,e))
        # remove added paths again
        sys.path.remove(plugindir)

        return plugin_modules
    else:
        return {}


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
    conf_parser = HelpParser(
    # Turn off help, so we print all options in response to -h
        add_help=False
        )
    conf_parser.add_argument("-c", "--conf_file", dest="conf_file",
                             help="Specify config file", metavar="FILE")
    return conf_parser


def make_parser(pre_parser):
    #parser = HelpParser(
    parser = argparse.ArgumentParser(
    # Inherit options from config_parser
    parents=[pre_parser],
    # simple usage message
    usage="litscript [options] sourcefile",
    # version
    )

    parser.add_argument("-w", "--weave", dest="weave",
                      action="store", default=None,
                      help="Should the document be weaved? If yes, provide the"
                      " extension of the weaved output document.")
    parser.add_argument("-t", "--tangl", dest="tangle",
                      action="store", default=None,
                      help="Should the document be tangeld? If yes provide the"
                      " ending of the tangeld output document.")
    parser.add_argument("-f", "--format", dest="format",
                      action="store", default="rst",
                      help="The output format: 'rst' only "
                        "one available so far.")
    parser.add_argument("--figure-directory", dest='figdir',
                      action="store", default='_figures',
                      help="Directory path for matplolib graphics:"
                        " Default 'figures'")
    parser.add_argument("-g","--figure-format", dest="figfmt",
                      action="store", default="png",
                      help="Figure format for matplolib graphics: Defaults to"
                        "'png' for rst and Sphinx html documents and 'pdf' "
                        "for tex")
    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                      action="store", default=[],
                      help="Optional directory containing litscript plugin"
                        " files.")
    parser.add_argument("-ow", "--output-weave", dest="woutput",
                        default=None, nargs=1,
                      help="Specify the output file for the weaved content.")
    parser.add_argument("-ot", "--output-tangle", dest="toutput", nargs=1,
                        default=None,
                      help="Specify the output file for the tangled content.")
    parser.add_argument("--force", action="store_true", default=False,
                      help="Overwrite existing files without asking.")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                      help="Run in debugging mode.")
    parser.add_argument('source', type=argparse.FileType('rt'), nargs=1,
                      default=[sys.stdin],
                      help='The to processing source file.')
    parser.add_argument('-l','--log-level',dest='loglevel', default='ERROR',
                      help='Specify the logging level')
    parser.add_argument('-q','--quiet',dest='quiet',action='store_true', default=False,
                      help='Disable stdout logging')
    parser.add_argument('--version', action='version', version=__version__)
    return parser


def main(argv=None):
    """Litscript Main
    can be either called from commandline, or in an interactive
    python environment.

    cmd_example::

        litscript -w rst helloworld.lit

    interactive_example::

        from litscript import main
        main.main(argv=['-w rst','helloworld.lit'])

    """

    ## read configfile argument
    pre_parser = make_pre_parser()

    # if length of argv is to small, call the help
    if len(argv) < 1:
        pre_parser.print_help()
        raise LitscriptException()

    hard_defaults = {"conf_file":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
                                              "litscript","config"
                                             )
                    }
    pre_parser.set_defaults(**hard_defaults)
    args, remaining_argv = pre_parser.parse_known_args(argv)
    # read configfile
    config_parser = read_config(args.conf_file)
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
    logger = logging.getLogger('litscript.main')
    if args['quiet']:
        handler = logging.NullHandler()
    else:
        handler = ColorizingStreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    try:
        logger.setLevel(getattr(logging,args['loglevel']))
    except AttributeError:
        raise LitscriptException('invalid logging level "{0}"'.format(args['loglevel']))
    # default figdir
    if not os.path.isabs(args['figdir']) and args['woutput']:
        outputdir = os.path.split(args['woutput'])[0]
        args.figdir = os.path.join(os.path.abspath(outputdir),args['figdir'])
    # import plugin modules
    plugin_moduls = import_plugins(args['plugindir'])

    L = chunks.Litrunner(options=args)
    print(formatters.BaseFormatter.plugins)
    return


# vim: set ts=4 sw=4 tw=79 :
