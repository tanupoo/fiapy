#!/bin/sh

file=$1
if [ -z "$file" ] ; then
	echo "Usage: $0 (xml file)"
	exit 1
fi

port=${FIAPY_PORT:-18880}

wget --quiet --output-document=- --header='Content-Type: text/xml' --post-file=$file http://localhost:$port/

