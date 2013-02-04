from .chunks import Litrunner
from .process import PythonProcessor
from .formatter import CompactFormatter


def main():
    L = Litrunner()
    L.register_processor(PythonProcessor)
    L.register_formatter(CompactFormatter)
    L.set_defaults(PythonProcessor.name,{},CompactFormatter.name,{})
    L.test_readiness()
    return L
