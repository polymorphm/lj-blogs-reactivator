# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2012, 2015 Andrej Antonov <polymorphm@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

assert str is not bytes

import os, os.path, threading

DEFAULT_EXT = 'txt'

def normalize_ext(txt_file, ext=None):
    if not txt_file:
        return
    
    if ext is None:
        ext = DEFAULT_EXT
    
    if txt_file.endswith('.{}'.format(ext)):
        return txt_file
    
    return '{}.{}'.format(txt_file, ext)

def change_ext(txt_file, new_ext):
    if not txt_file:
        return
    
    return '{}.{}'.format(txt_file.rsplit('.', 1)[0], new_ext)

def rename_to_last(path):
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    prefix = 0
    
    while True:
        prefix += 1
        new_basename = 'last-{}.{}'.format(prefix, basename)
        new_path = os.path.join(dirname, new_basename)
        
        if os.path.exists(new_path):
            continue
        
        try:
            os.rename(path, new_path)
            
            return
        except OSError:
            if os.path.exists(new_path):
                continue
            
            raise

def create_file(path):
    tempnam = os.path.join(
            os.path.dirname(path),
            'new.{}'.format(os.path.basename(path)),
            )
    
    while True:
        if os.path.exists(path):
            rename_to_last(path)
        
        try:
            open(tempnam, 'wb').close()
            os.rename(tempnam, path)
            
            break
        except OSError:
            if os.path.exists(path):
                continue
            
            raise
    
    return open(path, 'w', encoding='utf-8', newline='\n')

class OutMgr(object):
    def __init__(self, out_file=None, ext=None):
        self._lock = threading.RLock()
        
        if ext is not None:
            self._ext = ext
        else:
            self._ext = DEFAULT_EXT
        self._out_file = normalize_ext(out_file, self._ext)
        self._fd_map = {}
    
    def get_fd_and_lock(self, ext=None):
        # this function is thread-safe
        
        lock = self._lock
        
        if ext is None:
            ext = self._ext
        
        out_file = self._out_file
        
        if out_file is None:
            return None, lock
        
        with lock:
            if ext != self._ext:
                out_file = change_ext(out_file, ext)
            
            if ext in self._fd_map:
                return self._fd_map[ext], lock
            
            self._fd_map[ext] = fd = create_file(out_file)
            
            return fd, lock
    
    def write(self, text, ext=None, end=None):
        # this function is thread-safe
        
        if end is None:
            end = '\n'
        
        fd, lock = self.get_fd_and_lock(ext=ext)
        
        if fd is None:
            return
        
        with lock:    
            fd.write('{}{}'.format(text, end))
            fd.flush()
