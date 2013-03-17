import zmq
import time
import signal
import threading
from zmq.utils import jsonapi

from rstscript import base


class Handler(base.MessageHandler):

    def run(self,socket,data):
        socket.send_json(['log','hha'])
        socket.send_json(['log','hha'])
        socket.send_json(['done','hha'])

if __name__ == '__main__':
    server = base.ZmqProcess(zmq.PULL,host='127.0.0.1',port=5577,bind=True, Handler=Handler)
    signal.signal(signal.SIGINT,server.stop)
    server.start()
