#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fiapMongo

def select_print(key, limit, skip):
    print 'key=', key
    print 'limit=%d, skip=%d' % (limit, skip)
    try:
        cursor = m.iterPoint(key, limit, skip)
    except Exception as e:
        print e
        exit(0)
    print 'total =', key['total']
    print 'rest  =', key['rest']
    print 'next  =', key['next']
    for i in cursor:
        print '%s %s' % (i['time'], i['value'])
    cursor.close()
    print

#
# main
#

#
# limit, skip
#
m = fiapMongo.fiapMongo(port=27036)

key = {}
key['pid'] = 'http://example.org/fiapy/test/p01'
key['next'] = 0
key['rest'] = 0
k_limit = 2
while True:
    select_print(key, k_limit, key['next'])
    if key['rest'] == 0:
        break

#
# max and min
#
keys = [
    'http://example.org/fiapy/test/p02',
    'http://example.org/fiapy/test/p03'
    ]

key = {}
for k in keys:
    key = {'pid':k, 'an':'value', 'op':'max'}
    select_print(key, 0, 0)

key = {}
for k in keys:
    key = {'pid':k, 'an':'value', 'op':'min'}
    select_print(key, 0, 0)

#
# test for condition (!= eq)
#
key = {}
key['cond'] = { '$where' : 'this.value <= 1300 &&  this.value >= 1200' }
key['pid'] = 'http://example.org/fiapy/test/p01'
select_print(key, 0, 0)

#
# test for condition (== eq)
#
key = {}
key['value'] = '1274'
key['cond'] = { '$where' : 'this.value == 1244' }
key['pid'] = 'http://example.org/fiapy/test/p01'
select_print(key, 0, 0)

