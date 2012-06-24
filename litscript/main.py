import re
import os
import sys
from argparse import ArgumentParser, FileType

#from .glue import worker
from .__init__ import __version__
from .utils import LitscriptException

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser


def import_plugins(plugindirs=[]):
    plugindir_paths = []
    # add the plugin-directory paths if they're not already in the path
    for plugindir in plugindirs:
        plugindir_paths.insert(0, os.path.abspath(plugindir))
    # list all files in plugindirs and add the plugindir_paths to the current
    # pythonpath
    files = []
    added_paths = []
    for p in plugindir_paths:
        if not p in sys.path:
            sys.path.insert(0, p)
            added_paths.insert(0,p)
        try:
            files.extend(os.listdir(p))
        except:
            pass
    # filter for plugins
    re_pyfile = re.compile(".*\.py$", re.IGNORECASE)
    pyfiles = filter(re_pyfile.search, files)
    # strip off '.py' on end of filenames
    modules = [filename[:-3] for filename in pyfiles]
    # import the modules which we found in the plugin path
    plugin_modules = {}
    for module in modules:
        plugin_modules[module] = __import__(module)

    # remove added paths again
    for paths in added_paths:
        sys.path.remove(paths)

    return plugin_modules


def read_config(conf_file):
    config_parser = SafeConfigParser()
    abspath = os.path.abspath(conf_file)
    if os.path.exists(abspath):
        config_parser.read([abspath])
        return config_parser
    else:
        print('The given path: %s does not exist'%abspath)
        return

def make_pre_parser():
    conf_parser = ArgumentParser(
    # Turn off help, so we print all options in response to -h
        add_help=False
        )
    conf_parser.add_argument("-c", "--conf_file", dest="conf_file",
                             help="Specify config file", metavar="FILE")
    return conf_parser


def make_parser(pre_parser):
    parser = ArgumentParser(
    # Inherit options from config_parser
    parents=[pre_parser],
    # simple usage message
    usage="litscript [options] sourcefile",
    # version
    version="litscript " + __version__
    # Don't mess with format of description
    #formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    #parser = ArgumentParser(usage="litscript [options] sourcefile",
            #version="litscript " + __version__)

    parser.add_argument("-w", "--weave", dest="weave",
                      action="store", default='.rst',
                      help="Should the document be weaved? If yes, provide the"
                      " extension of the weaved output document.")
    parser.add_argument("-t", "--tangl", dest="tangle",
                      action="store", default='.py',
                      help="Should the document be tangeld? If yes provide the"
                      " ending of the tangeld output document.")
    parser.add_argument("-f", "--format", dest="format",
                      action="store", default="rst",
                      help="The output format: 'rst' only "
                        "one available so far.")
    parser.add_argument("--figure-directory", dest="figdir",
                      action="store", default='figures',
                      help="Directory path for matplolib graphics:"
                        " Default 'figures'")
    parser.add_argument("-g","--figure-format", dest="figfmt",
                      action="store", default="png",
                      help="Figure format for matplolib graphics: Defaults to"
                        "'png' for rst and Sphinx html documents and 'pdf' "
                        "for tex")
    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                      action="store", default=None,
                      help="Optional directory containing litscript plugin"
                        " files.")
    parser.add_argument("-o", "--output", dest="output", default=None,
                      help="Specify the output file.")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                      help="Run in debugging mode.")
    parser.add_argument('source', type=FileType('rt'), nargs='*',
                      default=sys.stdin,
                      help='The to processing source file.')

    return parser


def main(argv=None):
    """Litscript Main
    can be either called from commandline, or in an interactive
    python environment.

    cmd_example::

        litscript -w rst helloworld.lit

    interactive_example::

        from litscript import main
        main.main(['-w rst','helloworld.lit']

    """

    if argv is None:
        argv = sys.argv[1:]

    # not working as also accepting input from stream
    #if len(argv) == 1:
        #parser.print_help()
        #return 1

    # read configfile args
    pre_parser = make_pre_parser()
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

    # true parser
    parser = make_parser(pre_parser)
    # set the defaults
    parser.set_defaults(**soft_defaults)
    # parse remaining args
    args = parser.parse_args(remaining_argv)

    return args

if __name__ == '__main__':
    sys.exit(main())

# vim: set ts=4 sw=4 tw=79 :
