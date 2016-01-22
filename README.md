fiapy
=====

## What's it ?

[IEEE1888](http://standards.ieee.org/findstds/standard/1888-2014.html) is a set of protocol to exchange amount of time series data between two nodes.

This is an IEEE1888 implementation written in python.
A part of IEEE1888.3 security is supported.
WRITE and FETCH protocols for both client and server are supported.
TRAP protocol is under developing.
REGISTER and LOOKUP are not supported.

Experimentaly, it supports:

- JSON format.
- translation between XML and JSON, vice versa.
- RESTful interface.

For more detail about this features,
see [JSON-data-model.md](https://github.com/tanupoo/fiapy/blob/master/doc/JSON-data-model.md)

### fiapy.py

It's an IEEE1888 server implementation.
To run it, you can simply type like below:

    ~~~~
    % fiapy.py
    ~~~~

The default port number is 18880.
If you want to see the debug message, you add "-d (number)" into the parameter.
Using "-d 2" will show verbose messages.

If you want to use the IEEE1888.3 security,
you have to add "-s" option with the security level.

    ~~~~
    % fiapy.py -s 2
    ~~~~

The default port number is 18883.

It's not allowed to use both secure and non-secure mode in same time.
If you want to run secure and non-secure severs, you have to run both.

To get a latest value of the key, you can get it like below.

    ~~~~
    wget -t 1 -q -O - 'http://localhost:18880/?k=http://example.org/fiapy/test/p03&k=http://example.org/fiapy/test/p01'
    ~~~~

### fiapc.py

It's an IEEE1888 client implementation.
It reads a request from the standard input or a file with -f option.
By default, it send a request in JSON format and prints the result in JSON format.
If you provide a file in XML format, it automatically translates into JSON.

For example, to send a FETCH request in JSON,

~~~~
% fiapc.py -e http://fiap.example.org/storage -f fetch.json
~~~~

If you want to send a request in XML, you have to add "-x" option into the parameter.
If you want to see the result in XML, you have to add "-X" option as well.

If you want to use the IEEE1888.3 security,
you have to specify the https scheme
and pass the security configuration to the command like below.

~~~~
% fiapc.py -e https://fiap.example.org/storage -f fetch.json \
    -c config.json
~~~~

### trapy.py

TBD

## System requirement

python version is 2.7.
you need addtional python modules.
you have to use the mongodb if you use the IEEE1888 server.

### python modules

the following modules are required.  most modules are installed in the python core module.

    ~~~~
    Base64
    BaseHTTPServer
    SocketServer
    argparse
    bson
    python-dateutil
    hmac
    httplib2
    json
    mimetools
    pymongo
    pytz
    rfc822
    urlparse
    uuid
    ~~~~

the following modules are needed to be installed.

    ~~~~
    pymongo
    python-dateutil
    httplib2
    ~~~~

one example for python module installation is like below:

    ~~~~
    % sudo easy_install pymongo
    ~~~~

### mongodb

this version requires mongodb as the backend database.
you need to configure properly and prepare the port number for the mongodb server.
you have to specify the port number when you launch fiapy.py.

### timezone

Since Mongodb doesn't support timezone for ISODate(),
any datetime objects are removed the timezone and become naive.
So, fiapy looks upon any data in the Mongodb as in UTC.

If you put a time attribute with a timezone, fiapy converts it in UTC before storing the data into Mongodb.
If you put a time attribute without any timezone, fiapy considers it in the timezone you defined
when you had launched fiapy.
The timezone in the response from fiapy is always converted into the timezone you specified as well.
See the options of fiapy.

You should consider to convert it into your timezone when you see it on your browswer.

## TODO

- documentation.
- content-length considertaions.
- good log messages in operation.  e.g. logging point id.
- implement TRAP protocol, trapy.
- consider the error message when the translation error happens.
- consider the error message when the method hasn't been identified.
- client(fiapyc) side cursor handling.

## IEEE1888.3 security

See [HOWTO-cert.md](https://github.com/tanupoo/fiapy/blob/master/doc/HOWTO-cert.md)
to create certificates for the IEEE1888 component.
Checking the peer's subjectAltName has not been done yet.
IEEE1888-level rejection has not been supported yet.

### current specification

- It always sends the certificate request.
- It doesn't case the CA directory.

## Timezone

The timezone of data in the database is UTC.
If an offset of the datetime string in the point element is specified,
fiapy converts it into UTC before saving the data.
If any offset is not specified and the timezone is defined in the JSON data,
fiapy uses the timezone in the JSON data to convert it into UTC.
If both an offset of the datetime string and the timezone in the JSON data,
fiapy uses the offset of the string.
If any timezone information are not specified,
fiapy deals with it as UTC timezone.

## JSON format

see [JSON-data-model.md](https://github.com/tanupoo/fiapy/blob/master/doc/JSON-data-model.md)

## sample

    ~~~~
    python fiapc.py -d 99 -e http://localhost/ -f sample/test-fetch-01.json -c sample/comp003-config.json
    ~~~~

    ~~~~
    python sample-interface-stat.py | ./fiapc.py -e http://localhost
    ~~~~

## Tips

### How to send a IEEE1888 POST request simply.

if you want to send a request in XML without fiapClient.py,
you can use test-post-xml.sh to send it.
It just utilizes "wget --post-file".

