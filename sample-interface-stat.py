#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import shlex
import re
import json

from datetime import datetime
import pytz
TZ='Asia/Tokyo'

args1 = shlex.split('/usr/sbin/netstat -inb')
args2 = shlex.split('grep -v Link')

p1 = subprocess.Popen(args1, stdout=subprocess.PIPE)
p2 = subprocess.Popen(args2, stdin=p1.stdout, stdout=subprocess.PIPE)

pid_base = 'http://tanu.org/mac/if'

req = { 'fiap' : '20140401', 'dataRQ' : [] }
time = datetime.now(pytz.timezone(TZ)).strftime('%Y-%m-%dT%H:%M:%S%z')

for line in p2.stdout:
  p = re.split('\s+', line)
  if '.' in p[3]:
    fiap_name = '%s/%s/ibytes' % (pid_base, p[0])
    value = str(p[6])
    req['dataRQ'].append({ fiap_name : [ {'time': time, 'value': str(value) } ] })

    fiap_name = '%s/%s/obytes' % (pid_base, p[0])
    value = str(p[9])
    req['dataRQ'].append({ fiap_name : [ {'time': time, 'value': str(value) } ] })

print json.dumps(req)

