#!/usr/bin/python

# Copyright (c) 2008-2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""zwrite-like twitter poster

(mostly to share a common password file with ztwitgw)"""

import sys
import os
import urllib
import optparse
import simplejson
from ztwitgw import embed_basicauth, embed_backdoor, MyFancyURLopener

urllib.URLopener.version = "thok.org-zpost.py/0.1"

# http://apiwiki.twitter.com/REST+API+Documentation says:
# curl -u email:password -d status="your message here" http://twitter.com/statuses/update.xml 

update_url = "http://twitter.com/statuses/update.json"

def get_auth_info():
    """get this user's auth info"""
    filebase = os.path.expanduser("~/.ztwit_")
    username, pw = file(filebase + "auth", "r").read().strip().split(":", 1)
    return username, pw


# TODO: retry on 408, maybe others?
def zpost(body):
    """post body to twitter"""
    assert len(body) <= 140
    username, pw = get_auth_info()
    posturl = embed_basicauth(update_url, username, pw)
    posturl = embed_backdoor(posturl)
    uo = MyFancyURLopener()
    u = uo.open(posturl, urllib.urlencode(dict(status=body)))
    # let the exceptions bubble up
    raw_s = u.read()
    u.close()
    s = simplejson.loads(raw_s)
    return s

if __name__ == "__main__":
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option("--message", "-m", action="store_true",
                      help="send the remaining args as the message")
    options, args = parser.parse_args()

    if options.message:
        message = " ".join(args)
        print zpost(message)
    else:
        print "Type your message now.  End with control-D."
        message = sys.stdin.read()
        print zpost(message)
