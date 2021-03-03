#!/usr/bin/env python
##ImmunityHeader v1
###############################################################################
## File       :  libkrb5.py
## Description:
##            :
## Created_On :  Mon Jan 5.10:30:39.CET.2015
## Created_By :  X.
##
## (c) Copyright 2010, Immunity, Inc. all rights reserved.
###############################################################################

import sys
import os
import tempfile
import struct
import logging

if '.' not in sys.path:
    sys.path.append('.')

try:
    from pyasn1.type import univ, tag
    from pyasn1.codec.ber import decoder,encoder
except ImportError:
    logging.error("libkrb5: Cannot import pyasn1 (required)")
    raise

try:
    from libs.newsmb.Struct import Struct
    from libs.newsmb.libgssapi import GSS_KRB5, asn1_encode
except ImportError:
    logging.error("libkrb5: Cannot import newsmb components (required)")
    raise

try:
    from libs.kerberos.protocol import Kerberos, Convert2PrincipalType, Convert2ServiceAndInstanceType
except ImportError:
    logging.error("libkrb5: Cannot import kerberos components (required)")
    raise

KRB5_NEGOTIATE_MESSAGE    = 0x00000001
KRB5_CHALLENGE_MESSAGE    = 0x00000002
KRB5_AUTHENTICATE_MESSAGE = 0x00000003

class KRB5Exception(Exception):
    pass

class KRB5Negotiate(Struct):
    st = [
        ['Krb5Oid'                 , '0s', ''],
        ['MessageType'             , '<H', KRB5_NEGOTIATE_MESSAGE],
        ['ApReq'                   , '0s', ''],
    ]

    def __init__(self, data = None, apreq=''):
        Struct.__init__(self, data)

        if data is not None:
            raise RuntimeError, "Not implemented."
        else:
            oid = encoder.encode(univ.ObjectIdentifier(GSS_KRB5))
            self['Krb5Oid'] = asn1_encode(0x60, oid)
            self['ApReq'] = apreq

    def pack(self):
        data = self['Krb5Oid']
        data += Struct.pack(self)
        data += self['ApReq']
        # Mandatory temporary patch!
        # We need to find a way to do it automatically using pyasn1
        d2 = data[0] + '\x82' + struct.pack('>H', len(data[2:])) + data[2:]
        return d2

class KRB5:
    def __init__(self, UserName = None, Password = None, DomainName = None, TargetHostname=None, DbName=None, Integrity = True, Confidentiality = True):

        if UserName == None:
            UserName = ''
        self.UserName = UserName.encode('ASCII')
        if Password == None:
            Password = ''
        self.Password = Password.encode('ASCII')
        if DomainName == None:
            DomainName = ''
        self.DomainName = DomainName.encode('ASCII').lower()
        self.DbName = DbName
        self.TargetHostname = TargetHostname
        self.TargetDNS = TargetHostname + '.' + self.DomainName
        self.ExportedSessionKey = None

    def negotiate(self, data = None):

        client_principal = Convert2PrincipalType(self.UserName, self.DomainName)
        auth_principal = Convert2ServiceAndInstanceType('krbtgt/'+self.DomainName, self.DomainName)
        cifs_principal = Convert2ServiceAndInstanceType('cifs/' + self.TargetDNS, self.DomainName)

        krb = Kerberos(self.DomainName, tcp=0)
        krb.set_credentials(self.UserName, self.Password)
        krb.open_db(self.DbName, client_principal)

        if not krb.do_auth(client_principal, auth_principal, with_db=1):
            logging.debug("libkrb5.negotiate() failed.")
            return ''

        if not krb.get_ticket_service(client_principal, cifs_principal, with_db=1):
            return ''

        krb.save_db()
        apreq = krb.build_apreq_from_credential_db(cc=None,
                                                   service_principal=cifs_principal,
                                                   generate_subkey=True)

        self.ExportedSessionKey = krb.get_subkey()[1]
        packet = KRB5Negotiate(apreq=apreq[1])
        return packet.pack()

if __name__ == '__main__':
    print 'N/A'