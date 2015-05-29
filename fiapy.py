#!/usr/bin/env python
# -*- coding: utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import argparse
import ssl
import fiapProto
import fiapConfig

FIAPY_TIMEOUT = 10

cf = None

# cf.debug
#   0: normal
#   1: verbose (mainly, ieee1888 level)
#   2: more verbose

class fiapHandler(BaseHTTPRequestHandler):

    check_content_length = False
    check_content_type = False

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    #
    # check content-length, content-type.
    # set the read timeout.
    #
    def _check_request(self):
        self.log_message('Connection from %s[%d] ' % self.client_address)
        if cf.debug >= 2:
            self.log_message('DEBUG: === Headers BEGIN:')
            for i in self.headers.items():
                self.log_message(i.__repr__())
            self.log_message('DEBUG: === Headers END')
        #
        # check the content-length
        #
        self.clen = -1
        if self.headers.getheader('Transfer-Encoding') == 'chunked':
            # XXX here possible DOS happen.
            self.clen = self.rfile.readline()
            self.clen = int(self.clen, 16)
        else:
            self.clen = self.headers.getheader('Content-Length', -1)
            self.clen = int(self.clen)
            if self.clen == -1 and self.check_content_length == True:
                self.log_message('ERROR: Content-Length does not exist')
                self.send_error(411)
                return False
        #
        # check the content-type
        #
        self.ctype = self.headers.getheader('Content-Type')
        if not self.ctype:
            if self.check_content_type == True:
                self.log_message('ERROR: Content-Type does not exist')
                self.send_error(400)
                return False
            self.ctype = 'text/html' # default content-type to be parsed.
            self.log_message('WARNING: Content-Type does not exist, set %s' % self.ctype)
        #
        self.log_message('%s %s [%s]' % (self.protocol_version, self.command, self.path))
        self.rfile._sock.settimeout(FIAPY_TIMEOUT)
        return True

    #
    # send 200 OK response
    #
    def _send_response(self, doc, ctype):
        #self.protocol_version = 'HTTP/1.1'
        doc += '\r\n'
        self.send_response(200)
        self.send_header('Content-Length', len(doc))
        self.send_header('Content-Type', ctype)
        self.end_headers()
        self.wfile.write(doc)
        if cf.debug >= 1:
            self.log_message('DEBUG: reply body=%s' % doc)

    def _check_acl_san(self):
        #
        # XXX
        # which one should be used here, self.connection or self.request ?
        #
        if opt.sec_lv and not isinstance(self.request, ssl.SSLSocket):
            return False
        return cf.check_acl_san(self.request.getpeercert())

    def do_POST(self):
        if self._check_request() == False:
            return
        if opt.sec_lv and self._check_acl_san() == False:
            self.send_error(401)
            return
        fiap = fiapProto.fiapProto(requester_address=self.client_address, strict_check=True, debug=cf.debug)
        if self.clen == -1 and False:
            #
            # XXX GUTP interop hack: accept in case of no content-length.
            #
            s = self.rfile.read()
        else:
            s = self.rfile.read(self.clen)
        #post_data = urlparse.parse_qs(s.rfile.read(length).decode('utf-8'))
        doc = None
        if cf.debug > 0:
            self.log_message('DEBUG: post body (len=%d): %s' %
                    (self.clen, s.replace('\n\r','')))
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
        self._send_response(doc, self.ctype)
        return

    def do_GET(self):
        if self._check_request() == False:
            return
        if opt.sec_lv and self._check_acl_san() == False:
            self.send_error(401)
            return
        if self.path == '/wsdl':
            fiap = fiapProto.fiapProto(strict_check=True, debug=cf.debug)
            doc = fiap.getwsdl()
            self._send_response(doc, 'text/xml; charset=utf-8')
            return
        elif self.path.startswith('/?'):
            fiap = fiapProto.fiapProto(strict_check=True, debug=cf.debug)
            doc = fiap.parseGETRequest(self.path)
            if doc == None:
                self.log_message('ERROR: %s' % fiap.getemsg())
                self.send_error(403, fiap.getemsg())
                return
            self._send_response(doc, 'text/json; charset=utf-8')
            return
        else:
            msg = 'unknown path, %s' % self.path
            self.log_message('ERROR: %s' % msg)
            self.send_error(403, msg)
            return

    def do_PUT(self):
        if self._check_request() == False:
            return
        msg = 'PUT is not allowed.'
        self.log_message(msg)
        self.send_error(405, msg)
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def run(port=18880, config=None):
    server = None
    if not opt.sec_lv:
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
    p.add_argument('-s', action='store', dest='sec_lv', default=0,
        help='specify to use TLS connection. 0, 1, or 2')
    p.add_argument('-c', action='store', dest='cfile', default=False,
        help='specify the file name of the configuration.')
    p.add_argument('-d', action='store', dest='debug', default=0,
        help='specify the debug level. 0, 1, or 2')
    opt = p.parse_args()
    return opt

#
# main
#
opt = parse_args()
cf = fiapConfig.fiapConfig(opt.cfile, security_level=opt.sec_lv, debug=opt.debug)
#
# set the runner and default port if needed.
#
if opt.sec_lv:
    if opt.port == None:
        opt.port = 18883
else:
    if opt.port == None:
        opt.port = 18880

run(port=opt.port, config=cf)
