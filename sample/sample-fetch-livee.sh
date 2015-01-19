#!/bin/sh
cat <<EOD | ./fiapClient.py -e http://live-e-storage.hongo.wide.ad.jp/axis2/services/FIAPStorage -x
{
  "fiap" : {
    "version" : "20140401",
    "queryRQ" : {
      "type" : "storage",
      "acceptableSize" : "10",
      "key" : [
        {
          "http://tanu.org/WXT510/SHome/Temperature" : {
            "attrName" : "time",
            "select" : "maximum"
          }
        },
        {
          "http://tanu.org/WXT510/SHome/Temperature" : {
            "attrName" : "time",
            "select" : "minimum"
          }
        },
        {
          "http://tanu.org/WXT510/SHome/Temperature" : {
            "attrName" : "time",
            "gteq" : "2015-01-10T12:00:00+09:00"
          }
        }
      ]
    }
  }
}
EOD
