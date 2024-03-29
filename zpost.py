#!/usr/bin/python3

# Copyright (c) 2008-2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""zwrite-like twitter poster

(mostly to share a common password file with ztwitgw)"""

__version__ = "0.5"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

import sys
import optparse
import tweepy
from ztwitgw import get_verifier_tty, get_oauth_verifier, get_just_verifier, get_oauth_info

# NOTE: tweepy.error.TweepError: Read-only application cannot POST
#   when using the ztwitgw key, need to register another or expand this one

# TODO: retry on 408, maybe others?
def zpost(body):
    """post body to twitter"""
    assert len(body) <= 280

    rt_key, rt_secret, at_key, at_secret, verifier = get_oauth_verifier(get_just_verifier, "zpost")

    consumer_token, consumer_secret = get_oauth_info("zpost")
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
    auth.set_access_token(at_key, at_secret)
    api = tweepy.API(auth)
    return api.update_status(body)

if __name__ == "__main__":
    parser = optparse.OptionParser(usage=__doc__)
    parser.add_option("--do-auth", action="store_true",
                      help="Do an authentication for the first time")
    parser.add_option("--message", "-m", action="store_true",
                      help="send the remaining args as the message")
    options, args = parser.parse_args()

    if options.do_auth:
        assert not options.message, "only auth"
        rt_key, rt_secret, at_key, at_secret, verifier = get_oauth_verifier(get_verifier_tty, "zpost")
        # they get written out as a side effect, if we made it here, great
        print("Auth completed.")
        sys.exit()

    if options.message:
        message = " ".join(args)
        print(zpost(message))
    else:
        print("Type your message now.  End with control-D.")
        message = sys.stdin.read()
        print(zpost(message))
