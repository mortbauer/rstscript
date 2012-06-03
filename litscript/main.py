import os
import sys
import re
from argparse import ArgumentParser, FileType

from .processors import IPython2Processor, ChunkProcessor
from .__init__ import __version__
from .document import Document

if sys.version_info[0] >= 3:
    from configparser import SafeConfigParser
else :
    from ConfigParser import SafeConfigParser

def _load_processor(plugindir=None):
    processors = {}
    plugindir_paths = []

    # add the plugin-directory paths if they're not already in the path
    if plugindir is not None:
        plugindir_paths.insert(0, os.path.abspath(plugindir))
    else:
        plugindir_paths = [
                    os.path.join(os.path.expanduser('~'),
                        '.config/litscript/plugins')
                      ]
    # list all files in plugindirs and add the plugindir_paths to the current
    # pythonpath
    files = []
    for p in plugindir_paths:
        if not p in sys.path:
            sys.path.insert(0, p)
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
    # discover all plugins in the loaded modules
    # list of classes which are based on ChunkProcessorBase
    plugin_classes = ChunkProcessor.__subclasses__()
    # create instances of each plugin class object,
    # and store them in the global instance dictionary *processors*
    for i in plugin_classes:
        processors[i.name] = i

    return processors
def _config_parse(config_file=None):
    """ Parse Configfiles

    Parses standard configuration files, like `.ini` files.

    Default parsed files are:

        $XDG_CONFIG_HOME/litscript/config
        ~/.litscript.rc

    Optionally there can be given the path of another file.

    The order of the prased files is like:

    1. if it exists the optinal given file
    2. $XDG_CONFIG_HOME/litscript/config
    3. ~/.litscript.rc

    Where the first has higher precedence then the others if there is the same
    key.

    """
    configfiles = [
        os.path.join(os.environ.get('XDG_CONFIG_HOME',
                                    os.path.expanduser('~/.config')),
                     'litscript', 'config'),
        os.path.expanduser('~/.litscript.rc'),
    ]
    if config_file:
        expanded_path = os.path.expanduser(config_file)
        if not os.path.exists(expanded_path):
            sys.exit('File \'%s\' does not exist, check your argument for the'
                    ' CONFIGFILE!' % expanded_path)
        configfiles.insert(0, expanded_path)

    cparser = SafeConfigParser()
    parsed_files = cparser.read(reversed(configfiles))

    settings = cparser._sections
    settings['parsed_configfiles'] = parsed_files

    return settings
class Litscript(object):
    version = __version__
    def __init__(self,cmd_settings):
        self.cmd = cmd_settings
        self.config = _config_parse(self.cmd['configfile'])
        self.processors = _load_processor(self.cmd['plugindir'])

    def _process(self,raw):
        self.document = Document(raw,self.processors)
        
    def main(self):
        for sourcefile in self.cmd['source']:
            self._process(sourcefile.read())

def main():
    if len(sys.argv)==1:
        print("This is litscript %s, enter litscript -h for help"
                % __version__)
        sys.exit()

    parser = ArgumentParser(usage="litscript [options] sourcefile",
            version="litscript " + __version__)

    parser.add_argument("-w", "--weave", dest="weave",
                      action = "store", default='.rst',
                      help="Should the document be weaved? If yes, provide the"
                      "extension of the weaved output document.")
    parser.add_argument("-t", "--tangl", dest="tangle",
                      action = "store", default='.py',
                      help="Should the document be tangeld? If yes provide the"
                      "ending of the tangeld output document.")
    parser.add_argument("-f", "--format", dest="format",
                      action = "store", default="rst",
                      help="The output format: 'sphinx', 'rst' (default), 'pandoc' or 'tex'")
    parser.add_argument("--figure-directory", dest="figdir",
                      action = "store", default = 'figures',
                      help="Directory path for matplolib graphics: Default 'figures'")
    parser.add_argument("-g","--figure-format", dest="figfmt",
                      action = "store", default="png",
                      help="Figure format for matplolib graphics: Defaults to"
                      "'png' for rst and Sphinx html documents and 'pdf' for tex")
    parser.add_argument("-p", "--plugin-directory", dest="plugindir",
                      action = "store", default=None,
                      help="Optional directory containing litscript plugin files.")
    parser.add_argument("-c", "--config", dest="configfile", default=None,
                      help="Specify the litscript config file.")
    parser.add_argument("-d", "--debug", action = "store_true", default=False,
                      help="Run in debugging mode.")
    parser.add_argument('source', type = FileType('r'), nargs='*',
                      default=sys.stdin,
                      help='The to processing source file.')

    arguments = vars(parser.parse_args(args))

    #arguments['default']['processor'] = 'ipython2'

    def debug(inst):
        print('cmd')
        print(inst.cmd)
        print('config')
        print(inst.config)
        print('processors')
        print(inst.processors)
        #print('settings')
        #print(inst.settings)
        print(inst.document)
        for i in inst.document:
            print(i.options)

    lit = Litscript(arguments)
    lit.main()
    if arguments['debug'] == True:
        debug(lit)
    return lit

if __name__ == '__main__':
    main()

# vim: set ts=4 sw=4 tw=79 :
