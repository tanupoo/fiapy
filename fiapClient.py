#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import sys
import re
import httplib, urllib
import argparse
import json
import fiapProto

def postrequest(host, port, url='/', content=None, ctype='text/xml; charset=utf-8',):

  headers = {}
  headers['Content-Type'] = ctype
  headers['Accept'] = ctype
  headers['Content-Length'] = len(content)

  conn = httplib.HTTPConnection(host, port)
  try:
    conn.request("POST", url, content, headers)
    response = conn.getresponse()
  except Exception as e:
    print e, str(type(e))
    exit(1)

  print 'HTTP: %s %s' % (response.status, response.reason)
  data = response.read()
  conn.close()
  return data

#
# fiapWrite.py -s server [-p port] [-c data file] [-u url] [-x]
# fiapWrite.py -w wsdl [-c data file]
#
def parse_args():
  p = argparse.ArgumentParser()
  p.add_argument('-c', action='store', dest='cfile', default=None,
    help='specify the filename of the content.')
  p.add_argument('-s', action='store', dest='server', default=None, required=True,
    help='specify the server name in the URL.')
  p.add_argument('-p', action='store', dest='port', default=18880,
    help='specify the port number of the server.')
  p.add_argument('-u', action='store', dest='url', default='/',
    help='specify the path of the service in the URL.')
  p.add_argument('-w', action='store', dest='wsdl', default=None,
    help='specify the wsdl.')
  p.add_argument('-x', action='store_true', dest='req_to_xml', default=False,
    help='specify to send an XML request.')
  p.add_argument('-X', action='store_true', dest='res_to_xml', default=False,
    help='specify to output an XML response.')
  p.add_argument('-d', action='store', dest='debug', default=0,
    help='specify the debug level.')
  return p.parse_args()

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

#
# input: plist: # [ { <point spec> }, ... ]
#
# echo '{ "point":"http://example.org/light/01", "time":"2014-04-01T05:50:34+09:00", "value":25.2 }' | fiapClient.py -a -p
#
if __name__ == '__main__' :
    opt = parse_args()

    debug = opt.debug

    #soapGetAddressLocation(opt.wsdl)

    if opt.cfile != None:
        fp = open(opt.cfile)
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
    # send the request and get a response.
    #
    res = postrequest(opt.server, opt.port, url=opt.url, content=req_doc, ctype=ctype)
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
        res_doc = json.dumps(json.loads(res_doc), indent=2)
    if req_doc == None:
        print 'ERROR: %s' % fiap.getemsg()
        exit(1)
    print res_doc
