import abc
import logging

from . import utils

logger = logging.getLogger('litscript.formatter')

class BaseFormatter(utils.PluginBase):
    plugtype = 'formatter'
    plugins = {}


class CompactFormatter(BaseFormatter):
    name = 'compact'
    _options = {'linewise':['--linewise']}
    _aliases = utils.optionconverter(_options)

    @property
    def aliases(self):
        return self._aliases

    @property
    def options(self):
        return self._options

    def process(self,cchunk):
        i = 0
        for hunk in cchunk.hunks:
            if i == 0:
                yield hunk.source.formatted
            else:
                yield hunk.source.simple
            yield hunk.stdout.simple
            yield hunk.stderr.simple
            yield hunk.traceback.simple
            i += 1
