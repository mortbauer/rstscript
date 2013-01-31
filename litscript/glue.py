from .chunks import *
from .processors import *
from .__init__ import __version__
from .utils import LitscriptException
from .colorlog import getlogger

logger = getlogger('litscript.glue')

class Litscript(object):
    version = __version__

    def __init__(self,args,loaded_modules):
        logger.info('init Litscript object with args: {0}'.format(args))
        logger.info('loaded modules: {0}'.format(loaded_modules))
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

    def _work(self,infile,outfile):
        try:
            chain = read(infile)
            chain = pre_process(chain,self._pre_plugins)
            chain = process(chain,self._proc_plugins,self._args)
            chain = post_process(chain,self._post_plugins)
            write(chain,outfile)
        except Exception as e:
            raise e
    def _tangle(self,infile,outfile):
        try:
            chain = read(infile)
            for chunk in chain:
                if chunk['type'] == 'code':
                    outfile.write(chunk['content_raw'].getvalue())
        except Exception as e:
            raise e


    def main(self):
        if self._args['woutput']: # weave
            for inp,outpn in zip(self._args['source'],[self._args['woutput']]):
                with open(outpn,'wt') as outp:
                    self._work(inp,outp)
        elif self._args['toutput']: # tangle
            for inp,outpn in zip(self._args['source'],self._args['toutput']):
                with open(outpn,'wt') as outp:
                    self._tangle(inp,outp)
