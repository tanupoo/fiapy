#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import sys
import re
import argparse
import socket
import json
import httplib2
import ssl
import fiapProto
import fiapConfig

FIAPC_TIMEOUT = 10

class CertificateValidationError(httplib2.HttpLib2Error):
    pass

def validating_server_factory(config):
    # we need to define a closure here because we don't control
    # the arguments this class is instantiated with
    class ValidatingHTTPSConnection(httplib2.HTTPSConnectionWithTimeout):

        def connect(self):
            # begin copypasta from HTTPSConnectionWithTimeout
            "Connect to a host on a given (SSL) port."

            if self.proxy_info and self.proxy_info.isgood():
                sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setproxy(*self.proxy_info.astuple())
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if self.timeout != 0:
                sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            # end copypasta

            if config.security_level == 2:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                ctx.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
            else:
                ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ctx.set_ciphers(config.ciphers)
            if config:
                if config.key_file and config.cert_file:
                    ctx.load_cert_chain(keyfile=config.key_file,
                            certfile=config.cert_file)
                ca_certs = config.ca_certs
                if ca_certs:
                    ctx.load_verify_locations(cafile=ca_certs)
                if config.cert_request:
                    ctx.verify_mode = ssl.CERT_REQUIRED
            try:
                self.sock = ctx.wrap_socket(sock)
            except ssl.SSLError:
                # we have to capture the exception here and raise later because 
                # httplib2 tries to ignore exceptions on connect
                import sys
                self._exc_info = sys.exc_info()
                raise
            else:
                self._exc_info = None

                # this might be redundant
                server_cert = self.sock.getpeercert()
                if opt.debug >= 2:
                    print 'DEBUG: server cert=:', server_cert
                if not server_cert:
                    raise CertificateValidationError(repr(server_cert))
            for i in server_cert['subjectAltName']:
                if opt.debug >= 2:
                    print 'DEBUG: SAN=', i

        def getresponse(self):
            if not self._exc_info:
                return httplib2.HTTPSConnectionWithTimeout.getresponse(self)
            else:
                raise self._exc_info[1], None, self._exc_info[2]
    return ValidatingHTTPSConnection

def postrequest(url, body=None, ctype='text/xml; charset=utf-8', config=None):
    #
    # set headers
    #
    headers = {}
    headers['Content-Type'] = ctype
    headers['Content-Length'] = str(len(body))
    #
    # set http_args
    #
    http_args = {}        
    if config.security_level:
        http_args['connection_type'] = validating_server_factory(config)
    #
    # start the http connection
    #
    http = httplib2.Http(timeout=FIAPC_TIMEOUT)
    try:
        res_headers, res_body = http.request(url, method='POST',
                body=body, headers=headers, **http_args)
    except Exception as e:
        print e, str(type(e))
        exit(1)
    if opt.debug >= 1:
        print 'DEBUG: HTTP: %s %s' % (res_headers.status, res_headers.reason)
    if opt.debug >= 2:
        print 'DEBUG: === BEGIN: response headers'
        for k, v in res_headers.iteritems():
            print 'DEBUG: %s: %s' % (k, v)
        print 'DEBUG: === END: response headers'
    return res_body

def soapGetAddressLocation(wsdl):
    service_port = None
    f = open(opt.wsdl)
    line = f.readlines()
    while line:
        r = re.search(r'<soap:address location="([^"]+)"', line)
        if r != None:
            service_port = r.group(1)
            break
        line = f.readlines()
    if service_port == None:
        return None
    (a, p) = service_port.split(':')
    return (a, p)

def set_default_port(url):
    (schema, dummy, host) = url.split('/', 2)
    path = ''
    if host.count('/') != 0:
        (host, path) = host.split('/', 1)
    if host.count(':') == 0:
        port = 18880
        if schema == 'https:':
            port = 18883
        return '%s//%s:%d/%s' % (schema, host, port, path), '%s:%s' % (host, port)
    return url, host

#
# parser
#
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-e', action='store', dest='url', default=None,
        required=True,
        help='specify the access point of the server in URL.')
    p.add_argument('-f', action='store', dest='bfile', default=None,
        help='specify the filename of the request.')
    p.add_argument('-c', action='store', dest='cfile', default=None,
        help='specify the configuration file name.')
    p.add_argument('-x', action='store_true', dest='req_to_xml', default=False,
        help='specify to send an XML request.')
    p.add_argument('-X', action='store_true', dest='res_to_xml', default=False,
        help='specify to output an XML response.')
    p.add_argument('-s', action='store', dest='sec_lv', default=None,
        help='specify the security level. 0, 1, or 2')
    p.add_argument('-w', action='store', dest='wsdl', default=None,
        help='specify the wsdl.')
    p.add_argument('-d', action='store', dest='debug', default=0,
        help='specify the debug level. 0, 1, or 2')
    return p.parse_args()

#
# main
#
opt = parse_args()
if opt.url.startswith('https://'):
    sec_lv = 1
sec_lv = opt.sec_lv
url, host = set_default_port(opt.url)

#soapGetAddressLocation(opt.wsdl)

if opt.debug:
    print 'DEBUG: reading request file.'
if opt.bfile != None:
    fp = open(opt.bfile)
else:
    fp = sys.stdin
src = fp.read()
if src == None:
    print 'ERROR: src document is nothing'
    exit(1)

fiap = fiapProto.fiapProto(debug=opt.debug)

#
# make a request
#
req_doc = ''
if opt.req_to_xml == True:
    ctype = 'text/xml; charset=utf-8'
    if re.match('^\<\?xml', src):
        req_doc = src
    else:
        req_doc = fiap.JSONtoXML(src)
else:
    ctype = 'text/json; charset=utf-8'
    if re.match('^\<\?xml', src) == None:
        req_doc = src
    else:
        req_doc = fiap.XMLtoJSON(src)
if req_doc == None:
    print 'ERROR: %s' % fiap.getemsg()
    exit(1)

if opt.debug >= 1:
    print 'DEBUG: Request:', req_doc

#
# parse the configuration file if specified.
#
cf = fiapConfig.fiapConfig(opt.cfile, security_level=sec_lv, debug=opt.debug)
#
# send the request and get a response.
#
if opt.debug >= 1:
    print 'DEBUG: connecting to', host
res = postrequest(url, body=req_doc, ctype=ctype, config=cf)
if res == None:
    print 'ERROR(FIAP): ' + fiap.emsg
    exit(1)
if opt.debug >= 1:
    print 'DEBUG: Response:', res

#
# print the response
#
if opt.res_to_xml == True:
    if re.match('^\<\?xml', res):
        res_doc = res
    else:
        res_doc = fiap.JSONtoXML(res)
else:
    if re.match('^\<\?xml', res):
        res_doc = fiap.XMLtoJSON(res)
    else:
        res_doc = res
    try:
        res_doc = json.dumps(json.loads(res_doc), indent=2)
    except ValueError as e:
        print 'ERROR: JSON parse error', e
        exit(1)
if req_doc == None:
    print 'ERROR: %s' % fiap.getemsg()
    exit(1)

print res_doc
