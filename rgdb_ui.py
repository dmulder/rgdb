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

import sys, os, os.path, zmq, threading, gtk
from gtksourceview2 import View as SourceView, LanguageManager, Buffer as SourceBuffer

class DebugWindow:
    def __init__(self):
        self.win = gtk.Window()
        self.scrolled = gtk.ScrolledWindow()
        self.win.set_default_size(900, 900)
        self.tb = SourceView()
        self.win.add(self.scrolled)
        self.scrolled.add(self.tb)
        self.win.connect('destroy', gtk.main_quit)
        self.win.show_all()

    def close(self):
        self.win.destroy()

    def open_file(self, filename, line_num):
        print 'called to open file %s at line %s' % (filename, line_num)
        lm = LanguageManager()
        buf = SourceBuffer()
        buf.set_data('languages-manager', lm)
        if os.path.isabs(filename):
            path = filename
        else:
            path = os.path.abspath(filename)
        lang = lm.guess_language(filename)
        if lang:
            buf.set_highlight_syntax(True)
            buf.set_language(language)
        else:
            buf.set_highlight_syntax(False)
        buf.begin_not_undoable_action()
        txt = open(path).read()
        buf.set_text(txt)
        buf.set_data('filename', path)
        buf.end_not_undoable_action()

        buf.set_modified(False)
        buf.place_cursor(buffer.get_start_iter())

if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://127.0.0.1:%s" % sys.argv[1])
    filename = ''
    previous_file = ''
    line_num = None

    dbw = DebugWindow()
    t = threading.Thread(target=gtk.main)
    t.start()

    while True:
        mesg = socket.recv()
        socket.send(mesg)
        if mesg == 'exit':
            dbw.close()
            break
        if mesg:
            filename, line_num = mesg.split(':')
            dbw.open_file(filename, line_num)
            previous_file = filename

    socket.close()

