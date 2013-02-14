import os
import sys
import time
import atexit
import logging
import socketserver
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

class SimpleD(daemonize.Daemon):
    def start(self):
        pid = super().start()

    def run(self):
        while True:
            with open('/tmp/daemonizetest.out','a') as f:
                f.write('hallo\n')
            time.sleep(2)

class SimpleDD(SimpleD):
    def run(self):
        while True:
            with open('/tmp/daemonizetest.out','a') as f:
                f.write('hallo\n')
            time.sleep(2)


class MyDaemon(daemonize.Daemon):
    def run(self):
        while True:
            with open('/tmp/daemonizetest.out','a') as f:
                f.write('hallo\n')
            time.sleep(2)

class MySockDaemon(daemonize.SocketServerDaemon):
    def run(self):
        self.server = socketserver.ThreadingUnixStreamServer(self.sockfile,self.handler)
        self.logger.info('i will serve immediately')
        atexit.register(os.remove,self.sockfile)
        self.server.serve_forever()

if __name__ == '__main__':

    logger = logging.getLogger('daemonizetest')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler('/tmp/daemonizetest.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel('INFO')

    #d = SimpleDD('/tmp/daemonizetest.pid',logger,'/home/martin1')
    #d = SimpleD('/tmp/daemonizetest.pid',logger,'/home/martin1')
    #d = MyDaemon('/tmp/daemonizetest.pid',logger,'/home/martin1')
    d = MySockDaemon('/tmp/daemonizetest.sock','/tmp/daemonizetest.pid',logger,ThreadedEchoRequestHandler,'')
    #d = daemonize.SocketServerDaemon('/tmp/daemonizetest.sock','/tmp/daemonizetest.pid',logger,ThreadedEchoRequestHandler,'')
    if sys.argv[1] == 'start':
        d.start()
    elif sys.argv[1] == 'stop':
        d.stop()
