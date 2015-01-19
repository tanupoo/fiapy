#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import argparse
import ssl
import fiapProto
import fiapConfig

cf = None

class fiapHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def _log_initmsg(self):
        if self.headers.has_key('Content-Type') == True:
            self.ctype = self.headers['Content-Type']
        else:
            self.ctype = 'text/xml' # default content-type to be parsed.
        m = 'client=%s[%d] ' % self.client_address
        m += 'path=[%s] ' % self.path
        m += 'ctype=[%s]' % self.ctype
        self.log_message(m)

    def _check_acl_san(self):
        #
        # XXX
        # which one should be used here, self.connection or self.request ?
        #
        if opt.secure and not isinstance(self.request, ssl.SSLSocket):
            return False
        print 'xxx', self.request.cipher()
        return cf.check_acl_san(self.request.getpeercert())

    def do_POST(self):
        self._log_initmsg()
        if opt.secure and self._check_acl_san() == False:
            self.send_error(401)
            return
        fiap = fiapProto.fiapProto(requester_address=self.client_address, strict_check=True, debug=cf.debug)
        clen = int(self.headers['Content-Length'])
        s = self.rfile.read(clen)
        # XXX should implement timeout() if clen is more than the actual length.
        #post_data = urlparse.parse_qs(s.rfile.read(length).decode('utf-8'))
        doc = None
        if cf.debug > 0:
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
        if cf.debug > 0:
            self.log_message('DEBUG: reply body=%s' % doc)
        return

    def do_GET(self):
        self._log_initmsg()
        if opt.secure and self._check_acl_san() == False:
            self.send_error(401)
            return
        if self.path != '/wsdl':
            self._logConnMsg()
            msg = '/wsdl is only allowed to GET, but for %s' % self.path
            self.log_message('ERROR: %s' % msg)
            self.send_error(403, msg)
            return
        # send WSDL
        self.send_response(200)
        self.end_headers()
        fiap = fiapProto.fiapProto(strict_check=True, debug=cf.debug)
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

def run(port=18880, config=None):
    server = None
    if not opt.secure:
        server = ThreadedHTTPServer(('', int(port)), fiapHandler)
    else:
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ctx.load_default_certs(purpose=ssl.Purpose.CLIENT_AUTH)
            #ctx.set_ciphers(ciphers)
            if config:
                if config.key_file and config.cert_file:
                    ctx.load_cert_chain(keyfile=config.key_file,
                            certfile=config.cert_file)
                ca_certs = config.ca_certs
                if ca_certs:
                    ctx.load_verify_locations(cafile=ca_certs)
                ctx.verify_mode = ssl.CERT_REQUIRED
            server = ThreadedHTTPServer(('', int(port)), fiapHandler)
            if config.cert_request:
                server.socket = ctx.wrap_socket(server.socket, server_side=True)
        except Exception as e:
            print 'ERROR: ', e.message, str(type(e))
            if server != None:
                server.socket.close()
            exit(1)

    #
    # start the server
    #
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
    except Exception as e:
        print 'ERROR: ', e.message, str(type(e))
    finally:
        print 'cleaning'
        server.socket.close()

#
# parser
#
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-p', action='store', dest='port', default=None,
        help='specify the port number for this server.')
    p.add_argument('-s', action='store_true', dest='secure', default=False,
        help='specify to use TLS connection.')
    p.add_argument('-c', action='store', dest='cfile', default=False,
        help='specify the file name of the configuration.')
    p.add_argument('-d', action='store', dest='debug', default=0,
        help='specify the debug level.')
    opt = p.parse_args()
    return opt

#
# main
#
opt = parse_args()
cf = fiapConfig.fiapConfig(opt.cfile, secure=opt.secure, debug=opt.debug)
#
# set the runner and default port if needed.
#
if opt.secure == True:
    if opt.port == None:
        opt.port = 18883
else:
    if opt.port == None:
        opt.port = 18880

run(port=opt.port, config=cf)
