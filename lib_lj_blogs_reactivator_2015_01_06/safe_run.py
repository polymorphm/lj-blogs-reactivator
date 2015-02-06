# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2014, 2015 Andrej Antonov <polymorphm@gmail.com>
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

import threading
import traceback
import time

THREE_SAFE_RUN_DELAY = 10.0

def safe_run(unsafe_func, *args, **kwargs):
    safe_run_ctx = {
            'result': None,
            'error': None,
            }
    
    def safe_run_thread_func():
        try:
            safe_run_ctx['result'] = unsafe_func(*args, **kwargs)
        except Exception as err:
            safe_run_ctx['error'] = type(err), str(err), traceback.format_exc()
    
    safe_run_thread = threading.Thread(target=safe_run_thread_func)
    safe_run_thread.start()
    safe_run_thread.join()
    
    # XXX   separate thread was used for avoid
    #       unexpected system errors from main thread
    
    return safe_run_ctx['result'], safe_run_ctx['error']

def three_safe_run(unsafe_func, *args, **kwargs):
    for try_i in range(3):
        result, error = safe_run(unsafe_func, *args, **kwargs)
        
        if error is None:
            return result, error
        
        time.sleep(THREE_SAFE_RUN_DELAY)
    
    return result, error