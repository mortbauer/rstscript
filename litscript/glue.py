from .chunks import *
from .processors import *
import logging

def worker(infilen,outfilen,settings={},log='console',
           logfile='lit.log',level='ERROR'):
    # register all imported plugins
    plugs = Pre.__subclasses__()
    plugs.extend(Proc.__subclasses__())
    plugs.extend(Post.__subclasses__())
    for x in plugs:
        x.register()

    # create logger
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    # do conversion
    try:
        infi = open(infilen,'rt')
        outfi = open(outfilen,'wt')
        chain = read(infi)
        chain = default_args(chain)
        chain = process(chain,Proc.plugins)
        chain = post_process(chain)
        if level != 'ERROR':
            chain = print_args(chain)
        write(chain,outfi)
    except Exception as e:
        raise e
    finally:
        infi.close()
        outfi.close()
