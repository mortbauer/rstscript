import zmq
import yaml
import signal

from rstscript import zmqserver
from rstscript import daemonize
from rstscript import kernel
from rstscript import client

configs = yaml.load(open('/data/devel/python/rstscript/rstscript-git/rstscript/defaults/config.yml','r').read())


class Handler(zmqserver.MessageHandler):

    def run(self,socket,data,logger):
        socket.send_json(['log','hha'])
        socket.send_json(['log','hha'])
        socket.send_json(['done','hha'])

#server = zmqserver.ZmqProcess(zmq.PULL,host=configs['host'],port=configs['port'],bind=True, Handler=Handler)
#daemon = daemonize.Daemon('pid',target=server.start,foreground=True)
#signal.signal(signal.SIGINT,server.stop)
configs['debug']=True
daemon = kernel.RSTDaemon(configs,foreground=False)
daemon.start()
cli = client.Client(configs['host'],configs['port'])
cli.connect()
cli.start()

