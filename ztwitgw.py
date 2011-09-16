#!/usr/bin/python

# Copyright (c) 2008-2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""take recent twitters and zephyr them to me"""

__version__ = "0.2"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

import sys
import os
import getpass
import subprocess
import signal
import tweepy
import time
from lengthener import lengthen

def get_oauth_info(appname=None):
    """get this user's oauth info"""
    filebase = os.path.expanduser("~/.ztwit_")
    if appname:
        # default path is ztwitgw
        filebase += appname + "_"
    key, secret = file(filebase + "oauth", "r").read().strip().split(":", 1)
    return key, secret

# TODO: write get_verifier_X11

def get_verifier_tty(output_path, appname=None):
    """we don't have a verifier, ask the user to use a browser and get one"""
    consumer_token, consumer_secret = get_oauth_info(appname=appname)
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
    redirect_url = auth.get_authorization_url() # tweepy.TweepError
    print "Open this URL in a browser where you're logged in to twitter:"
    print redirect_url
    verifier = raw_input("Enter (cut&paste) the response code: ")
    # use it...
    auth.get_access_token(verifier)
    # hmm, discard the verifier?
    file(output_path, "wb").write(":".join([auth.request_token.key, 
                                            auth.request_token.secret, 
                                            auth.access_token.key,
                                            auth.access_token.secret,
                                            verifier]))
    
def get_just_verifier(output_path, appname=None):
    """ask for the verifier *without* having consumer info"""
    auth = tweepy.OAuthHandler("", "")
    # TODO: this can't work unless we first give the user a redirect to the
    #    URL to *get* the response code. and possibly not then?
    verifier = raw_input("Enter (cut&paste) the response code: ")
    # use it...
    auth.get_access_token(verifier)
    # hmm, discard the verifier?
    file(output_path, "wb").write(":".join([auth.request_token.key, 
                                            auth.request_token.secret, 
                                            auth.access_token.key,
                                            auth.access_token.secret,
                                            verifier]))



def get_oauth_verifier(fallback_mechanism, appname=None):
    """get the request token and verifier, using fallback_mechanism if we don't have one stashed"""
    filebase = os.path.expanduser("~/.ztwit_")
    if appname:
        # default path is ztwitgw
        filebase += appname + "_"
    verifier_file = filebase + "oauth_verifier"
    if not os.path.exists(verifier_file):
        fallback_mechanism(verifier_file, appname=appname)
        if not os.path.exists(verifier_file):
            raise Exception("Fallback Failed")
    rt_key, rt_secret, at_key, at_secret, verifier = file(verifier_file, "r").read().strip().split(":", 4)
    return rt_key, rt_secret, at_key, at_secret, verifier

# do this with a localhost url?

def zwrite(username, body, tag, status_id=None):
    """deliver one twitter message to zephyr"""
    # username... will get encoded when we see one
    try:
        body = body.encode("iso-8859-1", "xmlcharrefreplace")
    except UnicodeDecodeError, ude:
        body = repr(body) + ("\n[encode fail: %s]" % ude)
        body = body.encode("iso-8859-1", "xmlcharrefreplace")
    # example syntax: http://twitter.com/engadget/status/18164103530
    zurl = " http://twitter.com/%s/status/%s" % (username, status_id) if status_id else ""
    zsig = "%s %s%svia ztwitgw%s" % (username, tag, tag and " ", zurl)
    # tag is from codde
    cmd = ["zwrite",
           "-q", # quiet
           "-d", # Don't authenticate
           "-s", zsig,
           "-c", "%s.twitter" % getpass.getuser(),
           "-i", username,
           "-m", body]
    subprocess.check_call(cmd)
           
def entity_decode(txt):
    """decode simple entities"""
    # TODO: find out what ones twitter considers defined,
    #   or if sgmllib.entitydefs is enough...
    return txt.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

# turns out we don't actually see &amp; in practice...
assert entity_decode("-&gt; &lt;3") == "-> <3"

def maybe_lengthen(url):
    """lengthen the url (with an old-ref) *or* leave it untouched"""
    new_url = lengthen(url)
    if not new_url:
        return url
    return "%s (via %s )" % (new_url, url)

def slice_substitute(target, offset, low, high, replacement):
    """substitute replacement into target in span low..high; return new target, new offset"""
    target = target[:low+offset] + replacement + target[high+offset:]
    offset += len(replacement) - (high - low)
    return target, offset

assert slice_substitute("abcdefghij", 0, 3, 6, "DEF") == ('abcDEFghij', 0)
assert slice_substitute("abcdefghij", 0, 3, 6, "X") == ('abcXghij', -2)
assert slice_substitute("abcdefghij", 0, 3, 6, "__DEF__") == ('abc__DEF__ghij', 4)

def url_expander(twit, body):
    """expand urls in the body, safely"""
    expcount = 0
    urlcount = 0
    longcount = 0
    offset = 0
    try:
        # https://dev.twitter.com/docs/tweet-entities
        # do media later, stick with urls for now
        for urlblock in twit.entities.get("urls", []):
            low, high = urlblock["indices"]
            if urlblock.get("expanded_url"):
                body, offset = slice_substitute(body, offset, low, high, 
                                                maybe_lengthen(urlblock["expanded_url"]))
                expcount += 1
            else:
                raw_replacement = maybe_lengthen(urlblock["url"])
                if raw_replacement != urlblock["url"]:
                    body, offset = slice_substitute(body, offset, low, high, raw_replacement)
                    longcount += 1
            urlcount += 1
        if expcount or urlcount or longcount:
            return body + ("\n[expanded %s/%s urls, lengthened %s]" % (expcount, urlcount, longcount))
        return body
    except Exception, exc:
        return body + ("[expander failed: %s]" % exc)

def process_new_twits(api, proto=None, tag=""):
    """process new messages, stashing markers"""
    if proto is None:
        proto = api.friends_timeline

    filebase = os.path.expanduser("~/.ztwit_")
    if tag:
        filebase = filebase + tag + "_"
    sincefile = filebase + "since"
    since_id = None
    if os.path.exists(sincefile):
        since_id = file(sincefile, "r").read().strip()
        # if since_id: # allow for truncated file

    # the iterators *have* a prev, but there's no way to "start" at since_id?
    # favorites.json doesn't take an id arg, and it's not like we save anything
    # (other than parsing) by walking up and then down, since the json for the
    # entire set is loaded anyway...
    for twit in reversed(list(tweepy.Cursor(proto, since_id=since_id, include_entities=1).items())):
        # reversed?
        if not twit:
            print "huh? empty twit"
            continue
        # type(twit) == tweepy.models.Status
        # type(twit.author) == tweepy.models.User
        who = twit.author.screen_name
        what = entity_decode(url_expander(twit, twit.text))
        status_id = twit.id_str  # to construct a link
        zwrite(who, what, tag, status_id)
        since_id = status_id
        print "Sent:", since_id
        time.sleep(3)
        signal.alarm(5*60) # if we're actually making progress, push back the timeout
            
    # Note that since_id is just an ordering - if I favorite an old tweet (even
    # something that showed up new because it was freshly retweeted) it doesn't
    # show up.  This isn't a new bug, I'm just noticing it...
    newsince = file(sincefile, "w")
    print >> newsince, since_id
    newsince.close()

if __name__ == "__main__":
    signal.alarm(5*60) # been seeing some hangs, give up after a bit
    prog, = sys.argv

    rt_key, rt_secret, at_key, at_secret, verifier = get_oauth_verifier(get_verifier_tty)
    consumer_token, consumer_secret = get_oauth_info()
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
    auth.set_request_token(rt_key, rt_secret)
    auth.set_access_token(at_key, at_secret)
    print "ct:", consumer_token
    print "cs:", consumer_secret
    print "rk:", rt_key
    print "rs:", rt_secret
    print "vf:", verifier
    print "ak:", at_key
    print "as:", at_secret
    api = tweepy.API(auth)

    process_new_twits(api)
    process_new_twits(api, proto=api.mentions, tag="reply")
    # replies_url = "http://twitter.com/statuses/replies.json"
    # but that's not in tweepy... try hacking it?
    # hmm, not in http://apiwiki.twitter.com/w/page/22554679/Twitter-API-Documentation either
    process_new_twits(api, proto=api.favorites, tag="favorites")
