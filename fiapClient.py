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
import fiapTools

class CertificateValidationError(httplib2.HttpLib2Error):
    pass

def validating_server_factory(ca_args):
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

            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            key_file = ca_args.get('key_file')
            cert_file = ca_args.get('cert_file')
            if key_file and cert_file:
                context.load_cert_chain(keyfile=key_file, certfile=cert_file)
            ca_certs = ca_args.get('ca_certs')
            if ca_certs:
                context.load_verify_locations(cafile=ca_certs)
            context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
            context.verify_mode = ssl.CERT_REQUIRED

            try:
                self.sock = context.wrap_socket(sock)
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
                if debug > 2:
                    print 'DEBUG:server cert=:', server_cert
                if not server_cert:
                    raise CertificateValidationError(repr(server_cert))
            for i in server_cert['subjectAltName']:
                print 'DEBUG:SAN=', i

        def getresponse(self):
            if not self._exc_info:
                return httplib2.HTTPSConnectionWithTimeout.getresponse(self)
            else:
                raise self._exc_info[1], None, self._exc_info[2]
    return ValidatingHTTPSConnection

def postrequest(url, body=None, ctype='text/xml; charset=utf-8', ca_args={}):
    #
    # set headers
    #
    headers = {}
    headers['Content-Type'] = ctype
    headers['Accept'] = ctype
    headers['Content-Length'] = '%s' % len(body)
    #
    # set http_args
    #
    http_args = {}        
    if url.startswith('https://') and len(ca_args) > 0:
        http_args['connection_type'] = validating_server_factory(ca_args)
    #
    # start the http connection
    #
    http = httplib2.Http(timeout=10)
    try:
        res_headers, res_body = http.request(url, method='POST',
                body=body, headers=headers, **http_args)
    except Exception as e:
        print e, str(type(e))
        exit(1)
    print 'HTTP: %s %s' % (res_headers.status, res_headers.reason)
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
        help='specify the file name for the configuration including security.')
    p.add_argument('-x', action='store_true', dest='req_to_xml', default=False,
        help='specify to send an XML request.')
    p.add_argument('-X', action='store_true', dest='res_to_xml', default=False,
        help='specify to output an XML response.')
    p.add_argument('-w', action='store', dest='wsdl', default=None,
        help='specify the wsdl.')
    p.add_argument('-d', action='store', dest='debug', default=0,
        help='specify the debug level.')
    return p.parse_args()

#
# main
#
if __name__ == '__main__' :
    opt = parse_args()
    debug = opt.debug
    url, host = set_default_port(opt.url)
    if debug > 0:
        print 'connect to', host

    #soapGetAddressLocation(opt.wsdl)

    if opt.bfile != None:
        fp = open(opt.bfile)
    else:
        fp = sys.stdin
    src = fp.read()
    if src == None:
        print 'ERROR: src document is nothing'
        exit(1)

    fiap = fiapProto.fiapProto(debug=debug)

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

    #
    # parse the configuration file if specified.
    #
    ca_args = fiapTools.parse_config_file(opt.cfile)
    #
    # send the request and get a response.
    #
    res = postrequest(url, body=req_doc, ctype=ctype, ca_args=ca_args)
    if res == None:
        print 'ERROR(FIAP): ' + fiap.emsg
        exit(1)
    if debug > 0:
        print 'Response:', res

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
