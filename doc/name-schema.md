schema name proposal
====================

<<**this is the draft version.  More discusssion is needed.**>>

## schema name

The representation of "Point ID" is like below:

    ~~~~
    http://example.org/home/device01/temperature
    ~~~~

The original reason why it uses "http:" schema is that it would provide information related to the Point ID when you accessed to the link.

But, it sometimes disturbs for a developer to understand IEEE1888.
It is not used though it is like ly to be.

The only requirement is that the identifier of "Point ID" must be identical in the Internet.
It's just a string of the identifier of data stream.
It's not a URL though it is likely to be.

When I introduce the version of GET method, the point IDs (it's just URI) are present in the URL.  It is awkward.

In addition, "http" in the point ID is not a schema name of the URI.
It breaks the intent of RFC 3968.

So, we probably need a different name for the part of schema in the point ID.

### idea: proposed schema name

- igem (Internet Green Environment Messaging)
- image (Internet Messaging for the Advanced Green Environment)
- imase (Internet Messaging for the Advanced Smart Energy)

