#!/usr/bin/python

# Copyright (c) 2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""Tool to print twitter access_tokens, run as a service, to avoid
   publishing consumer_key/consumer_secret."""

__version__ = "0.2"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

# if *we* have consumer_token, consumer_secret (ie. get_oauth_info just works)
# then we run tweepy.OAuthHandler, and get_authorization_url
# tell the user to click on it, and go *to the app* with the verifier

# So really, the app should call this service to get the url.
# and anyone should be able to just use it, the auth steps are taken care of by twitter.

import tweepy
from ztwitgw import get_oauth_info

def generate_url():
    """Just give me a url [why does this ever change? *does* this ever change?]"""
    consumer_token, consumer_secret = get_oauth_info()
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
    redirect_url = auth.get_authorization_url()
    return redirect_url
