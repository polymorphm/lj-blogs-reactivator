# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2015 Andrej Antonov <polymorphm@gmail.com> 
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

import argparse
import random
import threading
import itertools
import csv
from . import out_mgr
from . import safe_run
from . import get_useragent
from . import reactivator

class ArgumentError(Exception):
    pass

class Task:
    pass

def main():
    parser = argparse.ArgumentParser(
            description='utility for reactivation (via email) of bad '
                    'LJ-blog accounts',
            )
    
    parser.add_argument(
            '--proxy',
            metavar='PROXY-ADDRESS',
            help='address of SOCKS5-proxy',
            )
    
    parser.add_argument(
            'in_path',
            metavar='IN-PATH',
            help='path to in csv-file of accounts',
            )
    
    parser.add_argument(
            'out_path',
            metavar='GOOD-CSV-PATH',
            help='path to out files',
            )
    
    parser.add_argument(
            'thread_count',
            metavar='THREAD-COUNT',
            type=int,
            help='count of threads',
            )
    
    args = parser.parse_args()
    
    proxy_address_str = args.proxy
    in_csv_path = args.in_path
    out_path = args.out_path
    thread_count = args.thread_count
    
    if proxy_address_str is not None:
        if ':' not in proxy_address_str:
            raise ArgumentError('invalid proxy argument')
        
        proxy_address = proxy_address_str.rsplit(sep=':', maxsplit=1)
    else:
        proxy_address = None
    
    ui_lock = threading.RLock()
    out = out_mgr.OutMgr(out_path)
    
    out.get_fd_and_lock(ext='out.log')
    out.get_fd_and_lock(ext='err.log')
    out.get_fd_and_lock(ext='err-tb.log')
    good_fd, good_fd_lock = out.get_fd_and_lock(ext='good.csv')
    bad_fd, bad_fd_lock = out.get_fd_and_lock(ext='bad.csv')
    
    in_csv_reader = csv.reader(open(in_csv_path, 'r', encoding='utf-8', errors='replace'))
    good_csv_writer = csv.writer(good_fd)
    bad_csv_writer = csv.writer(bad_fd)
    
    def begin_handler(task):
        with ui_lock:
            print_str = '[task_{}] {}: begin'.format(task.task_i, task.lj_username)
            out.write(print_str, ext='out.log')
            print(print_str)
    
    def done_handler(task):
        with ui_lock:
            if task.error is None:
                with good_fd_lock:
                    good_csv_writer.writerow((task.email, task.email_pass, task.lj_username, task.lj_pass))
                    good_fd.flush()
                
                print_str = '[task_{}] {}: done'.format(task.task_i, task.lj_username)
                out.write(print_str, ext='out.log')
                print(print_str)
            else:
                error_type, error_str, error_tb = task.error
                
                with bad_fd_lock:
                    bad_csv_writer.writerow((task.email, task.email_pass, task.lj_username, task.lj_pass))
                    bad_fd.flush()
                
                print_str = '[task_{}] {}: error: {!r} {!r}'.format(
                        task.task_i, task.lj_username, error_type, error_str
                        )
                out.write(print_str, ext='out.log')
                out.write(print_str, ext='err.log')
                out.write('{}\n\n{}\n\n'.format(print_str, error_tb), ext='err-tb.log')
                print(print_str)
    
    task_counter = itertools.count()
    
    def new_task_iter():
        for row in in_csv_reader:
            if len(row) != 4:
                continue
            
            task = Task()
            task.task_i = next(task_counter)
            task.email, task.email_pass, task.lj_username, task.lj_pass = row
            
            yield task
    
    task_iter = new_task_iter()
    task_iter_lock = threading.RLock()
    useragent_list = get_useragent.get_useragent_list()
    
    print_str = 'user agent string list: {}'.format(
            ', '.join(repr(s) for s in  useragent_list),
            )
    out.write(print_str, ext='out.log')
    print(print_str)
    
    def thread_func():
        while True:
            with task_iter_lock:
                try:
                    task = next(task_iter)
                except StopIteration:
                    break
            
            begin_handler(task)
            
            result, error = safe_run.three_safe_run(
                    reactivator.blocking_lj_reactivator,
                    email=task.email,
                    email_pass=task.email_pass,
                    lj_username=task.lj_username,
                    lj_pass=task.lj_pass,
                    ua_name=random.choice(useragent_list),
                    proxy_address=proxy_address,
                    )
            
            task.result, task.error = result, error
            
            done_handler(task)
    
    thread_list = list(threading.Thread(target=thread_func)
            for thread_i in range(thread_count))
    
    for thread in thread_list:
        thread.start()
    
    for thread in thread_list:
        thread.join()
    
    print_str = 'done!'
    out.write(print_str, ext='out.log')
    print(print_str)
