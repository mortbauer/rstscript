import time
import threading
import socketserver

class ThreadedEchoRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        # Echo the back to the client
        data = self.request.recv(1024)
        cur_thread = threading.currentThread()
        response = '%s: %s' % (cur_thread.getName(), data)
        time.sleep(5)
        self.request.send(response.encode('utf-8'))
        return

if __name__ == '__main__':
    address = '/tmp/socketserver.sock' # let the kernel give us a port
    server = socketserver.ThreadingUnixStreamServer(address,ThreadedEchoRequestHandler)
    t = threading.Thread(target=server.serve_forever)
    t.setDaemon(True) # don't hang on exit
    t.start()
    print('Server loop running in thread:', t.getName())

        #server.socket.close()

