import sys
import zmq
import time

host = '127.0.0.1'
port = 5679

def connect(sock,context,timeout=10):
    communication_sock = context.socket(zmq.PULL)
    communication_port = communication_sock.bind_to_random_port(
            'tcp://*', min_port=6001, max_port=6020, max_tries=100)
    sock.send_json(['run',{'host':host,'port':communication_port}])
    print('communicating with server on port "{0}"'.format(communication_port))
    while True:
        rep = communication_sock.recv_json()
        print('received:', rep)
        if rep[0] == 'done':
            break
    communication_sock.close()

def ping():
    """Sends ping requests and waits for replies."""
    context = zmq.Context()
    sock = context.socket(zmq.PUSH)
    sock.connect('tcp://%s:%s' % (host, port))

    threads = []
    for i in range(5):
        connect(sock,context)

    sock.send_json(['stop',{}])
    sock.close()
    context.term()

if __name__ == '__main__':
    t1 = time.time()
    ping()
    print('time elapsed',time.time()-t1)

