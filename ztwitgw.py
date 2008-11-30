#!/usr/bin/python

"""take recent twitters and zephyr them to me"""

import urllib
import simplejson
import sys
import os
import getpass
import subprocess
import time

urllib.URLopener.version = "thok.org-ztwitgw.py-one-way-zephyr-gateway/0.1"

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
def embed_basicauth(url, user, passwd):
    """stuff basicauth username/password into a url"""
    # could use urllib2 and a real basicauth handler...
    # but the url is constant, so be lazy.
    assert url.startswith("http://")
    tag, path = url.split("://", 1)
    return tag + "://" + user + ":" + passwd + "@" + path

assert "http://a:b@c/" == embed_basicauth("http://c/", "a", "b")

def zwrite(username, body, tag):
    """deliver one twitter message to zephyr"""
    # username... will get encoded when we see one
    body = body.encode("iso-8859-1", "xmlcharrefreplace")
    # tag is from codde
    cmd = ["zwrite",
           "-q", # quiet
           "-d", # Don't authenticate
           "-s", "%s %s%svia ztwitgw" % (username, tag, tag and " "),
           "-c", "%s.twitter" % getpass.getuser(),
           "-i", username,
           "-m", body]
    subprocess.check_call(cmd)
           
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
        else:
            raise
    if not rawtwits:
        return # nothing new, don't update either
    twits = simplejson.loads(rawtwits)
    for twit in reversed(twits):
        who = twit["user"]["screen_name"]
        what = twit["text"]
        zwrite(who, what, tag)
            
    newlast = file(lastfile, "w")
    print >> newlast, etag
    print >> newlast, lastmod
    newlast.close()

if __name__ == "__main__":
    prog, = sys.argv
    process_new_twits()
    process_new_twits(url=replies_url, tag="reply")
