from .chunks import *
from .processors import *
from .__init__ import __version__
from .utils import LitscriptException
import logging


# create logger
logging.basicConfig(format='%(levelname)s:%(message)s',level=logging.DEBUG)


class Litscript(object):
    version = __version__

    def __init__(self,args,loaded_modules):
        self._args = args
        self._loaded_modules = loaded_modules
        self._register()

    def _register(self):
        plugins = Pre.__subclasses__()
        plugins.extend(Proc.__subclasses__())
        plugins.extend(Post.__subclasses__())
        for x in plugins:
            x.register()
        self._plugins = plugins
        self._pre_plugins = Pre.plugins
        self._proc_plugins = Proc.plugins
        self._post_plugins = Post.plugins

    def _work(self,infile,outfile,level):
        try:
            chain = read(infile)
            chain = default_args(chain)
            chain = process(chain,self._proc_plugins)
            chain = post_process(chain)
            if level != 'ERROR':
                chain = print_args(chain)
            write(chain,outfile)
        except Exception as e:
            raise e

    def main(self):
        for inp,outpn in zip(self._args.source,self._args.woutput):
            with open(outpn,'wt') as outp:
                self._work(inp,outp,level='ERROR')
