fiapy
=====

IEEE1888 python implementation with both data models, XML and JSON.

## TODO

- need to implement TRAP protocol, trapy.
- make timezone handling sure.
- write manual
- cursor

### fiapy.py

### trapy.py

### fiapClient.py

## response message

It should be conformed to section 10 of RFC2616.

### Timezone

The timezone of data in the database is UTC.
If an offset of the datetime string in the point element is specified,
fiapy converts it into UTC before saving the data.
If any offset is not specified and the timezone is defined in the JSON data,
fiapy uses the timezone in the JSON data to convert it into UTC.
If both an offset of the datetime string and the timezone in the JSON data,
fiapy uses the offset of the string.
If any timezone information are not specified,
fiapy deals with it as UTC timezone.

## FIAP data model in JSON

{ "fiap" : <version>, 
  "timezone" : <tz string>, 
  <data request spec> |
  <data response spec> |
  <query request spec> |
  <query response spec> }

<version> := "20140401"

<data request spec> :=
  "dataRQ" : [ <point spec>, ... ]

<data response spec> :=
  "dataRS" : {
    "response" : <response message> }

<query request spec> :=
  "queryRQ" : <storage query spec> | <stream query spec>

<query response spec> :=
  "queryRS" : {
    "response" : <response message>,
    "point" : [ <point spec>, ... ] }

<point spec> := {
  "<point id>" : [ <value spec>, ... ] }

<value spec> := {
  "value" : <value>,
  "time" : <time spec> }

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

<point id> := PointID

<time spec> := ISO8601 date and time string

<value> := value string

