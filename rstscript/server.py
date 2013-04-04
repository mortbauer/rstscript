import os
import sys
import time
import ujson
import logging
import threading
import socketserver

from rstscript.litrunner import Litrunner

class RstscriptHandler(socketserver.BaseRequestHandler):

    def handle(self):
        t1 = time.time()
        # get the options
        data = self.request.recv(1024)
        data = ujson.loads(data)
        if data[0] == 'run':
            pid = data[1]
            options = data[2]
            # set default job options
            for x in self.server.configs:
                options.setdefault(x,self.server.configs[x])
            # if debugging mode
            stderr = None
            if not options['quiet']:
                # getlogger
                self.logger = logging.getLogger('rstscript.handler.{0}'.
                        format(threading.current_thread().name))
                formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
                stderr = open('/proc/{0}/fd/2'.format(pid),'w')
                handler = ColorizingStreamHandler(stderr)
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                if options['debug']:
                    self.logger.setLevel('DEBUG')
                else:
                    self.logger.setLevel(
                            getattr(logging,options['loglevel'].upper(),'WARNING'))
                # add also the server handlers, so logging to the central log file
                # happens as well
                for handler in self.server.logger.handlers:
                    self.logger.addHandler(handler)
            else:
                # log to central log file
                self.logger = self.server.logger
            self.logger.info('current running threads "{0}"'.
                    format(len(threading.enumerate())))
            # test if project is new
            project_id = (options['input'],options['woutput'],options['toutput'])
            # do the work
            try:
                if project_id in self.server.projects and not options['rebuild']:
                    # test if default options changed
                    if self.server.projects[project_id].options['options'] != options['options']:
                        self.server.projects[project_id] = Litrunner(options,
                                self.logger)
                    else:
                        # the logger needs to be renewed, has info from old thread
                        # and so on
                        self.server.projects[project_id].logger = self.logger
                else:
                    # completely new
                    self.server.projects[project_id] = Litrunner(options,
                            self.logger)
                # now run the project
                self.server.projects[project_id].run()
            except Exception as e:
                self.logger.exception('an unexpected error occured')
            finally:
                if stderr:
                    stderr.close()
            # send some response
            self.request.send(ujson.dumps(options).encode('utf-8'))
            self.server.logger.info('served in "{0}" sec'.format(time.time()-t1))
            return
        elif data[0] == 'stop':
            self.server.shutdown()
