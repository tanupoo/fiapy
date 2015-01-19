#!/bin/sh

ts=`date +'%Y-%m-%dT%H:%M:%%02d%z'`

exec_fiapy() {
cat <<EOD | ./fiapClient.py -e http://localhost/
{
  "fiap" : {
    "version" : "20140401",
    "dataRQ" : {
      "http://example.org/fiapy/test/p01" : [
        { "time" : "$ts1", "value" : "$1" }
      ],
      "http://example.org/fiapy/test/p02" : [
        { "time" : "$ts1", "value" : "$2" },
        { "time" : "$ts2", "value" : "$3" }
      ],
      "http://example.org/fiapy/test/p03" : [
        { "time" : "$ts1", "value" : "$4" },
        { "time" : "$ts2", "value" : "$5" },
        { "time" : "$ts3", "value" : "$6" }
      ]
    }
  }
}
EOD
}

i=0
while [ $i -lt 50 ] ;
do
	ts1=`printf $ts $i`
	ts2=`printf $ts $((i+1))`
	ts3=`printf $ts $((i+2))`
	i=$((i+3))

	x="`head -c 6 < /dev/random | hexdump -b | head -1 | cut -c9-`"
	echo $x | (read v1 v2 v3 v4 v5 v6; exec_fiapy 1$v1 2$v2 3$v3 4$v4 5$v5 6$v6)
done
