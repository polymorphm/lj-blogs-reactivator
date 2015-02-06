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

import time
import re
from urllib import parse as url_parse
from urllib import request as url_request
from http import cookiejar
import socket
import imaplib
from email import parser as email_parser

try:
    from lib_socks_proxy_2013_10_03 import socks_proxy_context
except ImportError as e:
    socks_proxy_context = None
    socks_proxy_context_import_error = e

LJ_HTTPS_URL = 'https://www.livejournal.com'
LJ_HTTP_URL = 'http://www.livejournal.com'

REQUEST_TIMEOUT = 60.0
REQUEST_READ_LIMIT = 10000000

class LjReactivatorError(Exception):
    pass

class EmailError(LjReactivatorError):
    pass

class AuthLjError(LjReactivatorError):
    pass

class SendValidLjError(LjReactivatorError):
    pass

class ConfirmLjError(LjReactivatorError):
    pass

class LjReactivatorCtx:
    pass

class SafeIMAP4(imaplib.IMAP4):
    def _create_socket(self):
        sock = socket.create_connection(
                (self.host, self.port),
                timeout=15.0,
                )
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        return sock

def mail_fetch(email, imap_host, email_login, email_pass):
    try:
        imap = SafeIMAP4(host=imap_host)
        imap.starttls()
        imap.login(email_login, email_pass)
        try:
            imap.select()
            typ, search_data = imap.search(None, 'UNSEEN')
            
            for num in reversed(search_data[0].split()):
                typ, fetch_data = imap.fetch(num, '(RFC822)')
                
                msg_parser = email_parser.BytesFeedParser()
                msg_parser.feed(fetch_data[0][1])
                msg = msg_parser.close()
                
                msg_from = msg.get_all('from')
                msg_to = msg.get_all('to')
                msg_subject = msg.get_all('subject')
                
                if not msg_from or tuple(msg_from) != ('do-not-reply@livejournal.com',) or \
                        not msg_to or tuple(msg_to) != (email,) or \
                        not msg_subject or tuple(msg_subject) != ('Validate Email',):
                    continue
                
                for msg_part in msg.walk():
                    if msg.get_content_type() == 'text/plain':
                        payload = msg.get_payload(decode=True)
                        
                        assert isinstance(payload, bytes)
                        
                        msg_text = payload.decode(errors='replace')
                        
                        return msg_text
        finally:
            imap.close()
            imap.logout()
    except imaplib.IMAP4.error as imap_error:
        error_str = 'email is {!r}, error is {!r}'.format(
                email,
                imap_error,
                )
        raise imaplib.IMAP4.error(error_str)

def login_phase(lj_reac_ctx):
    opener = lj_reac_ctx.opener
    open_func = lj_reac_ctx.open_func
    ua_name = lj_reac_ctx.ua_name
    username = lj_reac_ctx.lj_username
    password = lj_reac_ctx.lj_pass
    
    lj_login_url = url_parse.urljoin(LJ_HTTPS_URL, 'login.bml?ret=1')
    lj_update_url = url_parse.urljoin(LJ_HTTP_URL, 'update.bml')
    
    resp = open_func(
            opener,
            url_request.Request(
                    lj_login_url,
                    data=url_parse.urlencode({
                            'user': username,
                            'remember_me': '1',
                            'ref': lj_update_url,
                            'password': password,
                            'action:login': 'Log in',
                            }).encode(),
                    headers={
                            'User-Agent': ua_name,
                            'Referer': lj_login_url,
                            },
                    ),
            timeout=REQUEST_TIMEOUT,
            )
    
    if resp.getcode() != 200 or resp.geturl() != lj_update_url:
        raise AuthLjError('lj auth error')

def send_valid_phase(lj_reac_ctx):
    opener = lj_reac_ctx.opener
    open_func = lj_reac_ctx.open_func
    ua_name = lj_reac_ctx.ua_name
    username = lj_reac_ctx.lj_username
    
    lj_update_url = url_parse.urljoin(LJ_HTTP_URL, 'update.bml')
    lj_register_url = url_parse.urljoin(LJ_HTTP_URL, 'register.bml')
    
    resp = open_func(
            opener,
            url_request.Request(
                    lj_register_url,
                    data=url_parse.urlencode({
                            'authas': username,
                            'action:send': 'Send Validation Email',
                            }).encode(),
                    headers={
                            'User-Agent': ua_name,
                            'Referer': lj_update_url,
                            },
                    ),
            timeout=REQUEST_TIMEOUT,
            )
    
    if resp.getcode() != 200 or resp.geturl() != lj_register_url:
        raise SendValidLjError('lj send validation error')

def mail_phase(lj_reac_ctx):
    ua_name = lj_reac_ctx.ua_name
    email = lj_reac_ctx.email
    email_pass = lj_reac_ctx.email_pass
    
    mail_ru_imap_host = 'imap.mail.ru'
    
    if email.endswith('@mail.ru') or \
            email.endswith('@inbox.ru') or \
            email.endswith('@list.ru') or \
            email.endswith('@bk.ru'):
        email_login = email
        imap_host = mail_ru_imap_host
    else:
        raise EmailError('unknown email service')
    
    if imap_host == mail_ru_imap_host:
        mail_web_url = 'https://auth.mail.ru/cgi-bin/auth?from=splash'
        mail_web_url_referer = 'https://auth.mail.ru/'
        
        email_splt_left, email_splt_right = email.rsplit('@', 1)
        
        mail_cookies = cookiejar.CookieJar()
        mail_opener = url_request.build_opener(
                url_request.HTTPCookieProcessor(cookiejar=mail_cookies),
                )
        
        resp = mail_opener.open(
                url_request.Request(
                        mail_web_url,
                        data=url_parse.urlencode({
                                'Domain': email_splt_right,
                                'Login': email_splt_left,
                                'Password': email_pass,
                                'new_auth_form': '1',
                                }).encode(),
                        headers={
                                'User-Agent': ua_name,
                                'Referer': mail_web_url_referer,
                                },
                        ),
                timeout=REQUEST_TIMEOUT,
                )
        
        if resp.getcode() != 200 or resp.geturl() != mail_web_url:
            raise EmailError('mail web ui error')
    
    for att_i in range(10):
        time.sleep(10)
        
        mail_text = mail_fetch(email, imap_host, email_login, email_pass)
        
        if mail_text is None:
            continue
        
        assert isinstance(mail_text, str)
        
        confirm_url_prefix = 'http://www.livejournal.com/confirm/'
        confirm_url_match = re.search(
                r'\s(?P<confirm_url>' + re.escape(confirm_url_prefix) + r'\S+)\s',
                mail_text,
                flags=re.S,
                )
        
        if confirm_url_match is None:
            continue
        
        confirm_url = confirm_url_match.group('confirm_url')
        
        break
    else:
        raise EmailError(
                'confirm_url not received',
                )
    
    lj_reac_ctx.confirm_url = confirm_url

def confirm_phase(lj_reac_ctx):
    opener = lj_reac_ctx.opener
    open_func = lj_reac_ctx.open_func
    ua_name = lj_reac_ctx.ua_name
    confirm_url = lj_reac_ctx.confirm_url
    
    lj_register_url = url_parse.urljoin(LJ_HTTP_URL, 'register.bml')
    
    resp = open_func(
            opener,
            url_request.Request(
                    confirm_url,
                    headers={
                            'User-Agent': ua_name,
                            },
                    ),
            timeout=REQUEST_TIMEOUT,
            )
    
    if resp.getcode() != 200 or \
            not resp.geturl().startswith('{}?'.format(lj_register_url)):
        raise ConfirmLjError('lj confirm error')

def blocking_lj_reactivator(
        email=None,
        email_pass=None,
        lj_username=None,
        lj_pass=None,
        ua_name=None,
        proxy_address=None,
        ):
    assert email is not None
    assert email_pass is not None
    assert lj_username is not None
    assert lj_pass is not None
    assert ua_name is not None
    assert proxy_address is None or isinstance(proxy_address, (tuple, list))
    
    if proxy_address is not None:
        # open via proxy
        
        if socks_proxy_context is None:
            raise socks_proxy_context_import_error
        
        def open_func(opener, *args, **kwargs):
            with socks_proxy_context.socks_proxy_context(proxy_address=proxy_address):
                return opener.open(*args, **kwargs)
    else:
        # default open action
        
        def open_func(opener, *args, **kwargs):
            return opener.open(*args, **kwargs)
    
    cookies = cookiejar.CookieJar()
    opener = url_request.build_opener(
            url_request.HTTPCookieProcessor(cookiejar=cookies),
            )
    
    lj_reac_ctx = LjReactivatorCtx()
    lj_reac_ctx.email = email
    lj_reac_ctx.email_pass = email_pass
    lj_reac_ctx.lj_username = lj_username
    lj_reac_ctx.lj_pass = lj_pass
    lj_reac_ctx.ua_name = ua_name
    lj_reac_ctx.proxy_address = proxy_address
    lj_reac_ctx.open_func = open_func
    lj_reac_ctx.opener = opener
    
    login_phase(lj_reac_ctx)
    send_valid_phase(lj_reac_ctx)
    confirm_url = mail_phase(lj_reac_ctx)
    confirm_phase(lj_reac_ctx)
