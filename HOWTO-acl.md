the format of the access control
================================

## format

**in progress, just an IDEA**

    ~~~~
    "acl" : { <acl spec>, ... }

    <acl spec> := "<SAN>" : { <acl for pointid>, ... }

    <acl for pointid> := "<pointid>" : { <acl for method>, ... }

    <acl for method> :=
        "data" : <action spec> |
        "query" : <action spec> |
        "*" : <action spec>

    <action spec> :=
        "accept" |
        "reject"
    ~~~~

## example

    ~~~~
    "acl" : {
        "gw001.hongo.test.gutp.jp": {
            "*": { "*": "accept" }
        },
        "app002.hongo.test.gutp.jp": {
            "http://example.org/fiapy/test/p01": {
                "data": "accept",
                "query": "accept"
            },
            "http://example.org/fiapy/test/p02": {
                "query": "accept"
            },
            "*": { "*": "reject" }
        },
        "app003.hongo.test.gutp.jp": {
            "*": { "*": "reject" }
        },
        "*": { "*": { "*": "reject" } }
    }
    ~~~~
