from IPython.lib.kernel import find_connection_file
from IPython.zmq.blockingkernelmanager import BlockingKernelManager


class IPythonConnection(object):
    """ connects to a running IPython Kernel
    and can execute code there

    example usage:

        1. start the IPython Kernel by typing::

            ipython kernel

            [IPKernelApp] To connect another client to this kernel, use:
            [IPKernelApp] --existing kernel-4933.json

        or even more useful to see the output::

            ipython qtconsol

            [IPKernelApp] To connect another client to this kernel, use:
            [IPKernelApp] --existing kernel-4933.json

        in a shell which will start the IPython Kernel and gives you
        information on how to connect to it, you will need that immedeately.

        2. create a IPythonConnection with the value from before::

            ipc = IPythonConnection(4933)


        3. now you can execute code like::

            ipc.run_cell('print("Hello World")')

    """

    def __init__(self,connection):
        self.cf = find_connection_file(connection)
        self.km = BlockingKernelManager(connection_file=self.cf)
        self.km.load_connection_file()
        self.km.start_channels()

    def run_cell(self,code):
        #self.shell = self.km.shell_channel
        self.shell.execute(code)
