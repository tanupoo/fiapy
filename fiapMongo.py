#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import pymongo
import dateutil.parser
import pytz

class fiapMongoException():
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class fiapMongo():

    def __init__(self, host='127.0.0.1', port=27017):
        try:
            self.db = MongoClient(host=host, port=port).fiap
        except Exception as et:
            raise fiapMongoException(et)

    #
    # insert a chunk of data.
    #
    # input: point list and the chunk
    #      = [ { <point id> : [ { 'time': time, 'value' : value }, {...} ] }, {...} ]
    # output: the number of the data recorded.
    #
    def insertPointChunk(self, pchunk):
        total = 0
        for pid, vs in pchunk.iteritems():
            total += len(vs)
            try:
                self.db[pid].insert(vs)
            except Exception as et:
                raise fiapMongoException(et)
        return total

    #
    # insert data one by one.
    #
    # input: point list
    #      = [ { 'pid': pointID, 'time': time, 'value' : value }, {...} ]
    # output: the number of the data recorded.
    #
    def insertPointList(self, plist):
        total = 0
        for i in plist:
            pid = i['pid']
            time = i['time']
            value = i['value']
            try:
                self.db[pid].insert({'time':time, 'value':value})
                total += 1
            except Exception as et:
                raise fiapMongoException(et)
        return total

    #
    # psid = <PointSet ID>
    # pset = [ { <PointSet> : 'ps'}, { <Point> : 'p' }, ... ]
    #
    def insertPointSet(self, psid, pset):
        ps = []
        for i in pset:
            k, v = i
            ps.append({k: v})
        try:
            self.db[psid].insert({'set': ps})
        except Exception as et:
            raise fiapMongoException(et)
        return True

    #
    # input:
    #
    def saveTrap(self, req):
        try:
            self.trap.save(req)
            return True
        except Exception as et:
            raise fiapMongoException(et)

    #
    # input:
    #
    def removeTrap(self, req):
        try:
            self.trap.remove(req)
            return True
        except Exception as et:
            raise fiapMongoException(et)

    #
    # input: key, limit, skip
    #   key = {
    #     'pid': pid,
    #     'cond': { '$where' : 'condition' },
    #     'an': attrName,
    #     'op': None | 'max' | 'min',
    #     'trap': True
    #   }
    #
    #   cond: optional
    #   trap: optional
    #
    #   limit is as an acceptableSize.  it's set to the limit of find().
    #   limit == 0 means no limitation for query result.
    #   skip is as the value of a cursor.
    #
    # output: cursor and set below key:value in the key.
    #   key['total']: the number of total data without both limit and skip.
    #   key['next']: the number to be skipped for the next query.
    #                key['total'] == key['skip'] means that the result
    #                of the query includes all data.
    #   key['rest']: the remained data after this query.
    #   key['result']: initialize to 0
    #
    def iterPoint(self, key, k_limit, k_skip):
        key['total'] = 0
        key['result'] = 0
        #
        # check 'pid'
        #
        if key.has_key('pid') == False:
            raise fiapMongoException('pid must be specified.')
        pid = key['pid']
        #
        # check 'cond'
        #
        cond = key.get('cond')
        if cond == None:
            cond = {}
        #
        # create cursor
        #
        cursor = self.db[pid]
        op = key.get('op')
        if op == 'max':
            cursor = cursor.find(cond, limit=k_limit).sort(key['an'],pymongo.DESCENDING)
            key['total'] = 1
            key['rest'] = 0
            key['next'] = 0
            return cursor
        elif op == 'min':
            cursor = cursor.find(cond, limit=k_limit).sort(key['an'],pymongo.ASCENDING)
            key['total'] = 1
            key['rest'] = 0
            key['next'] = 0
            return cursor
        elif op != None:
            raise fiapMongoException('invalid op (%s) is specified' % op)
        #
        # in the case with no 'op'
        #
        # XXX needed ?
        #key['total'] = cursor.find(cond).count()
        cursor = cursor.find(cond, limit=k_limit, skip=k_skip)
        #
        # set additional information
        #
        key['rest'] = key['total'] - k_skip - k_limit
        key['next'] = key['total'] - key['rest']
        if key['rest'] <= 0:
            key['rest'] = 0 if key['rest'] < 0 else key['rest']
            key['next'] = 0
        return cursor

#
# input: a ISO8601 time string.
# output: a string for javascript time comparison.
#
def getKeyCondTime(timestr, op):
    fmt_isodate = 'ISODate("%Y-%m-%dT%H:%M:%SZ")'
    if len(timestr) == 0:
        raise fiapMongoException('null time string is specified.')
    try:
        dt = dateutil.parser.parse(timestr)
    except Exception as et:
        raise fiapMongoException('invalid time string (%s)' % et)
    return ' this.time %s %s' % (op, dt.astimezone(pytz.timezone('UTC')).strftime(fmt_isodate))

#
# dummy
#
def getKeyCondValue(str, op):
    return ' this.value %s %s' % (op, str)

if __name__ == '__main__' :
    m = fiapMongo(port=27036)
    keys = {'num':{'$gt':10}}
    for i in m.getPoint(keys, 0, 0):
        print i
