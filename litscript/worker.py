from .chunks import Litrunner
from .process import PythonProcessor


def main():
    L = Litrunner()
    L.register_processor(PythonProcessor)
    return L
