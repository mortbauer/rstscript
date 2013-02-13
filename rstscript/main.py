import os
import sys
import logging
import pprint
import colorama
import argparse
import traceback
import pkgutil
import rstscript

from rstscript import litrunner
from rstscript import processors

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

logger = logging.getLogger('rstscript')

class LitParser(argparse.ArgumentParser):
    def error(self,message):
        raise RstscriptException(message)

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

class LitManager(object):

    def _make_preparser(self):
        pre_parser = argparse.ArgumentParser(add_help=False)
        pre_parser.add_argument("-c", "--conf", dest="conf",
                                help="specify config file")
        pre_parser.add_argument("--pdb",action='store_true', dest="pdb",
                                help="debug with pdb")

        hard_defaults = {"conf":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
            "rstscript","config"),
            "conf.d":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
            "rstscript"),
            "plugindir":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
            "rstscript","plugindir")}
        # create default configuration directory and files if not there
        if not os.path.exists(hard_defaults['conf.d']):
            os.mkdir(hard_defaults['conf.d'])
            print('created configuration directory "{0}"'
                    .format(hard_defaults['conf.d']))
        if not os.path.exists(hard_defaults['plugindir']):
            os.mkdir(hard_defaults['plugindir'])
            print('created plugin directory "{0}"'
                    .format(hard_defaults['plugindir']))
        if not os.path.exists(hard_defaults['conf']):
            with open(hard_defaults['conf'],'wb') as f:
                f.write(pkgutil.get_data(__name__, 'defaults/config'))
            print('created configuration file "{0}"'
                    .format(hard_defaults['conf']))
        pre_parser.set_defaults(**hard_defaults)
        return pre_parser

    def _make_parser(self,pre_parser,soft_defaults):
        parser = argparse.ArgumentParser(
        parents=[pre_parser],
        )
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
        # set the defaults
        parser.set_defaults(**soft_defaults)
        return parser

    def _make_configparser(self,conf_file):
    config_parser = SafeConfigParser()
    abspath = os.path.abspath(conf_file)
    if os.path.exists(abspath):
        config_parser.read([abspath])
        return config_parser
    else:
        logger.warning('The given path: %s does not exist' % abspath)
        return config_parser

    def _make_logger(self,app_options):
        logger = logging.getLogger('rstscript.app')
        # setup the app logger
        if app_options.quiet:
            handler = logging.NullHandler()
        else:
            handler = ColorizingStreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if app_options.debug:
            logger.setLevel('DEBUG')
        else:
            if hasattr(logging,app_options.loglevel):
                logger.setLevel(getattr(logging,app_options.loglevel.upper()))
            else:
                logger.setLevel('WARNING')
                logger.error('invalid logging level "{0}"'.format(app_options.loglevel))
        return logger


    def __init__(self):
        self.logger = logging.getLogger('rstscript')
        self.logger.setLevel('INFO')
        # parse the arguments regarding the configuration
        pre_parser = self._make_preparser()
        app_options, remaining_argv = pre_parser.parse_known_args(argv)
        # read configfile
        config_parser = self._make_configparser(app_options.conf)
        if config_parser.has_section('default'):
            soft_defaults = dict(config_parser.items("default"))
        else:
            soft_defaults = {}
        # parse the rest
        parser = self._make_parser(pre_parser,soft_defaults)
        # parse remaining app_options
        app_options,proc_form_args = parser.parse_known_args(remaining_argv)
        # setup the logger
        logger = self._make_logger(app_options)
        # my first logging task
        logger.info('parsed options \n{0}'.format(pprint.pformat(vars(app_options))))
        # set some paths
        app_options.inputpath, app_options.basename = os.path.split(os.path.abspath(app_options.input[0].name))
        # parse remaining arguments which are passed through to the plugins, but be
        # careful, don't use any option keys already used in the main app, it will mess
        # everything completely up
        app_options.proc_args, app_options.form_args = parse_through_args(proc_form_args)
        # load the default processors and formatter
        processors.PythonProcessor.register()
        processors.CompactFormatter.register()
        # import plugin modules,if they can register themself on module level
        if not app_options.no_plugins:
            plugin_moduls = import_plugins(app_options.plugindir)
        # try to gues output if not specified
        if not app_options.noweave and not app_options.woutput:
            app_options.woutput = guess_outputfile(app_options.inputpath,
                    app_options.basename,'rst',force=app_options.force)
        if app_options.tangle and not app_options.toutput:
            app_options.toutput = guess_outputfile(app_options.inputpath,
                    app_options.basename,'py',force=app_options.force)
        # set a woutput directory if weaving
        if not app_options.noweave:
            app_options.woutputpath = os.path.split(app_options.woutput.name)[0]
            # set default figdir if it isn't a absolute path
            if  not os.path.isabs(app_options.figdir):
                app_options.figdir = os.path.join(app_options.woutputpath,app_options.figdir)
                logger.info('use "{0}" as figdir'.format(app_options.figdir))


            # parse the main arguments

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


def guess_outputfile(inputpath,basenamein,ext,force=False):
    basename = os.path.splitext(basenamein)[0]+os.path.extsep+ext
    outputfile = os.path.join(inputpath,basename)
    # test if outputfile existing, won't touch it if it does
    if os.path.exists(outputfile):
        if not force:
            raise rstscript.RstscriptException('outputfile "{0}" existing, provide'
            'name explicit or force me'.format(outputfile))
        else:
            logger.warning('will override existing file "{0}"'
                    .format(outputfile))
            return open(outputfile,'wt')
    else:
        logger.info('tryed to be smart and guessed output file to "{0}"'
                .format(outputfile))
        return open(outputfile,'wt')


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


def read_config(conf_file):
    config_parser = SafeConfigParser()
    abspath = os.path.abspath(conf_file)
    if os.path.exists(abspath):
        config_parser.read([abspath])
        return config_parser
    else:
        logger.warning('The given path: %s does not exist' % abspath)
        return config_parser


def make_pre_parser():
    conf_parser = argparse.ArgumentParser(
    #conf_parser = HelpParser(
    # Turn off help, so we print all options in response to -h
        add_help=False
        )
    conf_parser.add_argument("-c", "--conf", dest="conf",
                             help="specify config file")
    conf_parser.add_argument("--pdb",action='store_true', dest="pdb",
                             help="debug with pdb")
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
    # pass remaining app_options on
    #wsubparser.add_argument('--args',default='python',action='store',nargs=argparse.REMAINDER)

    return parser


def run():
    """Litscript Main Wrapper for catching unexpected Errors
    can be either called from commandline, if you want to use it as libary
    use directly the ``main`` function.

    cmd_example::

        rstscript -w rst helloworld.lit

    interactive_example::

        from rstscript import main
        main.main(['-w rst','helloworld.lit'])

    """
    try:
        main(sys.argv[1:])
        sys.exit(0)
    except rstscript.RstscriptException as e:
        print(e)
        sys.exit(1)

def main(argv):
    ## read configfile argument
    pre_parser = make_pre_parser()
    hard_defaults = {"conf":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript","config"),
        "conf.d":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript"),
        "plugindir":os.path.join(os.getenv("XDG_CONFIG_HOME",''),
        "rstscript","plugindir")}
    # create default configuration directory and files if not there
    if not os.path.exists(hard_defaults['conf.d']):
        os.mkdir(hard_defaults['conf.d'])
        print('created configuration directory "{0}"'
                .format(hard_defaults['conf.d']))
    if not os.path.exists(hard_defaults['plugindir']):
        os.mkdir(hard_defaults['plugindir'])
        print('created plugin directory "{0}"'
                .format(hard_defaults['plugindir']))
    if not os.path.exists(hard_defaults['conf']):
        with open(hard_defaults['conf'],'wb') as f:
            f.write(pkgutil.get_data(__name__, 'defaults/config'))
        print('created configuration file "{0}"'
                .format(hard_defaults['conf']))
    pre_parser.set_defaults(**hard_defaults)
    app_options, remaining_argv = pre_parser.parse_known_args(argv)
    # read configfile
    config_parser = read_config(app_options.conf)
    if config_parser.has_section('default'):
        soft_defaults = dict(config_parser.items("default"))
    else:
        soft_defaults = {}
    # import the debugging hook
    if app_options.pdb:
        print('\nEnter Debbuging Mode:\n')
        from . import debug
        # start the main app
        mainapp(pre_parser,remaining_argv,soft_defaults)
    else:
        try:
            mainapp(pre_parser,remaining_argv,soft_defaults)
            sys.exit(0)
        except rstscript.RstscriptException as e:
            print(e)
            sys.exit(1)
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)
        except Exception:
            traceback.print_exc()
            print('\nI\'m sorry but an unhandeled exception occured, '
            'you can debugg me with "--pdb"')
            sys.exit(1)

def mainapp(pre_parser,remaining_argv,soft_defaults):
    # parse the rest
    parser = make_parser(pre_parser)
    # set the defaults
    parser.set_defaults(**soft_defaults)
    # parse remaining app_options
    app_options,proc_form_args = parser.parse_known_args(remaining_argv)
    # setup the logger
    logger = logging.getLogger('rstscript')
    if app_options.quiet:
        handler = logging.NullHandler()
    else:
        handler = ColorizingStreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if app_options.debug:
        logger.setLevel('DEBUG')
    else:
        if hasattr(logging,app_options.loglevel):
            logger.setLevel(getattr(logging,app_options.loglevel.upper()))
        else:
            logger.setLevel('WARNING')
            logger.error('invalid logging level "{0}"'.format(app_options.loglevel))
    # my first logging task
    logger.info('parsed options \n{0}'.format(pprint.pformat(vars(app_options))))
    # set some paths
    app_options.inputpath, app_options.basename = os.path.split(os.path.abspath(app_options.input[0].name))
    # parse remaining arguments which are passed through to the plugins, but be
    # careful, don't use any option keys already used in the main app, it will mess
    # everything completely up
    app_options.proc_args, app_options.form_args = parse_through_args(proc_form_args)
    # load the default processors and formatter
    processors.PythonProcessor.register()
    processors.CompactFormatter.register()
    # import plugin modules,if they can register themself on module level
    if not app_options.no_plugins:
        plugin_moduls = import_plugins(app_options.plugindir)
    # try to gues output if not specified
    if not app_options.noweave and not app_options.woutput:
        app_options.woutput = guess_outputfile(app_options.inputpath,
                app_options.basename,'rst',force=app_options.force)
    if app_options.tangle and not app_options.toutput:
        app_options.toutput = guess_outputfile(app_options.inputpath,
                app_options.basename,'py',force=app_options.force)
    # set a woutput directory if weaving
    if not app_options.noweave:
        app_options.woutputpath = os.path.split(app_options.woutput.name)[0]
        # set default figdir if it isn't a absolute path
        if  not os.path.isabs(app_options.figdir):
            app_options.figdir = os.path.join(app_options.woutputpath,app_options.figdir)
            logger.info('use "{0}" as figdir'.format(app_options.figdir))
    # create the Litrunner object
    L = litrunner.Litrunner(app_options)
    # now lets look what we have to do
    if L.run():
        logger.info('### job completed succesfully ###')
    else:
        logger.info('### could\'n t complete job ###')

if __name__ == '__main__':
    run()

# vim: set ts=4 sw=4 tw=79 :
