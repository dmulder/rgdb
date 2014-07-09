#!/usr/bin/python

# The MIT License (MIT)
# 
# Copyright (c) 2014 David Mulder
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
