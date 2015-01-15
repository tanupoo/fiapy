fiapy
=====

IEEE1888 python implementation with both data models, XML and JSON.

## TODO

- need to check whether it could deal with duplicate keys in a query.
- consider the error message when the translation error happens.
- consider the error message when the method hasn't been identified.
- implement TRAP protocol, trapy.

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

see JSON-data-model.md

##

how to send POST request in XML

wget --quiet --output-document=- --header='Content-Type: text/xml' --post-file=test-fetch-01.xml http://localhost:18880/
