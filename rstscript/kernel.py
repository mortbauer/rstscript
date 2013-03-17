"""Generic linux daemon base class for python 3.x."""

import sys
import zmq
import signal
import logging
import threading

from rstscript import zmqserver
from rstscript import daemonize
from rstscript import utils
from rstscript import litrunner

class Handler(zmqserver.MessageHandler):

    def __init__(self,*args,**kwargs):
        super().__init__(**kwargs)
        self.projects = {}

    def run(self,socket,data,logger):
        # test if project is new
        try:
            project_id = (data['input'],data['woutput'],data['toutput'])
        except KeyError:
            logger.error('there needs to be at least the "input" key in the data')
        # do the work
        try:
            if project_id in self.projects and not data.get('rebuild',False):
                # test if default options changed
                if self.projects[project_id].options['options'] != data['options']:
                    self.projects[project_id] = litrunner.Litrunner(data,logger)
                else:
                    # the logger needs to be renewed, has info from old thread
                    # and so on
                    self.projects[project_id].logger = logger
            else:
                # completely new
                self.projects[project_id] = litrunner.Litrunner(data,logger)
            # now run the project
            self.projects[project_id].run()
        except Exception as e:
            logger.error('an unexpected error occured "{0}"'.format(e))
        finally:
            pass
        # send some response
        socket.send_json(['done',{'aaa':'hha'}])

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
                port=self.port,bind=True,Handler=Handler)
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
