#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json

class fiapTools():
    def __init__(self, f_debug=0):
        self.f_debug = f_debug
        pass

def parse_config_file(cfile):
    ca_args = {}
    if cfile != None:
        try:
            jc = json.load(open(cfile))
        except ValueError as e:
            print 'ERROR: JSON parse error in %s: %s', (cfile, e)
            exit(1)
        if jc.get('security'):
            ca_args['key_file'] = jc['security']['key_file']
            ca_args['cert_file'] = jc['security']['cert_file']
            ca_args['ca_certs'] = jc['security']['ca_certs']
    return ca_args
