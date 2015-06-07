#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fiapMongo
import dateutil.parser
import dateutil.tz
from xml.etree.ElementTree import tostring
from xml.etree.ElementTree import Element
from xml.etree import ElementTree
from datetime import datetime
import copy
import json
import uuid

_FIAPY_FIAP_VERSION = '20140401'
_FIAPY_MONGODB = { 'port': 27036 }
_FIAPY_MAX_ACCEPTABLESIZE = 512
_FIAPY_WSDL = './fiapy.wsdl'
_FIAPY_SERVICE_PORT = 'http://133.11.168.118:18880/' # XXX should be picked dynamically.
_FIAPY_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
_FIAPY_PRINT_TZNAME = 'Asia/Tokyo'
_FIAPY_MAX_TRAPTTL = 3600 # 1 hour

_HTTP_CODE_OK = '200' # OK
_HTTP_CODE_BAD_REQUEST = '400' # Bad Request
_HTTP_CODE_NOT_FOUND = '404' # Not Found
_HTTP_CODE_METHOD_NOT_ALLOWED = '405' # Method Not Allowed
_HTTP_CODE_INTERNAL_ERROR = '500' # Internal Server Error
_HTTP_CODE_NOT_IMPLEMENTED = '501' # Not Implemented

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

    def __init__(self, requester_address=None, requester_san=None,
                 tzname=_FIAPY_PRINT_TZNAME, strict_check=False, debug=0):
        self._initmsg()
        self.wsdl = None
        self.requester_address = requester_address
        self.requester_san = requester_san
        self.tzname = tzname
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
    # parse JSON format and process it, then response in JSON format.
    #
    # @return str success and it is the response message in JSON format.
    # @return None should raise HTTP error at the caller.
    #
    def serverParseJSON(self, doc):
        self._initmsg()
        try:
            j_root = json.loads(doc)
        except ValueError as et:
            self.emsg = 'error in JSON parser, %s' % et.message
            return None
        except Exception as et:
            print_exception(et)
            self.emsg = 'error in JSON parser, %s' % et.message
            return None
        #
        # start to parse each method
        #
        handler = {
            _FIAP_METHOD_DATARQ : self._serverParseJSON_DataRQ,
            _FIAP_METHOD_QUERYRQ : self._serverParseJSON_QueryRQ }
        ret = self._parseJSON(j_root, handler)
        if ret == None:
            return ret
        return json.dumps(ret)

    #
    # parse keys in the GET request
    #
    def parseGETRequest(self, url_path):
        qspec = {}
        qspec['type'] = 'storage'
        qspec['key'] = []
        pids = []
        conds = {}
        #
        # it doesn't need to always begin '?'.
        #
        for elm in url_path[2:].split('&'):
            #
            # XXX potentially, the injection attack could happen
            # because the keys and some conditions are added
            # into the query without check.
            #
            if elm.startswith('k=') == True:
                pids.append(elm[2:])
            elif elm.startswith('_=') == True:
                pass
            elif elm.startswith('a=') == True:
                if elm[2:] == '0':
                    conds['attrName'] = 'time'
                elif elm[2:] == '1':
                    conds['attrName'] = 'value'
                else:
                    self.emsg = 'invalid element [%s]' % elm
                    return None
            elif elm.startswith('s=') == True:
                if elm[2:] == '0':
                    conds['select'] = 'minimum'
                elif elm[2:] == '1':
                    conds['select'] = 'maximum'
                else:
                    self.emsg = 'invalid element [%s]' % elm
                    return None
            elif elm.startswith('i=') == True:
                qspec['acceptableSize'] = elm[2:]
            else:
                cond_list = { 'eq=':'eq', 'ne=':'ne', 'lt=':'lt', 'gt=':'gt',
                             'lteq=':'lteq', 'gteq=':'gteq' }
                found = False
                for k, v in cond_list.iteritems():
                    if elm.startswith(k) == True:
                        conds[v] = elm[len(k):]
                        found = True
                if found == False:
                    self.emsg = 'invalid element [%s]' % elm
                    return None
        if len(pids) == 0:
            self.emsg = 'no keys are specified'
            return None
        if self.debug > 0:
            print 'DEBUG: pids=', pids
            print 'DEBUG: conds=', conds
        if len(conds) == 0:
            conds = { 'attrName':'time', 'select':'maximum' }
        for pid in pids:
            qspec['key'].append({pid:conds})
        req = {'fiap':{'version':_FIAPY_FIAP_VERSION,'queryRQ':qspec}}
        if self.debug > 0:
            print 'DEBUG: parsed getreq=', req
        return self.serverParseJSON(json.dumps(req))

    #
    # parse keys in the GET request
    #
    def parseGETRequestOLD(self, url_path):
        pids = []
        for k in url_path[2:].split('&'):
            if k.startswith('k=') == True:
                pids.append(k[2:])
            elif k.startswith('_=') == True:
                pass
            else:
                self.emsg = 'invalid element, %s' % k
                return None
        if not pids:
            self.emsg = 'no keys are specified'
            return None
        qspec = {}
        qspec['type'] = 'storage'
        qspec['key'] = []
        for pid in pids:
            qspec['key'].append({pid:{'attrName':'time', 'select':'maximum'}})
        req = {'fiap':{'version':_FIAPY_FIAP_VERSION,'queryRQ':qspec}}
        print 'DEBUG:', req
        return self.serverParseJSON(json.dumps(req))

    #
    # handler to parse JSON
    #
    def _parseJSON(self, j0, handler):
        # XXX copy just in case.
        #if j0.has_key('fiap') == False:
        #    return None
        #j_root = copy.deepcopy(j0['fiap'])
        j_root = j0.get('fiap')
        if j_root == None:
            return None
        #
        for mname, func in handler.iteritems():
            j_body = j_root.get(mname)
            if j_body:
                if self.strict_check == True and self._checkJSONBase(j_root) == False:
                    self._setJSONResponse(mname, _HTTP_CODE_BAD_REQUEST, self.emsg)
                    return self.doc
                return func(j_root, j_body)
        # error if it comes here.
        self.emsg = 'valid method name is not specified. (%s)' % self._tostring(j_root)
        self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_METHOD_NOT_ALLOWED, self.emsg)
        return self.doc

    #
    # basic check of FIAP JSON
    #
    def _checkJSONBase(self, j_root):
        if j_root.has_key('version') == False:
            self.emsg = 'version key is not specified.'
            return False
        v = j_root['version']
        if v != _FIAPY_FIAP_VERSION:
            self.emsg = 'version must be %s, but %s' % (_FIAPY_FIAP_VERSION, v)
            return False
        #if len(j_root) != 1:
        #  self.emsg = 'only one method is allowed. (%s)' % j_root
        #  return False
        return True

    #
    # parse JSON query request
    #
    def _serverParseJSON_QueryRQ(self, j_root, j_body):
        #
        # check the value of the type attribute.
        # either storage or stream is valie.
        #
        k_type = j_body.get('type')
        if k_type == None:
            self.emsg = 'type is not specified.'
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return self.doc
        elif k_type == 'storage':
            return self._serverParseJSON_FETCH(j_body)
        elif k_type == 'stream':
            return self._serverParseJSON_TRAP(j_body)
        else:
            self.emsg = 'invalid type is specified. [%s]' % type
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return self.doc

    #
    # parse JSON FETCH protocol
    #
    def _serverParseJSON_FETCH(self, j_body):
        k_limit = self._getQueryAcceptableSize(j_body)
        k_skip = self._getQueryCursor(j_body.get('cursor'))
        #
        # copy the query for the response.
        #
        keys = self._getKey_JSONList(j_body.get('key'))
        if keys == None:
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return self.doc
        j_plist = []
        j_rquery = j_body
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
                    self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_INTERNAL_ERROR, self.emsg)
                    return self.doc
                #
                # do fetch data.
                #
                j_value = []
                for i in cursor:
                    if isinstance(i['time'], datetime) == False:
                        print 'ERROR: invalid time data in the database. %s (type=%s). ignored.' % (i['time'], str(type(i['time'])))
                        continue
                    fixed_dt = datetime_naive_to_aware(i['time'], self.tzname)
                    fixed_dt = fixed_dt.astimezone(dateutil.tz.gettz(self.tzname))
                    j_value.append({
                        'time' : fixed_dt.strftime(_FIAPY_DATETIME_FORMAT),
                        'value' : i['value'] })
                    k['result'] += 1
                    total += 1
                if len(j_value) == 0:
                    j_value.append({ 'time' : '1970-01-01T00:00:00Z', 'value' : 0 })
                j_plist.append({ k['pid'] : j_value })
                if k['next'] != 0:
                    k['query']['cursor'] = k['next']
            if self.debug > 0:
                for k in keys:
                    print 'DEBUG: search key =', k
        except fiapMongo.fiapMongoException as et:
            self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_INTERNAL_ERROR, self.emsg)
            return self.doc
        #
        if total == 0:
            self.emsg = 'There is no matched point for the query.'
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_NOT_FOUND, self.emsg)
            return self.doc
        self._setJSONResponse(_FIAP_METHOD_QUERYRS, 200, 'OK', { 'query' : j_rquery, 'point' : j_plist })
        return self.doc

    #
    # parse JSON TRAP protocol
    #
    def _serverParseJSON_TRAP(self, j_query):
        self.emsg = 'TRAP protocol is not supported yet.'
        self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_NOT_IMPLEMENTED, self.emsg)
        return self.doc

    #
    # parse JSON data request
    #
    def _serverParseJSON_DataRQ(self, j_root, j_pchunk):
        if self._fixTimeInPchunk(j_pchunk) != True:
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
                self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_INTERNAL_ERROR, self.emsg)
                return self.doc
        except fiapMongo.fiapMongoException as et:
            self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
            self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_INTERNAL_ERROR, self.emsg)
            return self.doc
        #
        # response to the data request in JSON
        #
        if total == 0:
            self.emsg = 'There is no point saved.'
            self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_NOT_FOUND, self.emsg)
            return self.doc
        self.emsg = ''
        self._setJSONResponse(_FIAP_METHOD_DATARS, 200, 'OK')
        return self.doc

    #
    # convert an ISO8601 string into a datetime object.
    #
    def _fixTimeInPchunk(self, j_pchunk):
        for pid, vs in j_pchunk.iteritems():
            for v in vs:
                if v.has_key('time') == False:
                    self.emsg = 'a json key, time is not specified. (%s)' % self._tostring(i[pid])
                    self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_BAD_REQUEST, self.emsg)
                    return False
                t = fix_to_utc(v['time'], self.tzname)
                if t == None:
                    self.emsg = 'invalid time string is found. (%s)' % v['time']
                    self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_BAD_REQUEST, self.emsg)
                    return False
                v['time'] = t
        return True

    def _setJSONResponse(self, method, code, msg, add=None):
        msg = '%s %s' % (code, msg)
        if add != None:
            body = { 'response' : msg }
            for k, v in add.iteritems():
                body[k] = v
        else:
            body = { 'response' : msg }
        self.doc = { 'fiap': { 'version': _FIAPY_FIAP_VERSION, method : body }}

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
            self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return None
        except Exception as et:
            print_exception(et)
            self.emsg = 'error in JSON parser, %s' % et.message
            self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return None
        #
        # start to parse each method
        #
        handler = {
            _FIAP_METHOD_DATARQ : self._JSONtoXML_DataRQ,
            _FIAP_METHOD_DATARS : self._JSONtoXML_DataRS,
            _FIAP_METHOD_QUERYRQ : self._JSONtoXML_QueryRQ,
            _FIAP_METHOD_QUERYRS : self._JSONtoXML_QueryRS }
        e_newroot = self._parseJSON(j_root, handler)
        if e_newroot == None:
            self._setJSONResponse(_FIAP_METHOD_DATARS, _HTTP_CODE_BAD_REQUEST, self.emsg)
            return None
        self.doc = self.getXMLdoc(e_newroot)
        return self.doc

    #
    # parse JSON query request and convert to XML
    #
    # input: json root
    # output: e_newroot or None.
    #
    def _JSONtoXML_QueryRQ(self, j_root, j_body):
        e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRQ)
        attr = {}
        attr['id'] = str(uuid.uuid1())
        for k in [ 'type', 'acceptableSize', 'cursor', 'ttl', 'callbackData', 'callbackControl' ]:
            i = j_body.get(k)
            if i != None:
                attr[k] = i
        e_query = ElementTree.SubElement(e_header, '{%s}query' % NS_FIAP, attr)
        #
        # key
        #
        j_key_list = j_body.get('key')
        if j_key_list == None:
            self.emsg = 'a key is not specified. (%s)' % j_body
            return None
        for key_spec in j_key_list:
            for pid, vals in key_spec.iteritems():
                attr = {'id': pid}
                for k in [ 'attrName', 'eq', 'ne', 'lt', 'gt', 'lteq', 'gteq', 'select', 'trap' ]:
                    if vals.has_key(k) == False:
                        continue
                    attr[k] = vals.pop(k)
                if len(vals) != 0:
                    self.emsg = 'unknown json key in the key spec remains. (%s)' % vals
                    return None
                ElementTree.SubElement(e_query, '{%s}key' % NS_FIAP, attr)
        return e_newroot

    #
    # parse JSON query response and convert to XML
    #
    # input: json root
    # output: e_newroot or None.
    #
    def _JSONtoXML_QueryRS(self, j_root, j_body):
        e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRS)
        attr = {}
        j_res = j_body.pop('response')
        if 'OK' not in j_res.split():
            self._getErrorObject(e_header, 'error', j_res)
            e_res = ElementTree.SubElement(e_header, '{%s}error' % NS_FIAP)
            e_res.text = j_res
            return e_newroot
        #
        # parse each 'point'
        #
        e_res = ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
        j_point = j_body.get('point')
        if j_point == None:
            self.emsg = 'there is no point in the reponse. (%s)' % v
            return None
        for plist in j_point:
            for pid, j_vslist in plist.iteritems():
                e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': pid})
                for vs in j_vslist:
                    t = vs.get('time')
                    v = vs.get('value')
                    if t == None or v == None:
                        print 'ERROR: time or value are not specified. [%s]' % vs
                        return None
                    dt = fix_to_utc(t, self.tzname)
                    e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : dt.strftime('%Y-%m-%dT%H:%M:%S%z') } )
                    e_value.text = v
        return e_newroot

    #
    # parse JSON data request and convert to XML
    #
    # input: json root
    # output: e_newroot or None.
    #
    def _JSONtoXML_DataRQ(self, j_root, j_body):
        e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARQ)
        attr = {}
        for pid, j_vslist in j_body.iteritems():
            e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': pid})
            for vs in j_vslist:
                t = vs.get('time')
                v = vs.get('value')
                if t == None or v == None:
                    print 'ERROR: time or value are not specified. [%s]' % vs
                    self.emsg = 'time or value are not specified. [%s]' % v
                    return None
                dt = fix_to_utc(t, self.tzname)
                e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : dt.strftime('%Y-%m-%dT%H:%M:%S%z') } )
                e_value.text = v
        return e_newroot

    #
    # parse JSON data response and convert to XML
    #
    # input: json root
    # output: e_newroot or None.
    #
    def _JSONtoXML_DataRS(self, j_root, j_data):
        e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARS)
        attr = {}
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
    # parse XML binding and convert to JSON object.
    #
    # @return None in error, otherwise JSON style object.
    #
    def XMLtoJSON(self, doc):
        self._initmsg()
        try:
            e_root = ElementTree.XML(doc)
        except Exception as et:
            print_exception(et)
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
        r = self._parseXML(e_root, handler)
        if r != None:
            r['version'] = _FIAPY_FIAP_VERSION
            return json.dumps( { 'fiap' : r } )
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
        j_query = self._XMLtoJSON_QueryObject(e_query)
        return { _FIAP_METHOD_QUERYRQ : j_query }

    #
    # translate Query Object into JSON
    #
    # @return j_query a query request spec in JSON
    # @return TBD XXX in error
    #
    def _XMLtoJSON_QueryObject(self, e_query):
        j_query = {}
        for k in [ 'uuid', 'type', 'acceptableSize', 'cursor', 'ttl', 'callbackData', 'callbackConrol' ]:
            v = e_query.get(k)
            if v != None:
                j_query[k] = v
        #
        # translate Key Objects into JSON
        #
        j_query['key'] = []
        for e_key in e_query.iterfind('./fiap:key', namespaces=_NSMAP):
            pid = e_key.get('id')
            if pid == None:
                return None
            keys = {}
            for i in [ 'attrName', 'eq', 'ne', 'lt', 'gt', 'lteq', 'gteq', 'select', 'trap' ]:
                v = e_key.get(i)
                if v != None:
                    keys[i] = v
            j_query['key'].append({ pid: keys })
        return j_query

    #
    # query response method parser
    #
    def _XMLtoJSON_QueryRS(self, e_root, e_header, e_body):
        e_query = e_header.find('./fiap:query', namespaces=_NSMAP)
        if e_query == None:
            self.emsg = 'query is not specified. [%s]' % tostring(e_root)
            return None
        j_query = self._XMLtoJSON_QueryObject(e_query)
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
            self._setJSONResponse(_FIAP_METHOD_QUERYRS, _HTTP_CODE_NOT_FOUND, self.emsg)
            return self.doc
        self.doc = { _FIAP_METHOD_QUERYRS : { "response" : "OK", "query" : j_query, "point" : self._getJSONPointSpec(pset_all) } }
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
            self.emsg = 'There is no Point in the object.'
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
        j_point = {}
        for p in pset:
            pid = p.get('pid')
            t = p.get('time')
            v = p.get('value')
            if pid == None or t == None or v == None:
                print 'ERROR: pid, t or v are not specified.'
                return None
            if j_point.get(pid) == None:
                j_point[pid] = []
            tstr = datetime.isoformat(t.astimezone(dateutil.tz.gettz(self.tzname)))
            j_point[pid].append({'time':tstr, 'value':v})
        return j_point

    #
    # parse XML and process it, then response in XML.
    #
    def serverParseXML(self, doc):
        self._initmsg()
        try:
            e_root = ElementTree.XML(doc)
        except Exception as et:
            print_exception(et)
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
                    #return None
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
            return self._serverParseXML_FETCH(e_root, e_query)
        elif type == 'stream':
            return self._serverParseXML_TRAP(e_root, e_query)
        else:
            self.emsg = 'invalid type is specified. [%s]' % type
            return None

    #
    # parse XML FETCH protocol
    #
    def _serverParseXML_FETCH(self, e_root, e_query):
        k_limit = self._getQueryAcceptableSize(e_query)
        k_skip = self._getQueryCursor(e_query.get('cursor'))
        iter_keys = e_query.iterfind('./fiap:key', namespaces=_NSMAP)
        keys = self._getKey_XMLList(iter_keys)
        if keys == None:
            return None
        #
        # create a header for the response message.
        #
        e_newroot, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_QUERYRS)
        e_rquery = copy.deepcopy(e_query)
        for e in e_rquery.findall('./*'):
            e_rquery.remove(e)
        e_header.append(e_rquery)
        #
        # fetch
        #
        try:
            m = fiapMongo.fiapMongo(**_FIAPY_MONGODB)
            #
            # get points.
            #
            total = 0
            for k in keys:
                try:
                    cursor = m.iterPoint(k, k_limit, k_skip)
                except fiapMongo.fiapMongoException as et:
                    self.emsg = '%s (%s)' % (_FIAPY_EMSG_INTERNAL_ACCESS_DATA, et)
                    self._getErrorObject(e_header, 'error', self.emsg)
                else:
                    for i in cursor:
                        if isinstance(i['time'], datetime) == False:
                            print 'ERROR: invalid time data in the database. %s (type=%s). ignored.' % (i['time'], str(type(i['time'])))
                            continue
                        fixed_dt = datetime_naive_to_aware(i['time'], self.tzname)
                        e_point = ElementTree.SubElement(e_body, '{%s}point' % NS_FIAP, {'id': k['pid']})
                        e_value = ElementTree.SubElement(e_point, '{%s}value' % NS_FIAP, {'time' : fixed_dt.strftime('%Y-%m-%dT%H:%M:%S%z') } )
                        e_value.text = i['value']
                        k['result'] += 1
                        if k['next'] != 0:
                            k['query'].set('cursor', str(k['next']))
                        e_rquery.append(k['query'])
                    total += k['result']
            if self.debug > 0:
                for k in keys:
                    print 'DEBUG: search key =', k
        except fiapMongo.fiapMongoException as et:
            self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
            self._getErrorObject(e_header, 'error', self.emsg)
        #
        if total == 0:
            self.emsg = 'There is no matched point for the query.'
            self._getErrorObject(e_header, 'error', self.emsg)
        else:
            ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
        self.doc = self.getXMLdoc(e_newroot)
        return self.doc

    #
    # parse XML TRAP protocol
    #
    def _serverParseXML_TRAP(self, e_root, e_query):
        f_remove = False
        req = {}
        req['limit'] = self._getQueryAcceptableSize(e_query)
        ttl = self._getQueryTTL(e_query.get('ttl'))
        if ttl == 0:
            req['tte'] = 0
        else:
            dt = datetime.now(dateutil.tz.gettz(self.tzname)) + timedelta(seconds=ttl)
            req['tte'] = dt.astimezone(dateutil.tz.tzutc())
        iter_keys = e_query.iterfind('./fiap:key', namespaces=_NSMAP)
        req['qk'] = self._getKey_XMLList(iter_keys)
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
        except fiapMongo.fiapMongoException as et:
            self.emsg = 'An error occured when it accesses to the DB. (%s)' % et
            self._getErrorObject(e_header, 'error', self.emsg)
        else:
            ElementTree.SubElement(e_header, '{%s}OK' % NS_FIAP)
        self.doc = self.getXMLdoc(e_newroot)
        return self.doc

    #
    # check the acceptableSize and fix it if needed.
    # input: the value of acceptableSize
    # output: 1 or value or _FIAPY_MAX_ACCEPTABLESIZE
    #
    def _getQueryAcceptableSize(self, j_query):
        v_limit = j_query.get('acceptableSize')
        if v_limit == None:
            if self.debug > 0:
                print 'DEBUG: no acceptableSize is specified. set to 1'
            return 1
        try:
            v_limit = int(v_limit)
        except Exception as e:
            print 'ERROR: acceptableSize is not a number. ignored and set to 1'
            return 1
        if v_limit == 0:
            print 'ERROR: acceptableSize must not be zero. ignored and set to 1'
            return 1
        elif v_limit > _FIAPY_MAX_ACCEPTABLESIZE:
            print 'ERROR: acceptableSize must be less or equal to %d, but %d. ignored.' % (_FIAPY_MAX_ACCEPTABLESIZE, v_limit)
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
        # response to data request in XML
        #
        e_root, e_header, e_body = self.getNewXMLdoc(_FIAP_METHOD_DATARS)
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
        #
        if len(pset_all) == 0:
            self.emsg = 'There is no Point in the object.'
            self._getErrorObject(e_header, 'error', self.emsg)
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
            e_header = ElementTree.SubElement(e_tr, '{%s}header' % NS_FIAP)
            if e_root != None:
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
    # @param key_spec an iterator of JSON dict objects including keys.
    #        e.g. etree.keys or json keys.
    #
    # @return None no keys. the error message set in self.emsg
    # @return a list object specifying the query object..
    #         [ { 'pid': pid, 'an': attrName, 'op': select,
    #             'cond': { '$where' : 'condition' }, 'trap': True }, ... ]
    #
    def _getKey_JSONList(self, j_key_list):
        if j_key_list == None:
            self.emsg = 'there seems no key in the Query'
            return None
        keys = []
        for key_spec in j_key_list:
            for pid, vals in key_spec.iteritems():
                key = { 'query' : vals }
                #
                # check id.
                #
                if pid == None:
                    self.emsg = 'id attribute is not specified. [%s]' % self._tostring(vals)
                    return None
                key['pid'] = pid
                #
                # check 'attrName' and make the condition.
                # ignore other conditions if 'eq' is specified.
                #
                an = vals.get('attrName')
                if an == None:
                    self.emsg = 'an attribute is not specified.' % self._tostring(vals)
                    return None
                key['an'] = an
                #
                # create 'cond'
                #
                if an == 'time':
                    key['cond'] = self.getKeyCond(vals, fiapMongo.getKeyCondTime)
                elif an == 'value':
                    key['cond'] = self.getKeyCond(vals, fiapMongo.getKeyCondValue)
                else:
                    self.emsg = 'invalid attrName is specified. [%s]' % self._tostring(vals)
                    return None
                #
                # check 'select'
                #
                op = vals.get('select')
                if op == 'maximum':
                    key['op'] = 'max'
                elif op == 'minimum':
                    key['op'] = 'min'
                elif op != None:
                    self.emsg = 'unknown value in select is specified. [%s]' % op
                    return None
                #
                # trap
                #
                key['trap'] = False
                a = vals.get('trap')  # for event detection {changed}
                if a == 'changed':
                    key['trap'] = True
                elif a != None:
                    self.emsg = 'unknown value of select is specified. [%s]' % self._tostring(vals)
                    return None
                keys.append( key )
        return keys

    #
    # input: a list or an iterator of dict objects including keys.
    #        e.g. etree.keys or json keys.
    # output: a list object specifying the query object..
    #         [ { 'pid': pid, 'an': attrName, 'op': select,
    #             'cond': { '$where' : 'condition' }, 'trap': True }, ... ]
    #
    def _getKey_XMLList(self, iter_keys):
        if iter_keys == None:
            self.emsg = 'there seems no key in the Query'
            return None
        keys = []
        for e_key in iter_keys:
            key = { 'query' : e_key }
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
                self.emsg = 'unknown value of select is specified. [%s]' % a
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
                self.emsg = 'unknown value of select is specified. [%s]' % self._tostring(e_key)
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
    # @return pset a dict object specifying the point.
    #         {'pid':pid, 'time':utc, 'value':v}
    #
    #   time is converted into UTC.
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
            utc = fix_to_utc(timestr, self.tzname)
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

def print_exception(et):
    print 'ERROR: %s (type=%s)' % (et, str(type(et)))

#
# fiap functions
#

# #
# # print a ptv list.
# # input: { 'pid':<point id>, 'time':<time>, 'value':<value> }
# #     tzstr is a string of a timezone such as 'UTC', 'Asia/Tokyo'
# #
# def print_points(pset, tzstr='UTC'):
#     for i in pset:
#         tstr = datetime.isoformat(i['time'].astimezone(dateutil.tz.gettz(tzstr)))
#         print 'point id="%s" time="%s" value="%s"' % (i['pid'], tstr, i['value'])

#
# if the string looks a naive datetime string, replace to self.tzname.
# and it returns in UTC.
#
# input: datetime string
#
# output: datetime object in UTC

def fix_to_utc(dtstr, tzname):
    try:
        dt = dateutil.parser.parse(dtstr)
        dt = datetime_naive_to_aware(dt, tzname)
        dt = dt.astimezone(dateutil.tz.tzutc())
    except Exception as et:
        print_exception(et)
        return None
    return dt

def datetime_naive_to_aware(dt, tzname):
    if dt.tzinfo == None or dt.tzinfo.utcoffset(dt) == None:
        return dt.replace(tzinfo=dateutil.tz.gettz(tzname))
    return dt

