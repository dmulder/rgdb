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

import paramiko, sys, time, re, zmq, os, readline, random, signal, getpass, pickle

class gdb:
    def __init__(self, args, host, user='root'):
        self.ssh = None
        self.channel = None
        self.socket = None
        self.pid = ''
        self.args = args
        self.host = host
        self.location = ''
        self.uname = ''
        self.debugger = 'gdb'
        self.__connect__(user)
        signal.signal(signal.SIGINT, self.stop)

    def __connect__(self, user='root'):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.host, username=user)
        except:
            self.ssh.connect(self.host, username=raw_input('Username: '), password=getpass.getpass('Password: '))
        self.uname = self.ssh.exec_command('uname')[1].read().strip()
        if self.uname == 'Darwin':
            self.debugger = 'lldb'
        self.binary = 'None' if not self.args else self.args[0] if int(self.ssh.exec_command('file %s >/dev/null; echo $?' % self.args[0])[1].read().strip()) == 0 else 'None'
        self.channel = self.ssh.invoke_shell()
        self.channel.resize_pty(width=500, height=500)
        self.channel.recv(2048)
        self.channel.send('%s %s\n' % (self.debugger, ' '.join(self.args)))
        self.__wait_gdb__()
        # Disable hardware watch points (use software watchpoints instead)
        if self.debugger == 'gdb':
            self.channel.send('set can-use-hw-watchpoints 0\n')
            self.__wait_gdb__()

    def EOF(self):
        children = self.ssh.exec_command('ps -eo pid,command | grep "%s %s" | grep -v grep' % (self.debugger, ' '.join(self.args)))[1].read().strip().split('\n')
        if len(children) == 1:
            try:
                self.ssh.exec_command('kill -9 %s' % children[0].split()[0])
            except:
                pass
        self.close()
        if self.socket:
            self.socket.send('exit')
            self.socket.recv()
            self.socket.close()
        exit(1)

    def stop(self, signal, frame):
        self.EOF()

    def __wait_gdb__(self):
        data = ''
        while not any([stop in data.strip().split('\n')[-1] for stop in ['(%s)' % self.debugger, '(y or n)', '(y or [n])']]):
            if self.channel.recv_ready():
                data += self.channel.recv(2048)
            time.sleep(.1)
        if '(y or n)' in data or '(y or [n])' in data.strip().split('\n')[-1]:
            self.channel.send('y\n')
            return '\n'.join(data.split('\n')[1:-1]) + self.__wait_gdb__()
        else:
            return '\n'.join(data.split('\n')[1:-1]).strip()

    def close(self):
        self.ssh.close()

    def send(self, command):
        if self.debugger == 'lldb':
            if command[0] == 'break':
                command[0] = 'b'
            elif command[0] == 'run':
                command[0] = 'r'
            elif command[0] == 'attach' and re.match('^\d+$', command[1]):
                command[0] = 'attach -p'
            elif command[0] in ['nexti', 'stepi']:
                command[0] = command[0][0] + command[0][-1]
            elif command[0] == 'return':
                command[0] = 'thread return'
            elif command[0] == 'info' and command[1] == 'break':
                command[0] = 'br'
                command[1] = 'l'
            elif command[0] == 'info' and command[1] == 'registers':
                command[0] = 'register'
                command[1] = 'read'
            elif command[0] == 'delete':
                command[0] = 'br del'
            elif command[0] == 'watch':
                command[0] = 'watchpoint set variable'
            elif command[0] == 'x':
                command[0] = 'memory read'
                command[1] = '`%s`' % command[1]
            elif command[0] == 'disassemble':
                command[0] = 'disassemble --frame'
            elif command[0] == 'inspect':
                command[0] = 'p'
        self.channel.send('%s\n' % ' '.join(command).strip())
        return self.__wait_gdb__()

    def line(self, command):
        data = self.send(command)

        ending_data = data.replace('\r', '').split('\n\n')[-1].strip()
        print data

        changed_files = re.findall('([a-zA-Z0-9_:]+) \([^\)]*\) at ([^:]+):(\d+)', data)
        if not changed_files and ending_data:
            changed_files = re.findall('([a-zA-Z0-9_:]+) \(.*\) at ([^:]+):(\d+)', ending_data)
        in_file = re.findall('(\d+)[ \t]+in[ \t]+([^:]+)', data)
        if not in_file and ending_data:
            re.findall('(\d+)[ \t]+in[ \t]+([^:]+)', ending_data)
        anything_else = list(set(re.findall('([\w\-\.]+):(\d+)[\n\r]?', data + '\n')))
        if in_file:
            try:
                self.location = os.path.basename(in_file[-1][1]).strip()
                return (self.location, in_file[-1][0], in_file[-1][1], None)
            except:
                pass
        elif changed_files:
            try:
                self.location = os.path.basename(changed_files[-1][1]).strip()
                return (self.location, changed_files[-1][2], changed_files[-1][1], changed_files[-1][0])
            except:
                pass
        elif anything_else and len(anything_else) == 1:
            self.location = os.path.basename(anything_else[0][0]).strip()
            return (self.location, anything_else[0][1], anything_else[0][0], None)
        else:
            try:
                line_num = re.findall('^(\d+)[ \t]+.+', data.strip().split('\n')[-1])[-1]
                return (self.location, line_num, '/tmp/null', None)
            except:
                pass
        return (None, None, None, None)

def find_all(name, path, method, tags_file):
    result = []
    for root, dirs, files in os.walk(path, followlinks=True):
        if name in files:
            result.append(os.path.join(root, name))
    if len(result) == 0:
        return None
    elif len(result) == 1:
        return result[0]
    elif method and tags_file:
        matches = []
        for line in open(tags_file, 'r'):
            if line[:line.find(' ')] == method:
                matches.append(line)
        files = []
        for line in matches:
            if '/^' in line:
                files.append(os.path.join(path, line.split('/^')[0].split()[1].strip()))
            else:
                files.append(os.path.join(path, line[:line[:line.index(';')].rfind(' ')].split()[1].strip()))
        result2 = filter(lambda x: x in result, files)
        if len(result2) == 0:
            return select_file(result)
        elif len(result2) == 1:
            return result2[0]
        else:
            return select_file(result2)
    else:
        return select_file(result)

def select_file(result):
    print
    for i in range(0, len(result)):
        print '\t%d:\t%s' % (i, result[i])
    selection = -1
    while selection < 0 or selection > len(result):
        try:
            selection = int(raw_input('Ambiguous file reference, select the correct filename: '))
        except:
            pass
    return result[int(selection)]

ethernet = None
def tcpdump_start(ssh, port):
    global ethernet
    if not ethernet:
        ethers = list(set(ssh.exec_command('netstat -i | cut -d\  -f1 | egrep -v "(Kernel|Iface|Name|lo)"')[1].read().strip().split('\n')))
        if len(ethers) == 1:
            ethernet = ethers[0]
        else:
            for i in range(0, len(ethers)):
                print '\t%d:\t%s' % (i, ethers[i])
            selection = -1
            while selection < 0 or selection > len(ethers):
                try:
                    selection = int(raw_input('Monitor traffic on which ethernet controller? '))
                except:
                    pass
            ethernet = ethers[selection]
    pid = None
    if port:
        pid = ssh.exec_command('echo $$; exec tcpdump -i %s -s0 -w /tmp/tcpdump_debug.out port %s' % (ethernet, port))[1].readline().strip()
    else:
        pid = ssh.exec_command('echo $$; exec tcpdump -i %s -s0 -w /tmp/tcpdump_debug.out' % ethernet)[1].readline().strip()
    time.sleep(2) # give tcpdump a couple seconds to get started
    return pid

def tcpdump_load(ssh, pid):
    time.sleep(1) # give tcpdump time to collect packets
    ssh.exec_command('kill %s' % pid)
    sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
    try:
        sftp.get(remotepath='/tmp/tcpdump_debug.out', localpath='/tmp/tcpdump_debug.out')
        if os.system('which wireshark  >/dev/null') == 0:
            os.system('wireshark /tmp/tcpdump_debug.out &')
    except IOError:
        pass
    sftp.close()

def debugger(con):
    settings = None
    settings_dir = os.path.join(os.path.expanduser('~'), '.config/rgdb/')
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
    settings_path = os.path.join(settings_dir, 'rgdb_settings')
    if not os.path.exists(settings_path):
        settings = {}
        while not 'code_path' in settings.keys() or not settings['code_path']:
            settings['code_path'] = raw_input('Enter a base path for your code directory: ')
        settings['tags_file'] = raw_input('Enter a tag file path (optional): ')
        settings['reverse'] = True if raw_input('Enable reverse debugging (true/false)? ').lower() == 'true' else False
        pickle.dump(settings, open(settings_path, 'w'))
    else:
        settings = pickle.load(open(settings_path, 'r'))

    debug_id = random.randint(5000, 6000)
    rc = None
    ui = os.path.join(os.path.dirname(sys.argv[0]), 'rgdb_ui')
    if not os.path.exists(ui):
        ui = 'python %s' % os.path.join(os.path.dirname(sys.argv[0]), 'rgdb_ui.py')
    if os.system('which gnome-terminal >/dev/null') == 0:
        rc = os.system('gnome-terminal --title="Remote GDB %s (Editor)" -x %s %d 2>/dev/null' % (con.binary, ui, debug_id))
    else:
        rc = os.system('xterm -T "Remote GDB %s (Editor)" -bg white -fg black -fn 9x15 -e %s %d 2>/dev/null &' % (con.binary, ui, debug_id))
    if rc != 0:
        exit(rc)
    code_path = settings['code_path']
    print 'Debugging %s on %s' % (con.binary, con.host)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://127.0.0.1:%d" % debug_id)
    con.socket = socket
    filename = None
    full_specified_name = None
    recent_files = {}
    line_num = None
    previous = None
    method = None
    while True:
        try:
            command = raw_input('(rgdb) ').strip().split()
            if not command:
                command = previous
            if not command:
                continue
            if command[0] in ['next', 'step', 'continue', 'finish'] or 'reverse' in command[0]:
                if len(command) > 1 and command[1] == 'tcpdump':
                    port = None
                    if len(command) > 2:
                        port = command[2]
                    tcpdump_pid = tcpdump_start(con.ssh, port)
                    filename, line_num, full_specified_name, method = con.line([command[0]])
                    tcpdump_load(con.ssh, tcpdump_pid)
                else:
                    filename, line_num, full_specified_name, method = con.line(command)
            elif command[0] == 'run':
                filename, line_num, full_specified_name, method = con.line(command)
                if settings['reverse']:
                    con.send('target record-full')
            elif command[0] == 'exit':
                break
            else:
                print con.send(command)
            if filename and line_num:
                if filename in recent_files.keys():
                    full_path = recent_files[filename]
                else:
                    full_path = find_all(filename, code_path, method, settings['tags_file'])
                    recent_files[filename] = full_path
                if full_path:
                    socket.send("%s:%s" % (full_path, line_num))
                    socket.recv()
            previous = command
        except EOFError:
            con.EOF()
            print
            break
    socket.send('exit')
    socket.recv()
    con.close()
    socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print '\n\t%s {machine} [gdb args...]\n' % sys.argv[0]
        print '\t\tYou\'ll be prompted on first run for a code path and tag file. The code path is'
        print '\twhere rgdb searches for source code files when it encounters a filename in gdb output.'
        print '\tFor example, ~/code could be the base directory where you store all your source files.'
        print '\t\tThe tag file property refers to your ctags file. Having a ctags file improves the'
        print '\tspeed and accuracy of file searches, but is not required.\n'
        exit(1)
    machine = sys.argv[1]
    gdb_args = sys.argv[2:]
    con = gdb(gdb_args, machine)
    debugger(con)

