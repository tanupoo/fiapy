#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import shlex
import re
import json
import dateutil.parser, dateutil.tz
from datetime import datetime

TZ='Asia/Tokyo'

args1 = shlex.split('/usr/sbin/netstat -inb')
args2 = shlex.split('grep -v Link')

p1 = subprocess.Popen(args1, stdout=subprocess.PIPE)
p2 = subprocess.Popen(args2, stdin=p1.stdout, stdout=subprocess.PIPE)

pid_base = 'http://fiap.tanu.org/mac/if'

req = { 'fiap': { 'version': '20140401', 'dataRQ' : {} } }
time = datetime.now()
time = time.replace(tzinfo=dateutil.tz.gettz(TZ)).strftime('%Y-%m-%dT%H:%M:%S%z')

for line in p2.stdout:
  p = re.split('\s+', line)
  if '.' in p[3]:
    dataRQ = {}
    # ibytes
    fiap_name = '%s/%s/ibytes' % (pid_base, p[0])
    value = str(p[6])
    dataRQ[fiap_name] = [ {'time': time, 'value': str(value) } ]

    fiap_name = '%s/%s/obytes' % (pid_base, p[0])
    value = str(p[9])
    dataRQ[fiap_name] = [ {'time': time, 'value': str(value) } ]

    req['fiap']['dataRQ'] = dataRQ

print json.dumps(req)

