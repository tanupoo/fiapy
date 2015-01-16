Certitificate Generation
========================

This memo describes the way to create the X.509 certificate by openssl command
for the IEEE1888 server/client.
The text includes how to create a certificate signing request (CSR)
and to sign it by CA.

## component's certificate generation

This section describes the way to generate **a self-signed certificate**.
The certificates created in this section could be used to create a TLS session.
However, the issuer in the certificate is identical to the subject name.
It means that no one guarantee the public key in the certificate.
If you don't trust the peer directly, you don't use such certificates.
You have to create a certificate signed by a trust point (e.g. CA).
Skip this section for that.

- create a configuration file of openssl.

this is a request for the component name, comp001.test.gutp.jp.
the component role is both app and storage.
belonging to test.gutp.jp.

~~~~
    % cat comp001-req.conf
    [req]
    distinguished_name = req_distinguished_name
    x509_extensions = v3_req
    prompt = no
    [req_distinguished_name]
    C = JP
    ST = Tokyo
    L = Hongo
    O = GUTP
    OU = OPWG
    CN = comp001.test.gutp.jp
    [v3_req]
    keyUsage = keyEncipherment, dataEncipherment
    extendedKeyUsage = serverAuth, clientAuth
    subjectAltName = @alt_names
    [alt_names]
    DNS.1 = app001.hongo.test.gutp.jp
    DNS.2 = storage001.hongo.test.gutp.jp
~~~~

this is a request for the component comp002.test.gutp.jp which is a GW.

~~~~
    % cat comp002-req.conf
    [req]
    distinguished_name = req_distinguished_name
    x509_extensions = v3_req
    prompt = no
    [req_distinguished_name]
    C = JP
    ST = Tokyo
    L = Hongo
    O = GUTP
    OU = OPWG
    CN = comp002.test.gutp.jp
    [v3_req]
    keyUsage = keyEncipherment, dataEncipherment
    extendedKeyUsage = serverAuth, clientAuth
    subjectAltName = @alt_names
    [alt_names]
    DNS.1 = gw001.hongo.test.gutp.jp
~~~~

- generate a certificate request.

~~~~
    % openssl req -x509 -nodes -days 730 -newkey rsa:2048 -keyout comp001-cert.pem -out comp001-cert.pem -config comp001-req.conf
    Generating a 2048 bit RSA private key
    ........................................................................+++
    ........................................................................+++
    writing new private key to 'cert.pem'
    -----
~~~~

generate the request for comp002 as well.

## Prerequisite: CA's certificate and private key generation

To sign a client's or server's certificate,
you need to setup the certificate and the private key of your authority.
It's typically called CA.

generate the password to handle the CA's private key.

**DON'T DO THIS AS IT IS**.  you have to use your own password.

~~~~
    % echo hogehoge | openssl passwd -stdin > testCA-pwd.txt
~~~~

see testCA-pwd.txt if your password has been stored.

~~~~
    % cat testCA-pwd.txt
    4KbyL6jKLkSI.
~~~~

generate the CA's private key.

~~~~
    % openssl genrsa -aes128 -out testCA-privkey.pem -passout file:testCA-pwd.txt 2048
    Generating RSA private key, 2048 bit long modulus
    ...........+++
    ....................................................................................................................+++
    e is 65537 (0x10001)
~~~~

generate the CA's certificate into testCA-cert.pem.

~~~~
    % openssl req -new -x509 -days 730 -passin file:testCA-pwd.txt \
        -key testCA-privkey.pem -out testCA-cert.pem \
        -subj '/C=JP/ST=Tokyo/L=Hongo/CN=testca.gutp.jp'
~~~~

For your information:
By the following command,
you could generate the CA's private key and certificate in same time.
But, this command encrypts the private key by 3DES-CBC by default.
please carefully use it if you like.

~~~~
    % openssl req -new -x509 -newkey rsa:2048 -days 730 \
        -passout file:testCA-pwd.txt -out testCA-cert.pem \
        -keyout testCA-privkey.pem \
        -subj '/C=JP/ST=Tokyo/L=Hongo/CN=ca.test.gutp.jp'
~~~~

see testCA-cert.pem if the CA's private key has been stored.

~~~~
    % openssl x509 -in testCA-cert.pem -noout -text
~~~~

see testCA-privkey.pem.  it's encoded by PEM format.

~~~~
    % cat testCA-privkey.pem
    -----BEGIN RSA PRIVATE KEY-----
    Proc-Type: 4,ENCRYPTED
    DEK-Info: AES-128-CBC,A63B1E6C6EACE9B57480CC055ED0AE63

    morDBiDNbfUC53WBNdGXpglZM8VO22hNm+UFLRrC0vHfynnhT6Is69ToDEQz8/sE
    IgYLztZB3N1JJnsyVJkOZExWM5zqHhBhY1MpZfnsiVBqQXlwnOuhb+nMZ+VkzN8X
    3/2XPC+bPcklSIUPGvZaYDjYXgRzcYdMVDnrry7GHFCeCp2hwEsfOlC7ulIrqPn4
    	: (snip)
    nvD3GJEsVBNTR84hBUT4tovdgIJ/cTZ6+qF2nNC6nByZvV0zubXTELnM5dlZ9jxG
    xO8f6EC5uQLJSGSczKKfQfFkLhP0zIJhKGAfmposX+YftCjGVeUR069IJkg4Jdw2
    ArHs4nA9xCl/K/DOj7QEko5jC2ACAy9PDppHWWd8M0RmT5DvRn6FpppR736/w+dU
    -----END RSA PRIVATE KEY-----
~~~~

## component's certificate request generation

in order to create CSR by the openssl command,
you have to create the configuration file for each component.
creation comp001-req.conf and comp002-req.conf,
please refer to the previous section.

After getting the configuration files, you have to create CSR,
generate the comp001's private key and CSR.

~~~~
    % openssl req -new -nodes -days 730 -newkey rsa:2048 -keyout comp001-privkey.pem -out comp001-req.pem -config comp001-req.conf
~~~~

generate the comp002's private key and CSR as well.

~~~~
    % openssl req -new -nodes -days 730 -newkey rsa:2048 -keyout comp002-privkey.pem -out comp002-req.pem -config comp002-req.conf
~~~~

## signing a CSR and generating a signed certificate.

~~~~
    openssl x509 -req \
        -CA testCA-cert.pem -CAkey testCA-privkey.pem \
        -passin file:testCA-pwd.txt \
        -set_serial 1 -in comp001-req.pem -out comp001-signedcert.pem \
        -extfile comp001-req.conf -extensions v3_req
~~~~

see comp001-signedcert.pem.
the issuer is the CA and the subject name is the component 001.
subject alternative names exist.

~~~~
    % openssl x509 -in comp001-signedcert.pem -noout -text
    Certificate:
        Data:
            Version: 3 (0x2)
            Serial Number: 1 (0x1)
            Signature Algorithm: sha1WithRSAEncryption
            Issuer: C=JP, ST=Tokyo, L=Hongo, CN=ca.test.gutp.jp
            Validity
                Not Before: Jan 15 23:44:53 2015 GMT
                Not After : Feb 14 23:44:53 2015 GMT
            Subject: C=JP, ST=Tokyo, L=Hongo, O=GUTP, OU=OPWG, CN=comp001.test.gutp.jp
            Subject Public Key Info:
                Public Key Algorithm: rsaEncryption
                RSA Public Key: (2048 bit)
                    Modulus (2048 bit):
                        00:bf:65:91:52:56:74:46:30:60:15:c7:0b:d9:e7:
                        1a:fc:bc:b6:3a:61:08:23:fe:b6:11:18:a9:f0:72:
                        f0:e4:77:a4:c9:a2:b5:1f:39:29:a0:9d:8a:87:17:
                        0f:e7:b2:6a:ea:77:b8:40:8d:a4:6a:40:bb:47:93:
                        30:50:a4:74:8d:f7:93:5e:99:88:7c:29:0f:1a:34:
                        5d:dd:3b:73:19:ad:88:2a:eb:9c:30:cf:f8:71:04:
                        7b:b2:bd:3e:b8:a1:0a:6c:1b:a3:00:10:85:32:27:
                        8e:47:f1:d9:b7:0d:ef:30:98:c5:af:1b:23:dc:a2:
                        65:4a:53:03:69:68:dd:ef:83:9f:0a:f5:c4:8b:24:
                        8c:ab:1c:8b:2e:2c:db:32:9d:fa:14:62:11:24:ec:
                        8b:0d:1b:05:4d:28:6a:11:e0:10:82:df:2c:1a:e8:
                        f9:16:1f:9d:c8:8f:bb:9c:af:eb:36:12:6c:da:af:
                        5e:f7:55:1c:4f:ff:9c:32:89:84:7d:13:77:bc:89:
                        f0:89:4c:e1:49:16:77:42:d3:e6:a7:86:e0:20:26:
                        31:ab:c9:70:d9:b7:3a:8f:17:66:68:24:f1:3f:3d:
                        38:68:5e:07:77:17:11:77:a2:96:75:b4:38:2b:63:
                        03:8b:ec:e6:b8:41:ca:90:10:ad:db:70:4b:ee:e5:
                        3d:9f
                    Exponent: 65537 (0x10001)
            X509v3 extensions:
                X509v3 Key Usage: 
                    Key Encipherment, Data Encipherment
                X509v3 Extended Key Usage: 
                    TLS Web Server Authentication, TLS Web Client Authentication
                X509v3 Subject Alternative Name: 
                    DNS:app001.hongo.test.gutp.jp, DNS:storage001.hongo.test.gutp.jp
        Signature Algorithm: sha1WithRSAEncryption
            44:72:95:05:e4:13:2f:0d:3f:b8:46:9f:09:46:1f:c4:00:07:
            75:49:c3:0b:63:00:c1:9c:1d:7d:45:1a:5a:f3:5c:39:58:e8:
            f6:b8:57:e5:a1:94:82:95:fe:f0:0b:37:c3:02:50:75:b1:85:
            1f:41:50:61:aa:67:1b:3a:d9:ee:4b:8b:c2:e7:83:7c:d0:c8:
            bd:d5:4b:0b:c2:6f:ef:a1:ae:9d:3b:75:7c:c5:f7:7d:d8:06:
            b0:49:47:60:81:9f:3b:7a:c5:7c:fc:ff:c3:00:29:d3:5d:c7:
            a3:6b:1b:df:16:5a:77:24:c2:97:89:21:a1:d6:b3:b2:2b:dd:
            d2:c4:5d:b9:e2:88:f1:6c:ba:ff:df:4f:72:42:5b:56:ff:a5:
            ea:74:5d:37:45:b9:22:33:f2:d8:e6:ed:69:ca:46:84:33:4c:
            6a:a5:0a:be:1c:4e:36:f2:2c:46:ef:6a:f8:c3:ed:5f:2d:f5:
            ba:28:d7:63:63:05:8f:a3:7c:20:7b:70:4d:b2:81:7e:35:c7:
            be:08:46:5f:74:6f:a4:d4:89:c2:98:b7:ca:f8:07:ae:50:22:
            ee:73:92:b5:4f:8c:ff:48:ed:48:30:05:cb:93:da:fa:79:bb:
            3f:46:0f:f2:5c:de:b9:13:0b:bb:61:65:b3:7c:56:6f:54:59:
            04:58:df:ed
~~~~

sign the request of comp002 as well.

~~~~
    openssl x509 -req \
        -CA testCA-cert.pem -CAkey testCA-privkey.pem \
        -passin file:testCA-pwd.txt \
        -set_serial 1 -in comp002-req.pem -out comp002-signedcert.pem \
        -extfile comp002-req.conf -extensions v3_req
~~~~

----
## TIPS

### another way to create a request with subjectAltName and sign it by CA.

you can pass a string defined by an environment variable into the openssl.conf.
for example, the openssl.conf has a line like below:

~~~~
    subjectAltName = $ENV::SAN
~~~~

and, then use the following command.

~~~~
    SAN="DNS:hoge.jp,email:admin@fiap.gutp.jp" \
    openssl req -new -newkey rsa:2048 \
        -keyout privkey.pem -passout pass:pwd.txt -out new-req.pem \
        -config openssl.conf -subj '/C=JP/ST=Tokyo/L=Hongo/CN=gw1.gutp.jp'

    SAN="DNS:hoge.jp,email:admin@fiap.gutp.jp" \
    openssl x509 -req -CA testCA-cert.pem -passin file:testCA.pwd \
        -set_serial 1 -in new-req.pem -out new-cert.pem \
        -extfile openssl.conf -extensions v3_req
~~~~

See http://cmrg.fifthhorseman.net/wiki/SubjectAltName
