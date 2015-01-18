#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import fiapProto
import argparse
import ssl

debug = 0

class fiapHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        #
        # XXX
        # which one should be used here, self.connection or self.request ?
        #
        client_cert = self.request.getpeercert()
        if debug > 2:
            print 'DEBUG: client_cert=', client_cert
        if not client_cert:
            raise CertificateValidationError(repr(server_cert))
        if debug > 0:
            for i in client_cert['subjectAltName']:
                print 'DEBUG: SAN=', i

    def _log_initmsg(self):
        if self.headers.has_key('Content-Type') == True:
            self.ctype = self.headers['Content-Type']
        else:
            self.ctype = 'text/xml' # default content-type to be parsed.
        m = 'client=%s[%d] ' % self.client_address
        m += 'path=[%s] ' % self.path
        m += 'ctype=[%s]' % self.ctype
        self.log_message(m)

    def do_POST(self):
        self._log_initmsg()
        fiap = fiapProto.fiapProto(requester_address=self.client_address, strict_check=True, debug=debug)
        clen = int(self.headers['Content-Length'])
        s = self.rfile.read(clen)
        # XXX should implement timeout() if clen is more than the actual length.
        #post_data = urlparse.parse_qs(s.rfile.read(length).decode('utf-8'))
        doc = None
        if debug > 0:
            self.log_message('DEBUG: post body=%s' % s.replace('\n',''))
        if self.ctype.find('text/xml') != -1: # XXX should it compare with 0 ?
            doc = fiap.serverParseXML(s)
        elif self.ctype.find('text/json') != -1:
            doc = fiap.serverParseJSON(s)
        else:
            msg = 'invalid content-type (%s) is specified.' % self.ctype
            self.log_message('ERROR: %s' % msg)
            self.send_error(403, msg)
            return
        if doc == None:
            self.log_message('ERROR: %s' % fiap.getemsg())
            self.send_error(403, fiap.getemsg())
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(doc)
        self.wfile.write('\n')
        if debug > 0:
            self.log_message('DEBUG: reply body=%s' % doc)
        return

    def do_GET(self):
        self._log_initmsg()
        if self.path != '/wsdl':
            self._logConnMsg()
            msg = '/wsdl is only allowed to GET, but for %s' % self.path
            self.log_message('ERROR: %s' % msg)
            self.send_error(403, msg)
            return
        # send WSDL
        self.send_response(200)
        self.end_headers()
        fiap = fiapProto.fiapProto(strict_check=True, debug=debug)
        self.wfile.write(fiap.getwsdl())
        self.wfile.write('\n')
        return

    def do_PUT(self):
        self._log_initmsg()
        msg = 'POST is not allowed.'
        self.log_message(msg)
        self.send_error(405, msg)
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def runs(port):
    server = None
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(
                certfile='cert/comp001-signedcert.pem',
                keyfile='cert/comp001-privkey.pem')
        context.load_verify_locations(cafile='cert/testCA-cert.pem')
        context.load_default_certs(purpose=ssl.Purpose.CLIENT_AUTH)
        context.verify_mode = ssl.CERT_REQUIRED
        #context.set_ciphers(ciphers)
        server = ThreadedHTTPServer(('', int(port)), fiapHandler)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
    except Exception as e:
        print 'ERROR: ', e.message, str(type(e))
    finally:
        print 'cleaning'
        if server != None:
            server.socket.close()

def run(port):
    server = None
    try:
        server = ThreadedHTTPServer(('', int(port)), fiapHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
    except Exception as e:
        print 'ERROR: ', e.message, str(type(e))
    finally:
        print 'cleaning'
        if server != None:
            server.socket.close()

#
# fiapy.py -d
#
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-p', action='store', dest='port', default=None,
        help='specify the port number for this server.')
    p.add_argument('-s', action='store_true', dest='secure', default=False,
        help='specify to use TLS connection.')
    p.add_argument('-c', action='store', dest='secure', default=False,
        help='specify to use TLS connection.')
    p.add_argument('-d', action='store', dest='debug', default=0,
        help='specify the debug level.')
    opt = p.parse_args()
    return opt

#
# main
#
opt = parse_args()
debug = opt.debug
#
# set the runner and default port if needed.
#
if opt.secure == True:
    opt.run = runs
    if opt.port == None:
        opt.port = 18883
else:
    opt.run = run
    if opt.port == None:
        opt.port = 18880

opt.run(port=opt.port)
