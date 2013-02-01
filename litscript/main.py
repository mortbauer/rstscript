import re
import os
import sys
import argparse

from .glue import Litscript
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
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def import_plugins(plugindirs):
    plugindir_paths = []
    # add the plugin-directory paths if they're not already in the path
    if type(plugindirs) == str:
        plugindirs = [plugindirs]
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
    parser = HelpParser(
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
                        default=None,
                      help="Specify the output file for the weaved content.")
    parser.add_argument("-ot", "--output-tangle", dest="toutput", nargs=1,
                        default=None,
                      help="Specify the output file for the tangled content.")
    parser.add_argument("--force", action="store_true", default=False,
                      help="Overwrite existing files without asking.")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                      help="Run in debugging mode.")
    parser.add_argument('source', type=argparse.FileType('rt'), nargs='+',
                      default=[sys.stdin],
                      help='The to processing source file.')
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
        main.main(['-w rst','helloworld.lit']

    """

    if argv is None:
        argv = sys.argv[1:]

    # read configfile argument
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

    # parse the rest
    parser = make_parser(pre_parser)
    # set the defaults
    parser.set_defaults(**soft_defaults)
    # parse remaining args
    args = parser.parse_args(remaining_argv)
    # default figdir, create also
    if args.woutput and not os.path.isabs(args.figdir):
        outputdir = os.path.split(args.woutput)[0]
        args.figdir = os.path.join(os.path.abspath(outputdir),args.figdir)
    if args.woutput and not os.path.exists(args.figdir):
        os.mkdir(args.figdir)

    # import plugins
    args = vars(args)
    plugin_moduls = import_plugins(args['plugindir'])

    # define output filenames
    if args['weave'] != None and args['woutput'] == None:
        ext = '.' + args['weave'].strip()
        args['woutput'] = [os.path.splitext(x.name)[0] + ext for x in args['source']]

    if args['tangle'] != None and args['toutput'] == None:
        ext = '.' + args['tangle'].strip()
        args['toutput'] = [os.path.splitext(x.name)[0] + ext for x in args['source']]

    L = Litscript(args,plugin_moduls)
    L.main()
    return L

if __name__ == '__main__':
    #sys.exit(main())
    main()

# vim: set ts=4 sw=4 tw=79 :
