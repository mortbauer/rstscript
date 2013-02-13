import time
import asyncore
import socket
import logging

logger = logging.getLogger('server')
hdlr = logging.FileHandler('./myapp.log')
formatter = logging.Formatter('%(name)s %(asctime)s %(levelname)s: %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel('INFO')

class EchoHandler(asyncore.dispatcher_with_send):
    def __init__(self,sock):
        super(self.__class__,self).__init__(sock)
        self.working = False

    def readable(self):
        return not self.working

    def writeable(self):
        return not self.working

    def handle_read(self):
        logger.info('reading')
        data = self.recv(8192)
        if data:
            logger.info('read "{0}"'.format(data))
            self.domywork(data)
        self.close()

    def domywork(self,data):
        logger.info('i\'m working as hell ;)')
        time.sleep(5)
        logger.info('I finnished my intensive work')
        self.send(b'I finnished my intensive work')
        return



class EchoServer(asyncore.dispatcher):

    def __init__(self,sock):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(sock)
        self.listen(5)

    def handle_accepted(self, sock, addr):
        logger.info('accepted')
        print('Incoming connection from %s' % repr(addr))
        handler = EchoHandler(sock)

sock='/tmp/asyncore.sock'
server = EchoServer(sock)
asyncore.loop()
