"""Generic linux daemon base class for python 3.x."""

import sys
import zmq
import signal
import logging
import threading

from rstscript import zmqserver
from rstscript import daemonize
from rstscript import litrunner


class ZmqHandler(zmqserver.MessageHandler,litrunner.LitServer):

    def __init__(self,*args,**kwargs):
        super(ZmqHandler,self).__init__(**kwargs)
        self.projects = {}

    def run(self,socket,data,logger):
        # send some response by calling Litrunner.run method
        socket.send_json(super(ZmqHandler,self).run(data,logger=logger))

class RSTDaemon(daemonize.Daemon):

    def __init__(self,configs):
        super().__init__(configs['pidfile'],
                foreground=configs.get('foreground',False))
        self.pidfile = configs['pidfile']
        self.host = configs['host']
        self.port = configs['port']
        self.configs = configs

    def start(self):
        self.server = zmqserver.ZmqProcess(zmq.REP,host=self.host,
                port=self.port,bind=True,Handler=ZmqHandler)
        signal.signal(signal.SIGINT,self.interupt)
        super().start()

    def interupt(self,signum, frame):
        logging.warn('catched interrupt "{0}", shutting down'
                .format(signum))
        self.stop()

    def stop(self):
        self.server.stop()

    def run(self):
        # hook up to remove the socket if the server ends regulary, won't
        # happen if you just kill the process
        try:
            self.server.start()
        except:
            logging.exception('the server was interuppted')
