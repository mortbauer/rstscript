import os
import sys
import time
import ujson
import socketserver

from rstscript.litrunner import Litrunner


class RstscriptHandler(socketserver.BaseRequestHandler):

    def handle(self):
        t1 = time.time()
        # get the options
        data = self.request.recv(1024)
        options = ujson.loads(data)
        # set default job options
        for x in self.server.configs:
            options.setdefault(x,self.server.configs[x])
        # test if project is new
        project_id = (options['input'],options['woutput'],options['toutput'])
        if project_id in self.server.projects:
            if self.server.projects[project_id].options != options:
                self.server.projects[project_id] = Litrunner(options)
        else:
            self.server.projects[project_id] = Litrunner(options)
        # now run the project
        self.server.projects[project_id].run()
        print('served in "{0}" sec'.format(time.time()-t1))
        # send some response
        self.request.send(ujson.dumps(options).encode('utf-8'))
        return

#def handler(clientsocket):
    #data = clientsocket.recv(1024).decode('utf-8')
    #clientsocket.send('ok "{0}"'.format(data).encode('utf-8'))
