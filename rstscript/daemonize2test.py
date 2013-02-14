"""\
Base daemon test file.

This file tests the base daemon (runs it's test logic). The daemon is
started, then stopped, then started then restarted then stopped again.

The output of this file should look like this (with different pids):

starting daemon
listing processes
15554 ?        S      0:00 python3 daemon.py start
-rw-rw-rw- 1 seth seth 6 2009-06-13 14:55 /tmp/test_daemon.pid
stopping daemon
listing processes
ls: cannot access /tmp/test_daemon.pid: No such file or directory
starting daemon
listing processes
15572 ?        S      0:00 python3 daemon.py start
-rw-rw-rw- 1 seth seth 6 2009-06-13 14:55 /tmp/test_daemon.pid
restarting daemon
listing processes
15582 ?        S      0:00 python3 daemon.py restart
-rw-rw-rw- 1 seth seth 6 2009-06-13 14:55 /tmp/test_daemon.pid
stopping daemon
listing processes
ls: cannot access /tmp/test_daemon.pid: No such file or directory
"""

import os, time

if __name__ == '__main__':
	start_cmd = 'python3 daemon.py start'
	stop_cmd = 'python3 daemon.py stop'
	restart_cmd = 'python3 daemon.py restart'

	os.chdir(os.path.abspath(os.path.dirname(__file__)))

	print('starting daemon')
	os.system(start_cmd)
	time.sleep(0.2)
	print('listing processes')
	os.system('ps x | grep "python3 daemon.py" | grep -v grep')
	os.system('ls -l /tmp/test_daemon.pid')

	print('stopping daemon')
	os.system(stop_cmd)
	time.sleep(0.2)
	print('listing processes')
	os.system('ps x | grep "python3 daemon.py" | grep -v grep')
	os.system('ls -l /tmp/test_daemon.pid')

	print('starting daemon')
	os.system(start_cmd)
	time.sleep(0.2)
	print('listing processes')
	os.system('ps x | grep "python3 daemon.py" | grep -v grep')
	os.system('ls -l /tmp/test_daemon.pid')
	print('restarting daemon')
	os.system(restart_cmd)
	time.sleep(0.2)
	print('listing processes')
	os.system('ps x | grep "python3 daemon.py" | grep -v grep')
	os.system('ls -l /tmp/test_daemon.pid')
	print('stopping daemon')
	os.system(stop_cmd)
	time.sleep(0.2)
	print('listing processes')
	os.system('ps x | grep "python3 daemon.py" | grep -v grep')
	os.system('ls -l /tmp/test_daemon.pid')
