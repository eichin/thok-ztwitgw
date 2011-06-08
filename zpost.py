#!/usr/bin/python

# Copyright (c) 2008-2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""zwrite-like twitter poster

(mostly to share a common password file with ztwitgw)"""

__version__ = "0.2"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

import sys
import tweepy
import optparse
from ztwitgw import get_oauth_info, get_verifier_tty, get_oauth_verifier

# NOTE: tweepy.error.TweepError: Read-only application cannot POST
#   when using the ztwitgw key, need to register another or expand this one

# TODO: retry on 408, maybe others?
def zpost(body, get_first_verifier=get_verifier_tty):
    """post body to twitter"""
    assert len(body) <= 140

    rt_key, rt_secret, at_key, at_secret, verifier = get_oauth_verifier(get_first_verifier)

    consumer_token, consumer_secret = get_oauth_info()
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
    auth.set_request_token(rt_key, rt_secret)
    auth.set_access_token(at_key, at_secret)
    api = tweepy.API(auth)
    return api.update_status(body)

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
