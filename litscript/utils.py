import signal
import os


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


# A very Simple and Stupid plugin system in python
# from: http://blog.mathieu-leplatre.info/a-very-simple-and-stupid-plugin-system-in-python.html
def plugins_list(plugins_dirs):
    """ List all python modules in specified plugins folders """
    for path in plugins_dirs.split(os.pathsep):
        for filename in os.listdir(path):
            name, ext = os.path.splitext(filename)
            if ext.endswith(".py"):
                yield name

def import_plugins(plugins_dirs, env):
    """ Import modules into specified environment (symbol table) """
    for p in plugins_list(plugins_dirs):
        try:
            m = __import__(p, env)
            env[p] = m
        except Exception as e:
            print(e)

