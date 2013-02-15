import os
import sys
import time
import atexit
import logging
import socketserver
import threading
from rstscript import daemonize


class ThreadedEchoRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        # Echo the back to the client
        data = self.request.recv(1024)
        cur_thread = threading.currentThread()
        response = '%s: %s' % (cur_thread.getName(), data)
        time.sleep(5)
        self.request.send(response.encode('utf-8'))
        return

if __name__ == '__main__':

    logger = logging.getLogger('daemonizetest')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler('/tmp/daemonizetest.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel('INFO')

    d = daemonize.SocketServerDaemon('/tmp/daemonizetest.sock','/tmp/daemonizetest.pid',logger,ThreadedEchoRequestHandler)
    if sys.argv[1] == 'start':
        d.start()
    elif sys.argv[1] == 'stop':
        d.stop()
