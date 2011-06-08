#!/usr/bin/python

# Copyright (c) 2008-2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""take recent twitters and zephyr them to me"""

__version__ = "0.1"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

import urllib
import simplejson
import sys
import os
import getpass
import subprocess
import time
import errno
import signal

urllib.URLopener.version = "thok.org-ztwitgw.py-one-way-zephyr-gateway/%s" % __version__

# from comick.py - either I should come up with my *own* library
#  for this, or find some existing library that has come out since
#  2003 that already does (maybe pycurl...)
class MyFancyURLopener(urllib.FancyURLopener):
    """prevent implicit basicauth prompting"""
    http_error_default = urllib.URLopener.http_error_default
    # don't allow password prompts
    prompt_user_passwd = lambda self, host, realm: (None, None)

def get_changed_content(url, etag=None, lastmod=None):
    """get changed content based on etag/lastmod"""
    uo = MyFancyURLopener()
    if etag:
        uo.addheader("If-None-Match", etag)
    if lastmod:
        uo.addheader("If-Modified-Since", lastmod)
    try:
        u = uo.open(url)
    except IOError, e:
        if e[0] == "http error" and e[1] == 304:
            return None, None, None
        raise
    if u.headers.has_key("ETag"):
        etag = u.headers["ETag"]
    if u.headers.has_key("Last-Modified"):
        lastmod = u.headers["Last-Modified"]
    s = u.read()
    u.close()
    return (s, etag, lastmod)

twit_url = "http://twitter.com/statuses/friends_timeline.json"
replies_url = "http://twitter.com/statuses/replies.json"
favorites_url = "http://api.twitter.com/1/favorites.json"

def embed_basicauth(url, user, passwd):
    """stuff basicauth username/password into a url"""
    # could use urllib2 and a real basicauth handler...
    # but the url is constant, so be lazy.
    assert url.startswith("http://")
    tag, path = url.split("://", 1)
    return tag + "://" + user + ":" + passwd + "@" + path

assert "http://a:b@c/" == embed_basicauth("http://c/", "a", "b")

def embed_since_id(url, since_id):
    """add a since_id argument"""
    # http://apiwiki.twitter.com/Twitter-REST-API-Method%3A-statuses-friends_timeline
    assert "?" not in url, "add support for merging since_id with other url args!"
    return url + "?since_id=%s" % since_id

def embed_backdoor(url):
    """add basic auth back doorargument"""
    # zephyr, via tibbetts
    if "?" in url:
        return url + "&source=twitterandroid"
    else:
        return url + "?source=twitterandroid"

def zwrite(username, body, tag, status_id=None):
    """deliver one twitter message to zephyr"""
    # username... will get encoded when we see one
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

def process_new_twits(url=twit_url, tag=""):
    """process new messages, stashing markers"""
    filebase = os.path.expanduser("~/.ztwit_")
    username, pw = file(filebase + "auth", "r").read().strip().split(":", 1)
    if tag:
        filebase = filebase + tag + "_"
    lastfile = filebase + "last"
    etag = None
    lastmod = None
    if os.path.exists(lastfile):
        etag, lastmod = file(lastfile, "r").read().splitlines()

    newurl = embed_basicauth(url, username, pw)
    
    sincefile = filebase + "since"
    since_id = None
    if os.path.exists(sincefile):
        since_id = file(sincefile, "r").read().strip()
        if since_id: # allow for truncated file
            newurl = embed_since_id(newurl, since_id)

    newurl = embed_backdoor(newurl)

    try:
        rawtwits, etag, lastmod = get_changed_content(newurl, etag, lastmod)
    except IOError, ioe:
        if ioe[0] == "http error":
            # "http error" would be enough, given http_error_default, except
            # that open_http gives a 1-arg one if host is empty...
            try:
                (kind, code, message, headers) = ioe
            except IndexError:
                raise ioe
            if 500 <= code <= 599:
                print >> sys.stderr, code, message, "-- sleeping"
                time.sleep(90)
                sys.exit()
            else:
                raise
        elif ioe[0] == "http protocol error":
            # IOError: ('http protocol error', 0, 'got a bad status line', None)
            print >> sys.stderr, ioe, "-- sleeping"
            time.sleep(90)
            sys.exit()
        elif IOError.errno == errno.ETIMEDOUT:
            # IOError: [Errno socket error] (110, 'Connection timed out')
            print >> sys.stderr, ioe, "-- sleeping longer"
            time.sleep(90)
            sys.exit()
        # got one of these, but that should imply a bug on my side?
        # IOError: ('http error', 400, 'Bad Request', <httplib.HTTPMessage instance at 0xb7b48d0c>)
        # this one is special too...
        # IOError: ('http error', 404, 'Not Found', <httplib.HTTPMessage instance at 0xb7ad5eec>)
        # TODO: IOError: [Errno socket error] (104, 'Connection reset by peer')
        else:
            raise
    if not rawtwits:
        return # nothing new, don't update either
    twits = simplejson.loads(rawtwits)
    for twit in reversed(twits):
        if not twit:
            print "huh? empty twit"
            continue
        # who = twit["user"].get("screen_name", "Unknown Screen Name %r" % (twit["user"]))
        who = twit["user"]["screen_name"]
        what = entity_decode(twit["text"])
        status_id = twit["id"]  # to construct a link
        zwrite(who, what, tag, status_id)
        since_id = status_id
            
    newlast = file(lastfile, "w")
    print >> newlast, etag
    print >> newlast, lastmod
    newlast.close()

    newsince = file(sincefile, "w")
    print >> newsince, since_id
    newsince.close()

if __name__ == "__main__":
    signal.alarm(5*60) # been seeing some hangs, give up after a bit
    prog, = sys.argv
    process_new_twits()
    process_new_twits(url=replies_url, tag="reply")
    process_new_twits(url=favorites_url, tag="favorites")
