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
    for i in pchunk:
      pid = i.keys()[0]
      total += len(i[pid])
      try:
        self.db[pid].insert(i[pid])
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
  #   { 'pid': pid, 'an': attrName, 'op': 'max'|'min',
  #     'cond': { '$where' : 'condition' }, 'trap': True }
  #   k_limit == 0 means no limitation for query result.
  #
  # output: cursor and set below key:value in the key.
  #   key['count']
  #   key['rest']
  #   key['result'] = 0
  #
  def iterPoint(self, key, k_limit, k_skip):
    pid = key['pid']
    cond = key['cond']
    cursor = self.db[pid].find(cond)
    if k_skip != 0:
      cursor = cursor.skip(k_skip)
    if k_limit != 0:
      cursor = cursor.limit(k_limit)
    if key['op'] == 'max':
      cursor = cursor.sort([(key['an'],pymongo.DESCENDING)]).limit(1)
    elif key['op'] == 'min':
      cursor = cursor.sort([(key['an'],pymongo.ASCENDING)]).limit(1)
    elif key['op'] != None:
      raise fiapMongoException('invalid op (%s) is specified' % key['op'])
    key['count'] = cursor.count()
    key['rest'] = key['count'] - k_skip - k_limit
    key['rest'] = 0 if key['rest'] < 0 else key['rest']
    key['result'] = 0
    return cursor

#
# input: a ISO8601 time string.
# output: a string for javascript time comparison.
#
def getKeyCondTime(timestr, op):
  fmt_isodate = 'ISODate("%Y-%m-%dT%H:%M:%SZ")'
  if len(timestr) != 0:
    raise fiapMongoException('null time string is specified.')
  try:
    dt = dateutil.parser.parse(timestr)
  except Exception as et:
    raise fiapMongoException(et)
  return ' this.time %s %s' % (op, dt.astimezone(pytz.timezone('UTC')).strftime(fmt_isodate))

#
# dummy
#
def getKeyCondValue(str, op):
  pass

if __name__ == '__main__' :
  m = fiapMongo(port=27036)
  keys = {'num':{'$gt':10}}
  for i in m.getPoint(keys, 0, 0):
    print i
