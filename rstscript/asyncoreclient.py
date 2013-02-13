import socket
import asyncore
import logging

logger = logging.getLogger('client')
hdlr = logging.FileHandler('./myapp.log')
formatter = logging.Formatter('%(name)s %(asctime)s %(levelname)s: %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel('INFO')

class HTTPClient(asyncore.dispatcher):

    def __init__(self, sockfile ):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connect( sockfile )
        self.store = []

    def handle_connect(self):
        logger.info('connect')
        sent = self.send(b'hallo server')
        logger.info('sent "{0}"'.format(sent))
        pass

    def handle_close(self):
        logger.info('close')
        self.close()

    def handle_read(self):
        logger.info('read')
        receiv = (self.recv(8192)).decode('utf-8')
        if receiv:
            logger.info('received "{0}"'.format(receiv))
            self.close()
            raise asyncore.ExitNow('Client is quitting!')


client = HTTPClient('/tmp/asyncore.sock')
try:
    asyncore.loop()
except asyncore.ExitNow:
    logger.info('exited the event loop')

