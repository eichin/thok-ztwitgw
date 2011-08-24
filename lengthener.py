#!/usr/bin/python

# Copyright (c) 2011 Mark Eichin <eichin@thok.org>
# See ./LICENSE (MIT style.)

"""un-shorten a url (if it's from a white-listed set of shorteners.)"""

__version__ = "0.1"
__author__  = "Mark Eichin <eichin@thok.org>"
__license__ = "MIT"

import httplib
import urlparse
import sys

# "general" shorteners allow end users (public or customers) to generate
#   links to *any* site, represented by the domain plus a short alphanumeric
#   token (tinyarrows.com and txtn.us are notable exceptions, which I'll add
#   if I ever see anyone actually using them :-)
general_shorteners = set([
        "bit.ly",
        "ow.ly",
        "ht.ly",                # another ow.ly/hootsuite shortener
        "j.mp",
        "dlvr.it",
        "goo.gl",
        "is.gd",                # http://is.gd/ethics.php - also v.gd, but it is preview-only
])

# feeds.feedburner.com is a (google) redirector, but at least the url is semi
#   informative, if not final (and not shortened.) New category?

# "local" shorteners let a site manage/track popular internal links directly,
#  and make detailed urls more easily shareable.  As with other shorteners,
#  these are followed by a single alphanumeric token (and sometimes cgi arguments)
#  but local ones always link to a particular target site; we might want to
#  explicitly check for that in the future.
local_shorteners = set([
        "engt.co",              # engadget.com
        "adafru.it",            # adafruit.com
        "wapo.st",              # washingtonpost.com
        "df4.us",               # daringfireball.com
        "onforb.es",            # forbes.com
        "on.cnn.com",           # cnn.com (uhhh...)
        "nyti.ms",              # nytimes.com
        "4sq.com",              # foursquare.com
        "youtu.be",             # youtube.com
])

# can't use urllib2 for this - in order to avoid redirected POSTs, it turns
#  any redirect into a GET... even if the redirect was originally a HEAD.
#  Will dig in to that later... stackoverflow gets credit for pointing me in
#  the right direction:
#    http://stackoverflow.com/questions/107405/how-do-you-send-a-head-http-request-in-python
#  though the actual answers there are incomplete or incorrect.

# Initially, no caching, just a lookup with a fast timeout.
# No cookie support either, or specific user-agent, until we find we need one.
def lengthen(url):
    """try to get a redirect, return the redirect if found"""
    split_url = urlparse.urlsplit(url)
    if split_url.netloc not in general_shorteners and split_url.netloc not in local_shorteners:
        return
    if split_url.scheme != "http":
        return
    if split_url.query:         # or add this back in?
        return
    if split_url.fragment:      # or add this back in?
        return
    host_connection = httplib.HTTPConnection(split_url.netloc)
    host_connection.request("HEAD", split_url.path)
    head_response = host_connection.getresponse()
    location = head_response.getheader("location")
    host_connection.close()
    return location

if __name__ == "__main__":
    for url in sys.argv[1:]:
        print url, "->", lengthen(url)
