import sys
import zmq
import signal
import datetime
from zmq.utils import jsonapi

from zmq.eventloop import zmqstream,ioloop

class Client(object):
    def __init__(self,host,port,min_port=6001,
            max_port=6100,max_tries=20):
        self.context = zmq.Context()
        self.host = host
        self.port = port
        self.min_port = min_port
        self.max_port = max_port
        self.max_tries = max_tries
        self.pull_sock = self.context.socket(zmq.PULL)
        self.answer_loop = ioloop.IOLoop()
        self.answer_loop.add_timeout(datetime.timedelta(seconds=2),
                self.timedout)
        self.pull_loop = ioloop.IOLoop()

    def connect(self):
        self.answer_sock = self.context.socket(zmq.REQ)
        self.answer_sock.connect('tcp://{host}:{port}'.
                format(host=self.host,port=self.port))
        self.answer_stream = zmqstream.ZMQStream(
                self.answer_sock,io_loop=self.answer_loop)
        self.answer_stream.on_recv(self.answer_handler)

    def timedout(self):
        self.answer_loop.stop()
        self.answer_sock.close()
        self.connect()
        self.inner = self.context.socket(zmq.PUSH)
        self.inner.connect('inproc://rstscript')
        self.inner.send_json(['timeout'])
        self.inner.close()

    def ping(self):
        self.answer_sock.send_json(['ping',{}])
        self.answer_loop.start()
        return True

    def stop(self):
        self.answer_sock.send_json(['stop',{}])
        self.answer_loop.start()
        return True

    def run(self,data):
        self.pull_port = self.pull_sock.bind_to_random_port(
                'tcp://*', min_port=self.min_port,
                max_port=self.max_port, max_tries=self.max_tries)
        stream_pull = zmqstream.ZMQStream(self.pull_sock,io_loop=self.pull_loop)
        stream_pull.on_recv(self.pull_handler)
        data['port'] = self.pull_port
        data['host'] = self.host
        self.answer_sock.send_json(['run',data])
        self.answer_loop.start()
        self.pull_loop.start()

    def pull_handler(self,data):
        msg = jsonapi.loads(data[-1])
        if msg[0] == 'done':
            print('\nFinnished job',msg[1])
            self.pull_loop.stop()
        elif msg[0] == 'log':
            print(msg[1])
        else:
            print('??',msg)

    def answer_handler(self,data):
        # for now just stop the loop
        self.answer_loop.stop()

    def disconnect(self):
        """ actually we do not really need that
        python closes the stuff for us"""
        self.answer_sock.close()
        self.answer_sock.close()
        self.context.term()

    def close(self,sign=None,frame=None):
        self.answer_sock.close()
        self.answer_sock.close()
        self.pull_sock.close()
        self.context.term()

