#!/usr/bin/python
import time, sys, os, os.path, zmq
from subprocess import Popen, PIPE

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://127.0.0.1:%s" % sys.argv[1])
filename = ''
previous_file = ''
line_num = None
proc = None

while True:
	mesg = socket.recv()
	socket.send(mesg)
	if (mesg and proc) or mesg == 'exit':
		# Kill the process and the spawned child (proc + 1).
		try:
			cproc = Popen(['grep', '-v', 'grep'], stdin=Popen(['grep', filename], stdin=Popen(['grep', '-v', '/bin/sh'], stdin=Popen(['grep', str(proc)], stdin=Popen(['ps', '-eo', 'pid,ppid,cmd'], stdout=PIPE).stdout, stdout=PIPE).stdout, stdout=PIPE).stdout, stdout=PIPE).stdout, stdout=PIPE).communicate()[0].split()[0]
			os.system('kill -9 %s %s' % (str(proc), cproc))
			os.system('rm %s/.%s.swp' % (os.path.dirname(previous_file), os.path.basename(previous_file)))
		except:
			pass
	if mesg == 'exit':
		break
	if mesg:
		filename, line_num = mesg.split(':')
		proc = Popen(['/bin/sh', '-c', 'vim +%s +"set cursorline" +"set so=999" %s' % (line_num, filename)]).pid
		previous_file = filename

socket.close()
