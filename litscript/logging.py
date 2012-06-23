import logging
from colorama import Fore


class ColorFormatter(logging.Formatter):
    """Simple python logging colorizer formatter """

    def format(self, record):
        """Format the record with colors."""
        message = logging.Formatter.format(self, record)
        level = record.levelname
        if level == 'DEBUG':
            color = Fore.BLUE
        elif level == 'INFO':
            color = Fore.GREEN
        elif level == 'WARNING':
            color = Fore.MAGENTA
        elif level == 'ERROR':
            color = Fore.RED
        elif level == 'CRITICAL':
            color = Fore.RED
        return message.replace('$COLOR', color).replace('$RESET',Fore.RESET)


def make_colored_stream_handler():
    """Return a colored stream handler"""
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('$COLOR%(levelname)s: $RESET %(message)s'))
    return handler


def make_file_handler(filename):
    handler = logging.FileHandler(filename)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    return handler
