import socket
import select

# Connect to the server
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#address = '/tmp/socketserver.sock'
address = '.communication.sock'
s.connect(address)
s.setblocking(0)

# Send the data
message = 'Hello, world'
print('Sending : "%s"' % message)
len_sent = s.send(message.encode('utf-8'))

# Receive a response
ready = select.select([s], [], [], 6)
if ready:
    response = s.recv(1024)
    print('Received: "%s"' % response)
    # Clean up
    s.close()

