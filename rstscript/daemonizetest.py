import sys
import time
import logging
from rstscript import daemonize

class MyDaemon(daemonize.Daemon):
    def run(self):
        while True:
            with open('/tmp/daemonizetest.out','a') as f:
                f.write('hallo\n')
            time.sleep(2)

if __name__ == '__main__':

    logger = logging.getLogger('daemonizetest')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler('/tmp/daemonizetest.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel('INFO')

    d = MyDaemon('/tmp/daemonizetest.pid',logger)
    if sys.argv[1] == 'start':
        d.start()
    elif sys.argv[1] == 'stop':
        d.stop()
