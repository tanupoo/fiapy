#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json

class fiapConfig():

    debug = 0
    ciphers = 'ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256'
    key_file = None
    cert_file = None
    ca_certs = None
    cert_request = False     # if set, send a CR even if ca_path set.
    security_level = False
    acl = None
    acl_san_wildcard = None

    def __init__(self, cfile, security_level=0, debug=0):
        self.security_level = security_level
        self.debug = debug
        if cfile:
            self._parse_config_file(cfile)
        return

    def _parse_config_file(self, cfile):
        try:
            jc = json.load(open(cfile))
        except ValueError as e:
            msg = 'ERROR: JSON parse error in %s: %s' % (cfile, e)
            if self.debug > 0:
                print msg
            raise ValueError(msg)
        if self.security_level and jc.get('security'):
            cf_sec = jc['security']
            self.security_level = cf_sec.get('level')
            if security_level > self.security_level:
                self.security_level = security_level
            if cf_sec.get('ciphers'):
                self.ciphers = cf_sec.get('ciphers')
            self.key_file = cf_sec.get('key_file')
            self.cert_file = cf_sec.get('cert_file')
            self.ca_certs = cf_sec.get('ca_certs')
            self.ca_path = cf_sec.get('ca_path')
            #
            # currently, it always sends the CR.
            #
            self.cert_request = True
            #
            if cf_sec.get('acl'):
                self.acl = cf_sec['acl']
                if self.debug > 2:
                    print 'access control list:'
                for san, acl in cf_sec['acl'].iteritems():
                    if san == '*':
                        self.acl_san_wildcard = acl
                    if self.debug > 2:
                        print '  san=', san
                        for pid, mlist in acl.iteritems():
                            print '    pid=', pid
                            for method, action in mlist.iteritems():
                                print '      ', method, action
        return

    def check_acl_san(self, cert):
        if not cert:
            print 'ERROR: cert of the peer does not exist'
            raise CertificateValidationError()
        if self.debug > 2:
            print 'DEBUG: peers_cert=', cert
        #
        # pick valid SAN, (DNS and rfc822)
        #
        sans = []
        for k, v in cert['subjectAltName']:
            if self.debug > 0:
                print 'DEBUG: SAN=', k, v
            if k in ['DNS', 'email']:
                sans.append(v)
        if not self.acl:
            if self.debug > 2:
                print 'DEBUG: no ACL section in the config'
            return True
        #
        # check acl
        #
        for san_cert in sans:
            for san, acl in self.acl.iteritems():
                if san == '*':
                    continue
                if san == san_cert:
                    #
                    # accept or reject it in this phase.
                    # it should be check at check_acl_method() later.
                    #
                    return self._check_acl_san_wildcard(acl)
        return self._check_acl_san_wildcard(self.acl_san_wildcard)

    def _check_acl_san_wildcard(self, a):
        if not a:
            return True # XXX TBD
        if len(a) == 1 and a.has_key('*'):
            if len(a['*']) == 1 and a['*'].has_key('*'):
                if a['*']['*'] == 'reject':
                    return False
        return True

    def check_acl_method(self, cert):
        pass
