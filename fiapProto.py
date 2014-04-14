#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fiapMongo
import dateutil.parser
from xml.etree.ElementTree import tostring
from xml.etree.ElementTree import Element
from xml.etree import ElementTree
from datetime import datetime
import pytz
import copy
import json
import uuid

_FIAPY_FIAP_VERSION = '20140401'
_FIAPY_MONGODB = { 'port': 27036 }
_FIAPY_MAX_ACCEPTABLESIZE = 60
_FIAPY_WSDL = './fiapy.wsdl'
_FIAPY_SERVICE_PORT = 'http://localhost:40080/'
_FIAPY_PRINT_TIMEZONE = 'Asia/Tokyo'
_FIAPY_MAX_TRAPTTL = 3600 # 1 hour

# XXX to be replaced to defined variable from the string.
_FIAP_METHOD_DATARQ = 'dataRQ'
_FIAP_METHOD_DATARS = 'dataRS'
_FIAP_METHOD_QUERYRQ = 'queryRQ'
_FIAP_METHOD_QUERYRS = 'queryRS'

_FIAPY_EMSG_INTERNAL_ACCESS_DATA = 'an error happend while accessing to the data.'

NS_XMLSOAP = 'http://schemas.xmlsoap.org/soap/envelope/'
NS_FIAPSOAP = 'http://soap.fiap.org/'
NS_FIAP = 'http://gutp.jp/fiap/2009/11/'

_NSMAP = {
  '' : NS_FIAP,
  'xmlsoap' : NS_XMLSOAP,
  'fiapsoap' : NS_FIAPSOAP,
  'fiap' : NS_FIAP
}

class fiapProto():

  def __init__(self, requester_address=None, requester_san=None, timezone=_FIAPY_PRINT_TIMEZONE, strict_check=False, debug=0):
    self._initmsg()
    self.wsdl = None
    self.requester_address = requester_address
    self.requester_san = requester_san
    self.timezone = timezone
    self.strict_check = strict_check
    self.debug = debug
    #
    # etree for the response
    #
    for prefix, uri in _NSMAP.iteritems():
      ElementTree.register_namespace(prefix, uri)
    e_envelope = ElementTree.Element('{%s}Envelope' % NS_XMLSOAP)
    e_envelope.append(ElementTree.Element('{%s}Body' % NS_XMLSOAP))
    self.et_root0 = ElementTree.ElementTree(e_envelope)

  def _initmsg(self):
    self.doc = None
    self.emsg = ''
    self.msg = ''
    self.method_name = None

  #
  # parse JSON and process it, then response in JSON.
  #
  def serverParseJSON(self, doc):
    self._initmsg()
    try:
      j_root = json.loads(doc)
    except ValueError as et:
      self.emsg = 'error in JSON parser, %s' % et.message
      return None
    except Exception as et:
      self.print_exception(et)
      self.emsg = 'error in JSON parser, %s' % et.message
      return None
    #
    # start to parse each method
    #
    handler = {
      _FIAP_METHOD_DATARQ : self._serverParseJson_DataRQ,
      _FIAP_METHOD_QUERYRQ : self._serverParseJson_QueryRQ }
    return json.dumps(self._parseJson(j_root, handler))

  #
  # handler to parse JSON
  #
  def _parseJson(self, j0, handler):
    # XXX copy just in case.
    j_root = copy.deepcopy(j0)
    #
    for mname, func in handler.iteritems():
      if j_root.has_key(mname):
        if self.strict_check == True and self._checkJsonBase(j_root) == False:
          self._setJsonResponse(mname, 400, self.emsg)
          print self.doc
          return self.doc
        return func(j_root)
    # error if it comes here.
    self.emsg = 'valid method name is not specified. (%s)' % self._tostring(j_root)
    self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
    return self.doc

  #
  # basic check of FIAP JSON
  #
  def _checkJsonBase(self, j_root):
    if j_root.has_key('fiap') == False:
      self.emsg = 'fiap key is not specified.'
      return False
    v = j_root.pop('fiap')
    if v != _FIAPY_FIAP_VERSION:
      self.emsg = 'fiap version must be %s, but %s' % (_FIAPY_FIAP_VERSION, v)
      return False
    #if len(j_root) != 1:
    #  self.emsg = 'only one method is allowed. (%s)' % j_root
    #  return False
    return True

  #
  # parse JSON query request
  #
  def _serverParseJson_QueryRQ(self, j_root):
    #
    # query
    #
    j_query = j_root.pop(_FIAP_METHOD_QUERYRQ)
    #
    # check type
    #
    k_type = j_query.get('type')
    #
    k_limit = self._getQueryAcceptableSize(j_query.get('acceptableSize'))
    k_skip = self._getQueryCursor(j_query.get('cursor'))
    j_key = j_query.pop('key')
    keys = self._getKeyList(j_key)
    if keys == None:
      self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
      return self.doc
    j_plist = []
    total = 0
    try:
      m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
      #
      # get points.
      #
      for k in keys:
        try:
          cursor = m.iterPoint(k, k_limit, k_skip)
        except fiapMongo.fiapMongoException as et:
          self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
          self._setJsonResponse(_FIAP_METHOD_QUERYRS, 500, self.emsg)
          return self.doc
        j_value = []
        for i in cursor:
          fixed_dt = datetime_naive_to_aware(i['time'])
          j_value.append({ 'time' : fixed_dt.strftime('%Y-%m-%dT%H:%M:%S%z'), 'value' : i['value'] })
          k['result'] += 1
          total += 1
        j_plist.append({ k['pid'] : j_value })
    except fiapMongo.fiapMongoException as et:
      self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
      self._setJsonResponse(_FIAP_METHOD_QUERYRS, 500, self.emsg)
      return self.doc
    #
    if self.debug > 0:
      for k in keys:
        print 'DEBUG: search key =', k
    if total == 0:
      self.emsg = 'There is no matched point for the query.'
      self._setJsonResponse(_FIAP_METHOD_QUERYRS, 404, self.emsg)
      return self.doc
    self._setJsonResponse(_FIAP_METHOD_QUERYRS, 200, 'OK', { 'point' : j_plist })
    return self.doc

  #
  # parse JSON data request
  #
  def _serverParseJson_DataRQ(self, j_root):
    j_pchunk = j_root.pop(_FIAP_METHOD_DATARQ)
    if self._fixTimeInPchunk(j_pchunk) == False:
      return self.doc
    #
    # prepare an interface for MongoDB 
    #
    total = 0
    try:
      m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
      try:
        total = m.insertPointChunk(j_pchunk)
      except fiapMongo.fiapMongoException as et:
        self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
        self._setJsonResponse(_FIAP_METHOD_DATARS, 500, self.emsg)
        return self.doc
    except fiapMongo.fiapMongoException as et:
      self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
      self._setJsonResponse(_FIAP_METHOD_DATARS, 500, self.emsg)
      return self.doc
    #
    # response to the data request in JSON
    #
    if total == 0:
      self.emsg = 'There is no point saved.'
      self._setJsonResponse(_FIAP_METHOD_DATARS, 404, self.emsg)
      return self.doc
    self.emsg = ''
    self._setJsonResponse(_FIAP_METHOD_DATARS, 200, 'OK')
    return self.doc

  #
  # convert an ISO8601 string into a datetime object.
  #
  def _fixTimeInPchunk(self, j_pchunk):
    for p in j_pchunk:
      pid = p.keys()[0]
      for v in p[pid]:
        if v.has_key('time') == False:
          self.emsg = 'a json key, time is not specified. (%s)' % self._tostring(i[pid])
          self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
          return False
        t = getutc(v['time'])
        if t == None:
          self.emsg = 'invalid time string has been found. (%s)' % v['time']
          self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
          return False
        v['time'] = t
    return True

  def _setJsonResponse(self, method, code, msg, add=None):
    msg = '%s %s' % (code, msg)
    if add != None:
      body = { 'response' : msg }
      for k, v in add.iteritems():
        body[k] = v
    else:
      body = { 'response' : msg }
    self.doc = { 'fiap' : _FIAPY_FIAP_VERSION, method : body }

  #
  # parse JSON binding format and convert to XML
  #
  # output: return a XML document, and set XML document into self.doc.
  #         return None in case of error, set JSON response into self.doc.
  #
  def JSONtoXML(self, doc):
    self._initmsg()
    try:
      j_root = json.loads(doc)
    except ValueError as et:
      self.emsg = 'error in JSON parser, %s' % et.message
      self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
      return None
    except Exception as et:
      self.print_exception(et)
      self.emsg = 'error in JSON parser, %s' % et.message
      self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
      return None
    #
    # start to parse each method
    #
    handler = {
      _FIAP_METHOD_DATARQ : self._JSONtoXML_DataRQ,
      _FIAP_METHOD_DATARS : self._JSONtoXML_DataRS,
      _FIAP_METHOD_QUERYRQ : self._JSONtoXML_QueryRQ,
      _FIAP_METHOD_QUERYRS : self._JSONtoXML_QueryRS }
    e_newroot = self._parseJson(j_root, handler)
    if e_newroot == None:
      self._setJsonResponse(_FIAP_METHOD_DATARS, 400, self.emsg)
      return None
    self.doc = self.getXMLdoc(e_newroot)
    return self.doc

  #
  # parse JSON query request and convert to XML
  #
  # input: json root
  # output: e_newroot or None.
  #
  def _JSONtoXML_QueryRQ(self, j_root):
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRQ)
    j_query = j_root.pop(_FIAP_METHOD_QUERYRQ)
    attr = {}
    attr['id'] = str(uuid.uuid1())
    for k in [ 'type', 'acceptableSize', 'cursor', 'ttl', 'callbackData', 'callbackControl' ]:
      if j_query.has_key(k) == False:
        continue
      attr[k] = str(j_query.pop(k))
    e_query = ElementTree.SubElement(e_header, '{%s}query' % NS_FIAP, attr)
    #
    # key
    #
    j_key = j_query.pop('key')
    if len(j_query) != 0:
      self.emsg = 'only one key of json key is allowed in the query spec. (%s)' % j_query
      return None
    while len(j_key) != 0:
      attr = {}
      v = j_key.pop(0)
      for k in [ 'id', 'attrName', 'eq', 'ne', 'lt', 'gt', 'lteq', 'gteq', 'select', 'trap' ]:
        if v.has_key(k) == False:
          continue
        attr[k] = v.pop(k)
      if len(v) != 0:
        self.emsg = 'there is something unknown json key in the key spec. (%s)' % v
        return None
      ElementTree.SubElement(e_query, '{%s}key' % NS_FIAP, attr)
    return e_newroot

  #
  # parse JSON query response and convert to XML
  #
  # input: json root
  # output: e_newroot or None.
  #
  def _JSONtoXML_QueryRS(self, j_root):
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRS)
    attr = {}
    j_query = j_root.pop(_FIAP_METHOD_QUERYRS)
    j_res = j_query.pop('response')
    if j_res == 'OK':
      e_res = ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
      while len(j_query) != 0:
        j_point = j_query.pop(0)
        pid = j_point.keys()[0]
        e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': pid})
        j_value = j_point.pop(pid)
        v = None
        while len(j_value) != 0:
          v = j_value.pop(0)
          while len(v) != 0:
            if v.has_key('time') == False:
              self.emsg = 'time key is not specified in the value spec. [%s]' % v
              return None
            if v.has_key('value') == False:
              self.emsg = 'value key is not specified in the vlaue spec. [%s]' % v
              return None
            t = getutc(v.pop('time'))
            e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : t.strftime('%Y-%m-%dT%H:%M:%S%z') } )
            e_value.text = v.pop('value')
            if len(v) != 0:
              self.emsg = 'there is something unknown json key in the value spec. (%s)' % v
              return None
      if v == None:
        self.emsg = 'there is no point in the reponse. (%s)' % v
        return None
    else:
      if len(j_query) != 0:
        self.emsg = 'only single response of json key is allowed in error case. (%s)' % j0
        return None
      self._getErrorObject(e_header, 'error', j_res)
      e_res = ElementTree.SubElement(e_header, '{%s}error' % NS_FIAP)
      e_res.text = j_res
    return e_newroot

  #
  # parse JSON data request and convert to XML
  #
  # input: json root
  # output: e_newroot or None.
  #
  def _JSONtoXML_DataRQ(self, j_root):
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARQ)
    attr = {}
    j_data = j_root.pop(_FIAP_METHOD_DATARQ)
    while len(j_data) != 0:
      j_point = j_data.pop(0)
      pid = j_point.keys()[0]
      e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': pid})
      j_value = j_point.pop(pid)
      while len(j_value) != 0:
        v = j_value.pop(0)
        while len(v) != 0:
          if v.has_key('time') == False:
            self.emsg = 'time key is not specified in the value spec. [%s]' % v
            return None
          if v.has_key('value') == False:
            self.emsg = 'value key is not specified in the vlaue spec. [%s]' % v
            return None
          t = getutc(v.pop('time'))
          e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : t.strftime('%Y-%m-%dT%H:%M:%S%z') } )
          e_value.text = v.pop('value')
          if len(v) != 0:
            self.emsg = 'there is something unknown json key in the value spec. (%s)' % v
            return None
    return e_newroot

  #
  # parse JSON data response and convert to XML
  #
  # input: json root
  # output: e_newroot or None.
  #
  def _JSONtoXML_DataRS(self, j_root):
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARS)
    attr = {}
    j_data = j_root.pop(_FIAP_METHOD_DATARS)
    j_res = j_data.pop('response')
    if len(j_data) != 0:
      self.emsg = 'only single response of json key is allowed. (%s)' % j_root
      return None
    if j_res == 'OK':
      e_res = ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
    else:
      e_res = ElementTree.SubElement(e_header, '{%s}error' % NS_FIAP)
      e_res.text = j_res
    return e_newroot

  #
  # parse XML binding format and convert to JSON.
  #
  def XMLtoJSON(self, doc):
    self._initmsg()
    try:
      e_root = ElementTree.XML(doc)
    except Exception as et:
      self.print_exception(et)
      self.emsg = 'internal error in parsing XML.'
      return None
    if self.strict_check == True and self.checkXMLbase(e_root) == False:
      return None
    #
    # start to parse each method
    #
    handler = {
      _FIAP_METHOD_DATARQ : [ self._XMLtoJSON_DataRQ, [ 'body' ] ],
      _FIAP_METHOD_DATARS : [ self._XMLtoJSON_DataRS, [ 'header' ] ],
      _FIAP_METHOD_QUERYRQ : [ self._XMLtoJSON_QueryRQ, [ 'header' ] ],
      _FIAP_METHOD_QUERYRS : [ self._XMLtoJSON_QueryRS, [ 'header', 'body' ] ] }
    if self._parseXML(e_root, handler) != None:
      return json.dumps(self._parseXML(e_root, handler))
    else:
      return None

  #
  # query method parser
  #
  def _XMLtoJSON_QueryRQ(self, e_root, e_header, e_body):
    #
    # start to parse a query class
    #
    e_query = e_header.find('./fiap:query', namespaces=_NSMAP)
    if e_query == None:
      self.emsg = 'query is not specified. [%s]' % tostring(e_root)
      return None
    #
    # check the type attribute.
    # either storage or stream is valid.
    #
    type = e_query.get('type')
    if type == None:
      self.emsg = 'type is not specified. [%s]' % tostring(e_query)
      return None
    elif type != 'storage' and type != 'stream':
      self.emsg = 'invalid type is specified. [%s]' % type
      return None
    #
    # translate Query Object into JSON
    #
    j_query = {} 
    for k in [ 'uuid', 'type', 'acceptableSize', 'cursor', 'ttl', 'callbackData', 'callbackConrol' ]:
      v = e_query.get(k)
      if v != None:
        j_query[k] = v
    #
    # translate Key Objects into JSON
    #
    for e_key in e_query.findall('./fiap:key', namespaces=_NSMAP):
      key_list = []
      key = {}
      for k in [ 'id', 'attrName', 'eq', 'ne', 'lt', 'gt', 'lteq', 'gteq', 'select', 'trap' ]:
        v = e_key.get(k)
        if v != None:
          key[k] = v
      key_list.append(key)
    j_query["key"] = key_list
    return { _FIAP_METHOD_QUERYRQ : j_query }

  #
  # query response method parser
  #
  def _XMLtoJSON_QueryRS(self, e_root, e_header, e_body):
    if self.strict_check == True:
      e_query = e_header.find('./fiap:query', namespaces=_NSMAP)
      if e_query == None:
        self.emsg = 'query is not specified. [%s]' % tostring(e_root)
        return None
    #
    if self._XMLtoJSON_OKorError(e_header) == None:
      return None
    #
    # XML is valid, but something error happens on the server side.
    #
    if self.msg != 'OK':
      self.doc = { _FIAP_METHOD_QUERYRS : { "response": self.msg } }
      return self.doc
    #
    # parse a list of Point Objects.
    #
    pset_all = self._parseXMLPointClass(e_root)
    if len(pset_all) == 0:
      self.emsg = 'There is no matched point for the query.'
      self._setJsonResponse(_FIAP_METHOD_QUERYRS, 404, self.emsg)
      return self.doc
    self.doc = { _FIAP_METHOD_QUERYRS : { "response" : "OK", "point" : self._getJSONPointSpec(pset_all) } }
    return self.doc

  #
  # parse XML data request and convert into JSON.
  #
  def _XMLtoJSON_DataRQ(self, e_root, e_header, e_body):
    #
    # parse a list of Point Objects.
    #
    pset_all = self._parseXMLPointClass(e_root)
    if len(pset_all) == 0:
      self.doc = { _FIAP_METHOD_DATARQ : { } }
      self.emsg = 'There is No Point in the object.'
      return self.doc
    #
    # translate XML data request into JSON
    #
    self.doc = { _FIAP_METHOD_DATARQ : self._getJSONPointSpec(pset_all) }
    return self.doc

  #
  # parse XML DataRS and convert into JSON.
  #
  def _XMLtoJSON_DataRS(self, e_root, e_header, e_body):
    if self._XMLtoJSON_OKorError(e_header) == None:
      return None
    self.doc = { _FIAP_METHOD_DATARS : { "response": "OK" } }
    return self.doc

  def _XMLtoJSON_OKorError(self, e_header):
    #
    # if there is an error object, it just parse the object and ignores others.
    #
    e_error = e_header.find('./fiap:error', namespaces=_NSMAP)
    if e_error != None:
      t = e_error.get('type')
      v = e_error.text
      # XXX should it be error if there is no type or/and text.
      self.msg = '%s: %s' % (t, v)
      return self.msg
    #
    # check if there is an OK object.
    #
    if e_header.find('./fiap:OK', namespaces=_NSMAP) == None:
      self.emsg = 'either OK or error object must be specified.'
      return None
    self.msg = 'OK'
    return self.msg

  #
  # parse XML Point Class.
  # write data if it's a request and non-translation mode.
  #
  # input: e_root
  # output: pset
  #
  def _parseXMLPointClass(self, e_root):
    result = True
    pset_all = []
    for e in e_root.findall('.//fiap:point', namespaces=_NSMAP):
      pset = self._getPointList(e)
      if len(pset) == 0:
        result = False
        break
      pset_all.extend(pset)
    return pset_all

  #
  # input: pset
  # output: pspec_list in dict of FIAP JSON
  #
  def _getJSONPointSpec(self, pset):
    pspec_list = []
    pspec = {}
    current = None
    for i in pset:
      if current != i['pid']:
        current = i['pid']
        pspec[current] = []
        pspec_list.append(pspec[current])
      tstr = datetime.isoformat(i['time'].astimezone(pytz.timezone(self.timezone)))
      pspec[current].append({'time':tstr, 'value':i['value']})
    return pspec_list

  #
  # parse XML and process it, then response in XML.
  #
  def serverParseXML(self, doc):
    self._initmsg()
    try:
      e_root = ElementTree.XML(doc)
    except Exception as et:
      self.print_exception(et)
      self.emsg = 'internal error in parsing XML.'
      return None
    if self.strict_check == True and self._checkXMLbase(e_root) == False:
      return None
    #
    # start to parse each method
    #
    handler = {
      _FIAP_METHOD_DATARQ : [ self._serverParseXML_DataRQ, [ 'body' ] ],
      _FIAP_METHOD_QUERYRQ : [ self._serverParseXML_QueryRQ, [ 'header' ] ] }
    return self._parseXML(e_root, handler)

  #
  # check SOAP XML base.
  #
  def _checkXMLbase(self, e_root):
    if e_root.tag != '{http://schemas.xmlsoap.org/soap/envelope/}Envelope':
      self.emsg = 'there is no xmlsoap:Envelope. [%s]' % tostring(e_root)
      return False
    if e_root.find('./xmlsoap:Body', namespaces=_NSMAP) == None:
      self.emsg = 'there is no xmlsoap:Body. [%s]' % tostring(e_root)
      return False
    return True

  #
  # XML parser with the handler.
  #   { <method> : [ <function>, [ <header and/or boday> ] ], ... }
  #
  # output: self.msg or None
  #
  def _parseXML(self, e_root, handler):
    method = None
    basepath = './/fiapsoap:%s//fiap:%s'
    e_any = { 'header':None, 'body':None }
    for mname, clist in handler.iteritems():
      if e_root.find('./*/fiapsoap:%s' % mname, namespaces=_NSMAP) == None:
        continue
      for i in clist[1]:
        e_any[i] = e_root.find(basepath % (mname, i), namespaces=_NSMAP)
        if e_any[i] == None:
          self.emsg = 'neither transport nor header is specified. [%s]' % tostring(e_root)
          return None
      method = clist[0]
    if method == None:
      self.emsg = 'FIAP method is not specified.'
      return None
    if len(e_any) == 0:
      self.emsg = 'either header nor body for %s is specified.' % mname
      return None
    self.method_name = mname
    return method(e_root, e_any['header'], e_any['body'])

  #
  # query method parser
  #
  def _serverParseXML_QueryRQ(self, e_root, e_header, e_body):
    #
    # start to parse a query class
    #
    e_query = e_root.find('.//fiap:query', namespaces=_NSMAP)
    if e_query == None:
      self.emsg = 'query is not specified. [%s]' % tostring(e_root)
      return None
    #
    # check uuid.
    # XXX it's not used.
    #
    uuid = e_query.get('id')
    #
    # check the type attribute.
    # either storage or stream is valid.
    #
    type = e_query.get('type')
    if type == None:
      self.emsg = 'type is not specified. [%s]' % tostring(e_query)
      return None
    elif type == 'storage':
      return self._serverParseFETCH(e_root, e_query)
    elif type == 'stream':
      return self._serverParseTRAP(e_root, e_query)
    else:
      self.emsg = 'invalid type is specified. [%s]' % type
      return None

  #
  # FETCH protocol parser
  #
  def _serverParseFETCH(self, e_root, e_query):
    k_limit = self._getQueryAcceptableSize(e_query.get('acceptablesSize'))
    k_skip = self._getQueryCursor(e_query.get('cursor'))
    iter_keys = e_query.iterfind('./fiap:key', namespaces=_NSMAP)
    keys = self._getKeyList(iter_keys)
    if keys == None:
      return None
    #
    # save the data and create a response message.
    #
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRS, e_root)
    try:
      m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
      #
      # get points.
      #
      for k in keys:
        try:
          cursor = m.iterPoint(k, k_limit, k_skip)
        except fiapMongo.fiapMongoException as et:
          self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
          self._getErrorObject(e_header, 'error', self.emsg)
          return None
        for i in cursor:
          fixed_dt = datetime_naive_to_aware(i['time'])
          e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': k['pid']})
          e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : fixed_dt.strftime('%Y-%m-%dT%H:%M:%S%z') } )
          e_value.text = i['value']
          k['result'] += 1
    except fiapMongo.fiapMongoException as et:
      self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
      self._getErrorObject(e_header, 'error', self.emsg)
      return None
    #
    total = 0
    for k in keys:
      total += k['result']
      if self.debug > 0:
        print 'DEBUG: search key =', k
        print '    result =', k['result']
    if total == 0:
      self.emsg = 'There is no matched point for the query.'
      self._getErrorObject(e_header, 'error', self.emsg)
      return self.doc
    ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
    self.doc = self.getXMLdoc(e_newroot)
    return self.doc

  #
  # TRAP protocol parser
  #
  def _serverParseTRAP(self, e_root, e_query):
    f_remove = False
    req = {}
    req['limit'] = self._getQueryAcceptableSize(e_query.get('acceptablesSize'))
    ttl = self._getQueryTTL(e_query.get('ttl'))
    if ttl == 0:
      req['tte'] = 0
    else:
      dt = datetime.now(pytz.timezone(self.timezone)) + timedelta(seconds=ttl)
      dt.astimezone(pytz.timezone('UTC'))
      req['tte'] = dt
    iter_keys = e_query.iterfind('./fiap:key', namespaces=_NSMAP)
    req['qk'] = self._getKeyList(iter_keys)
    if req['qk'] == None:
      return None
    #
    # register it to trapy.py
    #
    req['cd'] = e_query.get('callbackData')
    if req['cd'] == None:
      self.emsg = 'callbackData is not specified.'
      return None
    req['cc'] = e_query.get('callbackControl')
    if req['cc'] == None:
      self.emsg = 'callbackControl is not specified.'
      return None
    e_query = e_root.find('.//{%s}query' % NS_FIAP)
    req['h'] = ElementTree.tostring(e_query.getroot(), encoding='utf-8')
    req['rip'] = self.requester_address
    if req['rip'] == None:
      self.emsg = "internall error happens.  requester's addrss must be specified"
      return None
    req['rsan'] = self.requester_san
    #
    # register this trap and create a response message.
    #
    e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRS, e_root)
    try:
      m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
      try:
        m.saveTrap(req)
      except:
        self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
        self._getErrorObject(e_header, 'error', self.emsg)
        return None
    except fiapMongo.fiapMongoException as et:
      self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
      self._getErrorObject(e_header, 'error', self.emsg)
      return None
    ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
    self.doc = self.getXMLdoc(e_newroot)

    return self.doc

  #
  # check the acceptableSize and fix it if needed.
  # input: the value of acceptableSize
  # output: value or _FIAPY_MAX_ACCEPTABLESIZE
  #
  def _getQueryAcceptableSize(self, v_limit):
    #
    # get acceptableSize as limit()
    #
    k_limit = _FIAPY_MAX_ACCEPTABLESIZE
    if v_limit == None:
      if self.debug > 0:
        print 'DEBUG: acceptableSize is not specified.  set %d for the limit' % _FIAPY_MAX_ACCEPTABLESIZE
      return _FIAPY_MAX_ACCEPTABLESIZE
    elif v_limit > _FIAPY_MAX_ACCEPTABLESIZE:
      self.emsg = 'acceptableSize must be less than %d, but is too big, %d' % (_FIAPY_MAX_ACCEPTABLESIZE, v_limit)
      print 'WARNING: %s' % self.emsg
      return _FIAPY_MAX_ACCEPTABLESIZE
    return v_limit

  #
  # get cursor as skip()
  # output: cursor or 0
  #
  def _getQueryCursor(self, v_skip):
    if v_skip == None:
      return 0
    return v_skip

  #
  # get TTL
  # output: ttl or _FIAPY_MAX_TRAPTTL
  #
  def _getQueryTTL(self, v_ttl):
    if v_ttl == None:
      if self.debug > 0:
        print 'DEBUG: ttl is not specified.  set ttl %d for the default' % _FIAPY_MAX_TRAPTTL
      return _FIAPY_MAX_TRAPTTL
    return v_ttl

  #
  # data method parser for the server.
  # XXX: need to implement to process the pointSet.
  #      currently, it doesn't save the id of any pointSet.
  #
  def _serverParseXML_DataRQ(self, e_root, e_header, e_body):
    #
    # prepare an interface for MongoDB 
    #
    try:
      m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
      #
      # parse the point objects and save data to the DB
      #
      pset_all = []
      for e in e_root.findall('.//fiap:point', namespaces=_NSMAP):
        pset = self._getPointList(e)
        if len(pset) == 0:
          self.msg = 'There is no point data in a Point Object. Just skip it. (%s)' % e
          # XXX skip it to process all data as much as possible.
          continue
        try:
          m.insertPointList(pset)
        except fiapMongo.fiapMongoException as et:
          self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
          self._getErrorObject(e_header, 'error', self.emsg)
          break
        pset_all.extend(pset)
    except fiapMongo.fiapMongoException as et:
      self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
      self._getErrorObject(e_header, 'error', self.emsg)
      return None
    #
    # response to data request in XML
    #
    e_root, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARS)
    #
    if len(pset_all) == 0:
      self.emsg = 'There is No Point in the object.'
      self._getErrorObject(e_header, 'error', self.emsg)
      return None
    else:
      self.emsg = ''
      ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
    self.doc = self.getXMLdoc(e_root)
    return self.doc

  #
  # create an Error Object.
  # input: a Header Object, error type, message
  # output: a Error Object.
  #
  def _getErrorObject(self, e_header, type, msg):
    e_error = ElementTree.SubElement(e_header, '{%s}error' % NS_FIAP, { 'type' : '%s' % type})
    e_error.text = msg

  #
  # create new etree for the specifying method.
  # copy from a query object of the e_root in case of the query response.
  #
  # input: method type
  # output: new etree, and pointer to header and body.
  #
  def getNewXMLdoc(self, type, e_root=None):
    e_newroot = copy.deepcopy(self.et_root0)
    e_sb = e_newroot.find('.//xmlsoap:Body', namespaces=_NSMAP)
    e_rs = ElementTree.SubElement(e_sb, '{%s}%s' % (NS_FIAPSOAP, type))
    e_tr = ElementTree.SubElement(e_rs, '{%s}transport' % NS_FIAP)
    e_header = None
    e_body = None
    if type == _FIAP_METHOD_DATARS:
      e_header = ElementTree.SubElement(e_tr, '{%s}header' % NS_FIAP)
    elif type == _FIAP_METHOD_QUERYRS:
      if e_root == None:
        print 'ERROR: internal error.  e_root must be specified in query type.'
        raise Exception
      e_header = ElementTree.SubElement(e_tr, '{%s}header' % NS_FIAP)
      e_query = e_root.find('.//{%s}query' % NS_FIAP)
      e_header.append(e_query)
      e_body = ElementTree.SubElement(e_tr, '{%s}body' % NS_FIAP)
    elif type == _FIAP_METHOD_DATARQ:
      e_body = ElementTree.SubElement(e_tr, '{%s}body' % NS_FIAP)
    elif type == _FIAP_METHOD_QUERYRQ:
      e_header = ElementTree.SubElement(e_tr, '{%s}header' % NS_FIAP)
    else:
      print 'ERROR: internal error.  invalid type (%s) specified.' % type
      raise Exception
    return e_newroot, e_header, e_body

  #
  # input: ElementTree
  # output: a string of an XML document.
  #
  def getXMLdoc(self, e_root):
    doc = ElementTree.tostring(e_root.getroot(), encoding='utf-8')
    doc = '<?xml version="1.0" encoding="UTF-8"?>' + doc
    return doc

  #
  # input: an iterator of dict objects including keys.
  #        e.g. etree.keys or json keys.
  # output: a list object specifying the query object..
  #         [ { 'pid': pid, 'an': attrName, 'op': select,
  #             'cond': { '$where' : 'condition' }, 'trap': True }, ... ]
  #
  def _getKeyList(self, iter_keys):
    if iter_keys == None:
      self.emsg = 'there seems no key in the Query'
      return None
    keys = []
    for e_key in iter_keys:
      key = {}
      #
      # check id.
      #
      pid = e_key.get('id')
      if pid == None:
        self.emsg = 'id attribute is not specified. [%s]' % self._tostring(e_key)
        return None
      key['pid'] = pid

      #
      # check attrName.
      # XXX should it check the value of attrName ? e.g. either 'time' or 'value' is valid.
      #
      a = e_key.get('attrName')
      if a == None:
        self.emsg = 'a attribute is not specified.' % self._tostring(e_key)
        return None
      key['an'] = a

      #
      # check 'select'
      #
      key['op'] = None
      a = e_key.get('select')  # for selection of {maximum, minimum} if c_select == 'm':
      if a == 'maximum':
        key['op'] = 'max'
      elif a == 'minimum':
        key['op'] = 'min'
      elif a != None:
        self.emsg = 'unkown value of select is specified. [%s]' % a
        return None

      #
      # make a condition.
      # ignore other conditions if 'eq' is specified.
      #
      if key['an'] == 'time':
        conv_method = fiapMongo.getKeyCondTime
      elif key['an'] == 'value':
        conv_method = fiapMongo.getKeyCondValue
      else:
        self.emsg = 'invalid attrName is specified. [%s]' % self._tostring(e_key)
        return None
      key['cond'] = self.getKeyCond(e_key, conv_method)

      #
      # trap
      #
      key['trap'] = False
      a = e_key.get('trap')  # for event detection {changed}
      if a == 'changed':
        key['trap'] = True
      elif a != None:
        self.emsg = 'unkown value of select is specified. [%s]' % self._tostring(e_key)
        return None

      keys.append( key )

    return keys

  #
  # input: dict object such as a Key Element.
  #        conversion method of the value.
  # output: a dict object specifying the where close.
  #         { '$where' : condition }
  #
  def getKeyCond(self, e_key, conv_method):
    cond = ''
    a = e_key.get('eq')
    if a != None:
      cond = conv_method(a, '==')
      if c == None:
        return None
    else:
      a = e_key.get('neq')
      if a != None:
        cond = conv_method(a, '!=')
        if c == None:
          return None
      else:
        for k, v in { 'lt':'<', 'gt':'>', 'lteq':'<=', 'gteq':'>=' }.iteritems():
          a = e_key.get(k)
          if a == None:
            continue
          if len(cond) != 0:
            cond += ' && '
          c = conv_method(a, v)
          if c == None:
            return None
          cond += c
    if len(cond) == 0:
      return None
    return { '$where' : cond }

  #
  # input: a dict object such as a Point Element.
  # output: a dict object specifying the point.
  #         {'pid':pid, 'time':utc, 'value':v}
  #
  def _getPointList(self, po):
    pset = []
    pid = po.attrib['id']
    if pid == None:
      self.emsg = 'pointID is not specified in the point element. [%s]' % self._tostring(po)
      return []
    if len(pid) == 0:
      self.emsg = 'null pointID is specified in the point element. [%s]' % self._tostring(po)
      return []
    for e_value in po.iter(tag='{http://gutp.jp/fiap/2009/11/}value'):
      timestr = e_value.get('time')
      if timestr == None:
        self.emsg = 'time is not specified in the value element. [%s]' % self._tostring(e_value)
        return []
      if len(timestr) == 0:
        self.emsg = 'null time is specified in the value element. [%s]' % self._tostring(e_value)
        return []
      utc = getutc(timestr)
      if utc == None:
        self.emsg = 'invalid time string (%s)' % timestr
        return []
      v = e_value.text
      if v == None:
        self.emsg = 'value is not specified in the value element. [%s]' % self._tostring(po)
        return []
      p = {'pid':pid, 'time':utc, 'value':v}
      if self.debug > 0:
        print 'DEBUG: point =', p
      pset.append(p)
    return pset

  #
  # handler for print the dict or element object
  #
  def _tostring(self, obj):
    if type(obj) == Element:
      return tostring(obj)
    elif type(obj) == dict:
      return dict

  #
  # output: self.emsg
  #
  def getemsg(self):
    return self.emsg

  #
  # output: wsdl
  #
  def getwsdl(self, service_point=None, wsdl_file=None):
    if self.wsdl == None:
      if service_point == None:
        #service_point = 'http://live-e-storage.hongo.wide.ad.jp/axis2/services/FIAPStorage/'
        service_point = _FIAPY_SERVICE_PORT
      if wsdl_file == None:
        wsdl_file = _FIAPY_WSDL
      fp = open(wsdl_file)
      self.wsdl = ''.join(fp.readlines()).replace('__FIAP_SERVICE_PORT__', service_point, 1)
    return self.wsdl

  def print_exception(self, et):
    print et
    print 'exception type: ', str(type(et))

#
# fiap functions
#

#
# print a ptv list.
# input: { 'pid':<point id>, 'time':<time>, 'value':<value> }
#     tzstr is a string of a timezone such as 'UTC', 'Asia/Tokyo'
#
def print_points(pset, tzstr='UTC'):
  for i in pset:
    tstr = datetime.isoformat(i['time'].astimezone(pytz.timezone(tzstr)))
    print 'point id="%s" time="%s" value="%s"' % (i['pid'], tstr, i['value'])

#
# input: datetime string
#        if the string looks a naive datetime string, replace to UTC.
#
# output: datetime object in UTC
#
def getutc(dtstr):
  try:
    dt = dateutil.parser.parse(dtstr)
    d = datetime_naive_to_aware(dt)
    d = dt.astimezone(pytz.timezone('UTC'))
  except Exception as et:
    print et
    print 'exception type: ', str(type(et))
    return None
  return d

def datetime_naive_to_aware(dt):
  if dt.tzinfo == None:
    return dt.replace(tzinfo=pytz.UTC)
  return dt

