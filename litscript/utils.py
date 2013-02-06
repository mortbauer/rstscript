import os
import sys
import abc
import signal
import logging
import argparse

logger = logging.getLogger('litscript.utils')

class LitParser(argparse.ArgumentParser):
    #def exit(self):
        #raise LitscriptException('couldn\'t parse the arguments')
    def error(self,message):
        raise LitscriptException('couldn\'t parse the arguments')

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


def optionconverter(options):
    rev = {}
    for opt in options:
        for alias in options[opt]:
            rev[alias] = opt
    return rev


class classproperty(object):
     def __init__(self, getter):
         self.getter= getter
     def __get__(self, instance, owner):
         return self.getter(owner)

class PluginBase(metaclass=abc.ABCMeta):
    @classmethod
    def register(self):
        if ('__abstractmethods__' in self.__dict__ and
                len(self.__dict__['__abstractmethods__'])>0):
            raise LitscriptException('{0} "{1}" from module "{2}"'
            'is abstract, disabling it'
            .format(self.plugtype,self.name,self.__module__))
            return False
        else:
            if not hasattr(self.plugins,self.name):
                self.plugins[self.name] = self
                logger.info('registered {0} "{1}" from module "{2}"'.
                        format(self.plugtype,self.name,self.__module__))
            else:
                raise LitscriptException('{0} "{1}" module file "{2}" is '
                'already registered,no effect'.
                format(self.plugtype,self.name,self.__module__))
            return True
    @abc.abstractmethod
    def name(self):
        pass
    @abc.abstractmethod
    def process(self):
        pass

class LitscriptException(Exception):
    """Base class for exceptions in this module."""
    pass


class TimeoutException(Exception):
    pass


def timeout(timeout_time, default):
    def timeout_decorated(func_to_decorate):
        def f2(*args,**kwargs):
            def timeout_handler(signum, frame):
                raise TimeoutException()

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_time)  # triger alarm in timeout_time seconds
            try:
                retval = func_to_decorate(*args,**kwargs)
            except TimeoutException:
                return default
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_decorated

