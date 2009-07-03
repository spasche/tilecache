#!/usr/bin/env python

# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.

import sys, urllib, urllib2
import httplib

# setting this to True will exchange more useful error messages
# for privacy, hiding URLs and error messages.
HIDE_ALL = False 

class WMS (object):
    fields = ("bbox", "srs", "width", "height", "format", "layers", "styles")
    defaultParams = {'version': '1.1.1', 'request': 'GetMap', 'service': 'WMS'}
    __slots__ = ("base", "params", "client", "data", "response")

    def __init__ (self, base, params, user=None, password=None):
        self.base    = base
        if self.base[-1] not in "?&":
            if "?" in self.base:
                self.base += "&"
            else:
                self.base += "?"

        self.params  = {}
        if user is not None and password is not None:
           x = urllib2.HTTPPasswordMgrWithDefaultRealm()
           x.add_password(None, base, user, password)
           self.client  = urllib2.build_opener()
           auth = urllib2.HTTPBasicAuthHandler(x)
           self.client  = urllib2.build_opener(auth)
        else:
           self.client  = urllib2.build_opener()

        for key, val in self.defaultParams.items():
            if self.base.lower().rfind("%s=" % key.lower()) == -1:
                self.params[key] = val
        for key in self.fields:
            if params.has_key(key):
                self.params[key] = params[key]
            elif self.base.lower().rfind("%s=" % key.lower()) == -1:
                self.params[key] = ""

    def url (self):
        return self.base + urllib.urlencode(self.params)
    
    def fetch (self):
        urlrequest = urllib2.Request(self.url())
        # urlrequest.add_header("User-Agent",
        #    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)" )
        response = None
        while response is None:
            try:
                response = self.client.open(urlrequest)
                data = response.read()
                # check to make sure that we have an image...
                msg = response.info()
                if msg.has_key("Content-Type"):
                    ctype = msg['Content-Type']
                    if ctype[:5].lower() != 'image':
                        if HIDE_ALL:
                            raise Exception("Did not get image data back. (Adjust HIDE_ALL for more detail.)")
                        else:
                            raise Exception("Did not get image data back. \nURL: %s\nContent-Type Header: %s\nResponse: \n%s" % (self.url(), ctype, data))
            except httplib.BadStatusLine:
                response = None # try again
        return data, response

    def setBBox (self, box):
        self.params["bbox"] = ",".join(map(str, box))
