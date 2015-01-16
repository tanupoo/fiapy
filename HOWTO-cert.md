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
    keyUsage = keyEncipherment, digitalSignature, keyAgreement
    extendedKeyUsage = serverAuth, clientAuth
    subjectAltName = @alt_names

    [alt_names]
    DNS.1 = comp001.test.gutp.jp
    DNS.2 = app001.hongo.test.gutp.jp
    DNS.3 = storage001.hongo.test.gutp.jp
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
    keyUsage = keyEncipherment, digitalSignature, keyAgreement
    extendedKeyUsage = serverAuth, clientAuth
    subjectAltName = @alt_names

    [alt_names]
    DNS.1 = comp002.test.gutp.jp
    DNS.2 = gw001.hongo.test.gutp.jp
~~~~

- generate a certificate request.

~~~~
    % openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
        -keyout comp001-cert.pem -out comp001-cert.pem -config comp001-req.conf
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
    % openssl genrsa -aes128 \
        -out testCA-privkey.pem -passout file:testCA-pwd.txt 2048
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
    % openssl req -new -nodes -days 730 -newkey rsa:2048 \
        -keyout comp001-privkey.pem -out comp001-req.pem \
        -config comp001-req.conf
~~~~

generate the comp002's private key and CSR as well.

~~~~
    % openssl req -new -nodes -days 730 -newkey rsa:2048 \
        -keyout comp002-privkey.pem -out comp002-req.pem \
        -config comp002-req.conf
~~~~

## signing a CSR and generating a signed certificate.

~~~~
    % openssl x509 -req \
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
            Issuer: C=JP, ST=Tokyo, L=Hongo, CN=testca.gutp.jp
            Validity
                Not Before: Jan 16 15:31:49 2015 GMT
                Not After : Feb 15 15:31:49 2015 GMT
            Subject: C=JP, ST=Tokyo, L=Hongo, O=GUTP, OU=OPWG, CN=comp001.test.gutp.jp
            Subject Public Key Info:
                Public Key Algorithm: rsaEncryption
                RSA Public Key: (2048 bit)
                    Modulus (2048 bit):
                        00:d8:c6:7a:ef:81:8d:17:79:15:a0:4f:06:d2:dd:
                        e3:3c:80:1b:d2:46:f5:59:38:e0:f3:b0:29:d9:f7:
                                : (snip)
                        82:33:42:b3:ef:1c:56:ff:20:de:57:e6:9f:b0:ea:
                        18:3f:77:01:9e:76:06:16:c9:b2:d6:83:f7:26:ce:
                        0b:1d
                    Exponent: 65537 (0x10001)
            X509v3 extensions:
                X509v3 Key Usage: 
                    Digital Signature, Key Encipherment, Key Agreement
                X509v3 Extended Key Usage: 
                    TLS Web Server Authentication, TLS Web Client Authentication
                X509v3 Subject Alternative Name: 
                    DNS:comp001.test.gutp.jp, DNS:app001.hongo.test.gutp.jp, DNS:storage001.hongo.test.gutp.jp
        Signature Algorithm: sha1WithRSAEncryption
            22:f2:5c:b8:e3:c8:2a:b1:21:76:7d:c9:18:b4:5c:2d:7c:e1:
            1a:b3:69:17:21:58:eb:44:b9:6f:fb:ea:b1:52:2a:8a:a8:e1:
                                : (snip)
            32:6d:dc:19:02:a2:30:3c:d0:49:40:da:69:fa:15:63:be:d9:
            40:0c:95:5f
~~~~

sign the request of comp002 as well.

~~~~
    % openssl x509 -req \
        -CA testCA-cert.pem -CAkey testCA-privkey.pem \
        -passin file:testCA-pwd.txt \
        -set_serial 1 -in comp002-req.pem -out comp002-signedcert.pem \
        -extfile comp002-req.conf -extensions v3_req
~~~~

----
## TIPS

### KeyUsage extensions

If you see the follow error during the TLS negotiation,
you can check the key usage extensions in your certificate.

~~~~
[SSL: SSLV3_ALERT_UNSUPPORTED_CERTIFICATE] sslv3 alert unsupported certificate (_ssl.c:581)
~~~~

According to the discussion about
[Extensions for SSL server certificate](http://security.stackexchange.com/questions/26647/extensions-for-ssl-server-certificate/26650#26650),
three entries in the key usage are required.

~~~~
keyUsage = keyEncipherment, digitalSignature, keyAgreement
~~~~

For more information:
- About openssl key usage: [X509 V3 certificate extension configuration format](https://www.openssl.org/docs/apps/x509v3_config.html)
- [Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile](http://tools.ietf.org/html/rfc5280)

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
