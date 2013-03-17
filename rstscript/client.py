import sys
import zmq


class Client(object):
    def __init__(self,host,port,min_port=6001,
            max_port=6100,max_tries=20):
        self.context = zmq.Context()
        self.host = host
        self.port = port
        self.min_port = min_port
        self.max_port = max_port
        self.max_tries = max_tries

    def connect(self):
        self.sock = self.context.socket(zmq.REQ)
        self.sock.connect('tcp://{host}:{port}'.
                format(host=self.host,port=self.port))

    def start(self):
        self.sock.send_json(['start',{}])
        if 'done' in self.sock.recv_json():
            return True

    def stop(self):
        self.sock.send_json(['stop',{}])
        self.disconnect()
        self.context = zmq.Context()
        self.connect()
        return True

    def send(self,msgtype,msg):
        self.sock.send_json([msgtype,msg])

    def sendrecv(self,msgtype,msg):
        self.send(msgtype,msg)
        return self.sock.recv_json()

    def dispatch(self,action):
        """ returns a socket, connected to the server
        and getting json messages """
        sock = self.context.socket(zmq.PULL)
        port = sock.bind_to_random_port(
                'tcp://*', min_port=self.min_port,
                max_port=self.max_port, max_tries=self.max_tries)
        self.send(action,{'host':self.host,'port':port})
        return sock

    def run(self,data):
        sock = self.context.socket(zmq.PULL)
        port = sock.bind_to_random_port(
                'tcp://*', min_port=self.min_port,
                max_port=self.max_port, max_tries=self.max_tries)
        data['port'] = port
        data['host'] = self.host
        self.send('run',data)
        if 'done' in self.sock.recv_json():
            while True:
                msg = sock.recv_json()
                if msg[0] == 'done':
                    break
                elif msg[0] == 'log':
                    print(msg[1],file=sys.stderr)

    def disconnect(self):
        self.sock.close()
        self.context.term()

    def close(self):
        self.sock.close()
        self.context.term()

