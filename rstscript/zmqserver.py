import threading
import logging
import zmq
from zmq.eventloop import ioloop, zmqstream
from zmq.utils import jsonapi as json

from rstscript import utils

"""
Modul to set up a ZmqServer which listens to a port and dispatches each request
through the MessageHandler which uses the message to dispatch to the specified
handler in a separate thread.

[PULL] <- [PUSH]
|
|
 -> MessageHandler(['type','{data}']) -> handler.type(msg)

"""

class ZmqBase(threading.Thread):
    """
    This is the base for all processes and offers utility functions
    for setup and creating new streams.

    """
    def __init__(self,sock_type,host,port,bind=True):
        super().__init__()
        self.context = zmq.Context()
        self.loop = ioloop.IOLoop.instance()
        self.sock_type = sock_type
        self.host = host
        self.port = port
        self.bind = bind

    def setup(self):
        """
        Creates a :class:`~zmq.eventloop.zmqstream.ZMQStream`.

        :param sock_type: The ØMQ socket type (e.g. ``zmq.REQ``)
        :param addr: Address to bind or connect to formatted as *host:port*,
                *(host, port)* or *host* (bind to random port).
                If *bind* is ``True``, *host* may be:

                - the wild-card ``*``, meaning all available interfaces,
                - the primary IPv4 address assigned to the interface, in its
                  numeric representation or
                - the interface name as defined by the operating system.

                If *bind* is ``False``, *host* may be:

                - the DNS name of the peer or
                - the IPv4 address of the peer, in its numeric representation.

                If *addr* is just a host name without a port and *bind* is
                ``True``, the socket will be bound to a random port.
        :param bind: Binds to *addr* if ``True`` or tries to connect to it
                otherwise.
        :param callback: A callback for
                :meth:`~zmq.eventloop.zmqstream.ZMQStream.on_recv`, optional
        :param subscribe: Subscription pattern for *SUB* sockets, optional,
                defaults to ``b''``.
        :returns: A tuple containg the stream and the port number.

        """
        sock = self.context.socket(self.sock_type)


        try:
            # Bind/connect the socket
            if self.bind:
                if self.port:
                    sock.bind('tcp://%s:%s' % (self.host, self.port))
                else:
                    self.port = sock.bind_to_random_port('tcp://%s' % self.host)
            else:
                sock.connect('tcp://%s:%s' % (self.host, self.port))
        except Exception as e:
            logging.error('couldn\'t {2} to port {0}: {1}'.
                    format(self.port,e,'bind' if self.bind else 'connect'))
            raise

    def run(self):
        self.setup()
        self.loop.start()


    def stop(self,sign=None,frame=None):
        self.loop.stop()

class ZmqProcess(threading.Thread):
    """
    This is the base for all processes and offers utility functions
    for setup and creating new streams.

    """
    def __init__(self,sock_type,host,port,bind=True,
            Handler=None,args=(),kwargs={},subscribe=b''):
        super().__init__()
        self.context = zmq.Context()
        self.loop = ioloop.IOLoop()
        self.sock_type = sock_type
        self.host = host
        self.port = port
        self.bind = bind
        self.Handler = Handler
        self.args = args
        self.kwargs = kwargs
        self.subscribe = subscribe

    def setup(self):
        self.kwargs['stop'] = self.stop
        self.handler = self.Handler(*self.args,**self.kwargs)

    def stream(self):
        """
        Creates a :class:`~zmq.eventloop.zmqstream.ZMQStream`.

        :param sock_type: The ØMQ socket type (e.g. ``zmq.REQ``)
        :param addr: Address to bind or connect to formatted as *host:port*,
                *(host, port)* or *host* (bind to random port).
                If *bind* is ``True``, *host* may be:

                - the wild-card ``*``, meaning all available interfaces,
                - the primary IPv4 address assigned to the interface, in its
                  numeric representation or
                - the interface name as defined by the operating system.

                If *bind* is ``False``, *host* may be:

                - the DNS name of the peer or
                - the IPv4 address of the peer, in its numeric representation.

                If *addr* is just a host name without a port and *bind* is
                ``True``, the socket will be bound to a random port.
        :param bind: Binds to *addr* if ``True`` or tries to connect to it
                otherwise.
        :param callback: A callback for
                :meth:`~zmq.eventloop.zmqstream.ZMQStream.on_recv`, optional
        :param subscribe: Subscription pattern for *SUB* sockets, optional,
                defaults to ``b''``.
        :returns: A tuple containg the stream and the port number.

        """
        sock = self.context.socket(self.sock_type)


        try:
            # Bind/connect the socket
            if self.bind:
                if self.port:
                    sock.bind('tcp://%s:%s' % (self.host, self.port))
                else:
                    port = sock.bind_to_random_port('tcp://%s' % self.host)
            else:
                sock.connect('tcp://%s:%s' % (self.host, self.port))
        except Exception as e:
            logging.error('couldn\'t {2} to port {0}: {1}'.
                    format(self.port,e,'bind' if self.bind else 'connect'))
            raise

        # Add a default subscription for SUB sockets
        if self.sock_type == zmq.SUB:
            sock.setsockopt(zmq.SUBSCRIBE, self.subscribe)

        # Create the stream and add the callback
        stream = zmqstream.ZMQStream(sock, self.loop)
        if self.handler:
            stream.on_recv_stream(self.handler)

        return stream

    def run(self):
        self.setup()
        self.stream()
        logging.warn('listening on port {0} of host {1}'.format(self.port,self.host))
        self.loop.start()


    def stop(self,sign=None,frame=None):
        self.loop.stop()

class MessageHandler(object):
    """
    Base class for message handlers for a :class:`ZMQProcess`.

    Inheriting classes only need to implement a handler function for each
    message type.

    """
    def __init__(self,stop=None,json_load=-1):
        self._json_load = json_load
        self._context = zmq.Context()
        self._stop = stop

    def _logger(self,socket,loglevel):
        return utils.Logger(socket,loglevel=loglevel)

    def __call__(self, stream, msg):
        """
        Gets called when a messages is received by the stream this handlers is
        registered at. *msg* is a list as return by
        :meth:`zmq.core.socket.Socket.recv_multipart`.

        """
        # Try to JSON-decode the index "self._json_load" of the message
        try:
            msg_type, data = json.loads(msg[self._json_load])
            msg[self._json_load] = data
        except IndexError:
            logging.error('the message must have exactly two '
            'parts, you sent "{0}"'.format(msg))
            stream.send_json(['error',{}])
            return

        # Get the actual message handler and call it
        if msg_type.startswith('_'):
            logging.error('message type {0} starts with an "_",'
             'not allowed, private'.format(msg_type))
            stream.send_json(['error',{}])
        elif msg_type == 'stop':
            stream.send_json(['alive',{}])
            self._stop()
        elif msg_type == 'ping':
            stream.send_json(['alive',{}])
        else:
            try:
                target = getattr(self, msg_type)
                socket = self._context.socket(zmq.PUSH)
                socket.connect('tcp://{host}:{port}'.
                        format(host=data['host'],port=data['port']))
                thread = threading.Thread(target=target,
                        args=(socket,data,self._logger(
                            socket,data.get('loglevel','WARN'))),daemon=True)
                thread.start()
                logging.info('started thread for {0} on port {1}'
                        .format(target,data['port']))
                stream.send_json(['done',{}])
            except AttributeError:
                logging.error('handler {0} doesn\'t support "{1}"'
                        .format(self.__class__,msg_type))
                stream.send_json(['error',{}])
            except KeyError:
                logging.error('except for "stop" every message data'
                        ' needs the key "host" and "port"')
                stream.send_json(['error',{}])
