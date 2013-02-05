import os
import abc
import signal
import logging

logger = logging.getLogger('litscript.utils')

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
        if not '__abstractmethods__' in self.__dict__:
            self.plugins[self.name] = self
            return True
        else:
            logger.error('plugin "{0}" is abstract, disabling it'
                    .format(self.name))
            return False
    @abc.abstractmethod
    def name(self):
        pass
    @abc.abstractmethod
    def process(self):
        pass
    @abc.abstractmethod
    def aliases(self):
        pass
    @abc.abstractmethod
    def options(self):
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

