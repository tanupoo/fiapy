#!/usr/bin/env python
# -*- coding: utf-8 -*-

tv = \
'''
<!-- write request -- />
<ns1:dataRQ>
<transport>
  <body>
    <point id="http://www.gutp.jp/light/dimmer">
    <value time="2009-10-19T00:00:00.0000000+09:00">true</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">false</value>
    </point>
    <point id="http://www.gutp.jp/light/analogue_level">
    <value time="2009-10-19T00:00:00.0000000+09:00">10</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">0</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">3.4</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">0.5323</value>
    </point>
    <point id="http://www.gutp.jp/light/01/gradual_level">
    <value time="2009-10-19T00:00:00.0000000+09:00">HIGH</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">MID</value>
    <value time="2009-10-19T00:00:00.0000000+09:00">LOW</value>
    </point>
  </body>
</transport>
</ns1:dataRQ>

''', '''
<!-- query request -- />
<ns1:queryRQ>
<transport>
  <header>
    <query id="6229c37f-970d-9292-83e4-7c0e54733f8a"
      type="storage"
      acceptableSize="20"
      cursor="dab751ed-0133-4ce4-8b7d-ba5c54ce4fb5">
      <key id="http://gw.foo.org/room1/temperature" attrName="time"
        lteq="2009-10-01T00:00:00.0000000+09:00"
        gteq="2009-09-01T00:00:00.0000000+09:00" />
      <key id="http://gw.foo.org/room1/temperature"
        attrName="time" select="maximum" />
    </query>
  </header>
</transport>
</ns1:queryRQ>

''', '''
<!-- trap request -- />
<ns1:queryRQ>
<transport>
  <header>
    <query id="9eed9de4-1c48-4b08-a41d-dac067fc1c0d" type="stream"
      ttl="60"
      callbackData="http://hogehoge/axis/services/GUTAPI"
      callbackControl="http://hogehoge/axis/services/GUTAPI" >
      <key id="http://gw.foo.org/room1/temperature"
        attrName="time" trap="changed" />
      <key id="http://gw.foo.org/room1/temperature"
        attrName="value" trap="changed" />
    </query>
  </header>
  <body>
  </body>
</transport>
</ns1:queryRQ>

''', '''
<!-- response OK -- />
<ns1:dataRS>
<transport>
  <header>
    <OK />
  </header>
</transport>
</ns1:dataRS>

''', '''
<!-- response with error -- />
<ns1:dataRS>
<transport>
  <header>
    <error type="syntax">Malformed XML Error</error>
  </header>
</transport>
</ns1:dataRS>

''', '''
<!-- registration sample 1-- />
<transport xmlns:s="http://www.gutp.jp/ns/">
  <body>
    <component name="myGW"
      uri="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/axis/services/FIAPBACnetWSGW"
      support="FETCH|TRAP">
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/DB1"
        stream="in" limit="1" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/DB2"
        stream="in" limit="1" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/RH1"
        stream="in" limit="1" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/RH2"
        stream="in" limit="1" />
    </component>
  </body>
</transport>

''', '''
<!-- registration sample 2-- />
<transport>
  <body>
    <component name="myStorage"
      uri="http://fiap-storage.gutp.ic.i.u-tokyo.ac.jp/axis/services/FIAPStorage"
      support="FETCH|WRITE">
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/DB1" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/DB2" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/RH1" />
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/RH2" />
    </component>
  </body>
</transport>

''', '''
<!-- registration sample 3 -- />
<transport>
  <body>
    <point id="X" s:type="BINARY_INPUT" s:writable="false" s:location="Building2F221MeetingRoom1" />
    <point id="Y" s:type="BINARY_INPUT" s:writable="false" s:location="Building2F221MeetingRoom1" />
    <point id="Z" s:type="ANALOG_INPUT" s:writable="false" s:location="Building2F221MeetingRoom1" />
    <point id="W" s:type="MULTI_STATE_INPUT" s:writable="false" s:location="Building2F221MeetingRoom1" />
  </body>
</transport>

''', '''
<!-- lookup -- />
<transport>
  <header>
    <lookup id="6e5a0e85-b4a0-485f-be54-a758115317e1" type="component">
      <key id="http://fiap-gw.gutp.ic.i.u-tokyo.ac.jp/EngBldg2/10F/102A2/DB1" />
    </lookup>
  </header>
</transport>

''', '''
<!-- lookup -- />
<transport>
  <header>
    <lookup id="3f2504e0-4f89-11d3-9a0c-0305e82c3301" type="point">
      <point s:type="BINARY_INPUT" s:location="Building2F221MeetingRoom1"/>
    </lookup>
  </header>
</transport>

''', '''
<!-- lookup response -- />
<transport>
  <header>
    <lookup>
    </lookup>
    <OK />
  </header>
  <body>
  </body>
</transport>

'''

#
# component.key attributes
#
# - name: the name of the specified component (i.e., GW, Storage, or APP)
# - uri: the access URI of the specified component
# - priority: priority of access for the redundant dataset (optional)
# - support: which protocol type(s) the specified component supports (i.e., FETCH, WRITE, TRAP)
# - expires: the effective expiration time of the registration in seconds (optional)

#
# lookup.key attributes
#
# - id: identifier of the Point (i.e., Point ID)
# - attrName: the searching attributes of objects
# - stream: data flow comes into and out {in, out}of the component
# - limit: data caching maximum size
# - eq: this predicate becomes true if the key attribute value is equal to the specified value, otherwise it becomes false
# - neq: this predicate becomes true if the key attribute value is not equal to the specified value, otherwise it becomes false
# - lt: this predicate becomes true if the key attribute value is less than the specified value
# - gt: this predicate becomes true if the key attribute value is greater than the specified value
# - lteq: this predicate becomes true if the key attribute value is less than or equal to the specified value
# - gteq: this predicate becomes true if the key attribute value is greater than or equal to the specified value
