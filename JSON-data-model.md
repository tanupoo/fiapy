REST API
========

## JSON encoding

~~~~
{ "fiap" : <version>, 
  <timezone>,
  <data request spec> |
  <data response spec> |
  <query request spec> |
  <query response spec for FETCH> |
  <query response spec for TRAP> }

<version> := "20140401"

<timezone> := "timezone" : <tz string>
  option

<data request spec> :=
  "dataRQ" : [ <point spec>, ... ]

<data response spec> :=
  "dataRS" : {
    "response" : <response message> }

<query request spec> :=
  "queryRQ" : <storage query spec> |
  <stream query spec>

<query response spec for FETCH> :=
  "queryRS" : {
    "response" : <response message>,
    "query" : <storage query spec>,
    "point" : { <point spec>, ... } }

<query response spec for TRAP> :=
  "queryRS" : {
    "response" : <response message>,
    "query" : <stream query spec> }

<point spec> :=
  "<point id>" : [ <value spec>, ... ]

<value spec> := {
  "time" : <time spec>,
  "value" : <value> }

<storage query spec> := {
  "uuid" : <uuid>,
  "type" : "storage",
  "acceptableSize" : <acceptable size>,
  "cursor" : <cursor>,
  "key" : [ <key spec>, ... ] }

<stream query spec> := {
  "uuid" : <uuid>,
  "type" : "stream",
  "acceptableSize" : <acceptable size>,
  "cursor" : <cursor>,
  "ttl" : <ttl>,
  "callbackData" : <callback data point>,
  "callbackControl" : <callback control point>,
  "key" : [ <key spec> ... ] }

<key spec> := {
  "id" : <point id>,
  "attrName" : <attribute name>,
  "eq" : <value>,
  "ne" : <value>,
  "lt" : <value>,
  "gt" : <value>,
  "lteq" : <value>,
  "gteq" : <value>,
  "select" : <"minimum" | "maximum">,
  "trap" : <"changed"> }

<cursor> := "cursor is going to be specified in a storage query spec"

<point id> := PointID

<time spec> := ISO8601 date and time string
    it should be with a timezone indicator.
    e.g. 2014-11-21T07:54:03+0900

<value> := value string
    a double quatation is not allowed for the value data.
~~~~

### consice encoding for GET response

~~~~
{ "fiap" : <version>, 
  <query response spec for FETCH> }

<query response spec for FETCH> :=
  "queryRS" : {
    "response" : <response message>,
    "point" : { <point spec>, ... } }

<query spec> is optional.
~~~~

## response message

RFC2616 section 10

## example

~~~~
    {
      "fiap": {
        "version": "20141225",
        "queryRS": {
          "query": {
            "uuid": "1234-5678-5678-5678-5678-5678"
          }
          "point": {
            "http://fiap.tanu.org/test/alps01/temp": [
              { "time": "2014-11-21T07:54:03+0900", "value": "26.0" },
              { "time": "2014-11-21T07:55:00+0900", "value": "26.5" }
            ],
            "http://fiap.tanu.org/test/alps01/light": [
              { "time": "2014-11-21T07:54:03+0900", "value": "1301" },
              { "time": "2014-11-21T07:55:00+0900", "value": "1400" }
            ]
          }
        }
      }
    }
~~~~

## URL encoding

don't specify a complicated query.

### proposed schema name

- igem (Internet Green Environment Messaging)
- image (Internet Messaging for the Advanced Green Environment)

### query

~~~~
k=<point id>
a=value or time
    default: depends on the implementation.
m=max or min
    must be used with "a=".
eq=
    equal to.
    must be used with "a=".
ne=
    not equal to.
    must be used with "a=".
lt=
    less than.
    must be used with "a=".
gt=
    greater than.
    must be used with "a=".
lteq=
    less than or equal.
    must be used with "a=".
gteq=
    greater than or equal.
    must be used with "a=".
e=
    a session identifier.
~~~~

default: latest data.

### write

it only allows to write a single key.
"&" is used for a delimitter.

~~~~
k=<point id>
v=<value spec>
    <value spec> must be enclosed by a double quatation.  e.g. "26.5"
    the value must not allowed to include both "&" and any double quatations.
t=<time spec>
~~~~

### example

RFC 2396 encoding should be used.

- fetch

http://server.example.org/?k=igem://example.org/test/temperature&k=igem://example.org/test/humidity

- write

http://server.example.org/?k=igem://example.org/test/temperature&v="26.5"&t=2014-11-21T07:55:00+0900

## method

### POST

it supports full IEEE1888 data and query method.
The encoding is either JSON or XML.
in the case of XML encoding, it is identical to IEEE1888 base specification.

Content-Type must be text/json when JSON encoding is used.

if a requester sends a query by JSON encoding, the responder must respond data by JSON encoding or a HTTP error code with 415 (Unsupported Media Type). 

### GET

it supports simple IEEE1888 query method.
it allows to fetch a set of data of a single point id,
or to fetch a set of data of identical condition in each point ids.

a requester sends a request by the URL encoding.
a responder responds data by JSON encoding.

typically, a requester uses this method to fetch a latest data against a point id specified in the URL.

### PUT

it supports the limited IEEE1888 write method.
it allows to write a single value for a single point id.
it dosen't allow to write multiple values for a single point id,
nor to write multiple point ids.

### Other method

TBD

