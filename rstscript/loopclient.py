
import zmq
import signal
from zmq.eventloop import zmqstream,ioloop

def getcommand(data):
    print('received',data)

def process_message(data):
    print('reply',data)



def client(port_req):
    clientloop = ioloop.IOLoop.instance()
    def stop(sign=None,frame=None):
        clientloop.stop()
    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    port_pull = socket_pull.bind_to_random_port('tcp://*', min_port=6101, max_port=6200, max_tries=100)
    stream_pull = zmqstream.ZMQStream(socket_pull)
    stream_pull.on_recv(getcommand)
    print(("Connected to server with port %s" % port_pull))

    socket_req = context.socket(zmq.REQ)
    socket_req.connect ("tcp://localhost:%s" % port_req)
    stream_req = zmqstream.ZMQStream(socket_req)
    stream_req.on_recv(process_message)
    stream_req.send_json(['run',{'host':'localhost','port':port_pull}])
    print("Connected to publisher with port %s" % port_req)
    signal.signal(signal.SIGINT,stop)
    clientloop.start()
    print("Worker has stopped processing messages.")

client(5679)
