import signal


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
