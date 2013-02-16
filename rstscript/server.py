import os
import sys
import time
import ujson
import logging
import threading
import colorama
import socketserver

from rstscript.litrunner import Litrunner

class ColorizingStreamHandler(logging.StreamHandler):
    # Courtesy http://plumberjack.blogspot.com/2010/12/colorizing-logging-output-in-terminals.html
    # Tweaked to use colorama for the coloring

    """
    Sets up a colorized logger, which is used ltscript
    """
    color_map = {
        logging.INFO: colorama.Fore.WHITE,
        logging.DEBUG: colorama.Style.DIM + colorama.Fore.CYAN,
        logging.WARNING: colorama.Fore.YELLOW,
        logging.ERROR: colorama.Fore.RED,
        logging.CRITICAL: colorama.Back.RED,
        logging.FATAL: colorama.Back.RED,
    }

    def __init__(self, stream, color_map=None):
        logging.StreamHandler.__init__(self,
                                    colorama.AnsiToWin32(stream).stream)
        if color_map is not None:
            self.color_map = color_map

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            # Don't colorize a traceback
            parts = message.split('\n', 1)
            parts[0] = self.colorize(parts[0], record)
            message = '\n'.join(parts)
        return message

    def colorize(self, message, record):
        try:
            return (self.color_map[record.levelno] + message +
                    colorama.Style.RESET_ALL)
        except KeyError:
            return message

class RstscriptHandler(socketserver.BaseRequestHandler):

    def handle(self):
        t1 = time.time()
        # get the options
        data = self.request.recv(1024)
        options = ujson.loads(data)
        # set default job options
        for x in self.server.configs:
            options.setdefault(x,self.server.configs[x])
        # if debugging mode
        if options['debug'] and options['stdout']:
            # getlogger
            self.logger = logging.getLogger('rstscript.handler.{0}'.
                    format(threading.current_thread().name))
            #self.logger.addHandler(logging.StreamHandler(open(options['stdout'],'w')))
            formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
            handler = ColorizingStreamHandler(open(options['stdout'],'w'))
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            # log to central log file
            self.logger = self.server.logger
        # test if project is new
        project_id = (options['input'],options['woutput'],options['toutput'])
        if project_id in self.server.projects:
            if self.server.projects[project_id].options != options:
                self.server.projects[project_id] = Litrunner(options,self.logger)
        else:
            self.server.projects[project_id] = Litrunner(options,self.logger)
        # now run the project
        self.server.projects[project_id].run()
        print('served in "{0}" sec'.format(time.time()-t1))
        # send some response
        self.request.send(ujson.dumps(options).encode('utf-8'))
        return

#def handler(clientsocket):
    #data = clientsocket.recv(1024).decode('utf-8')
    #clientsocket.send('ok "{0}"'.format(data).encode('utf-8'))
