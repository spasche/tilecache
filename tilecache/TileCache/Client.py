#!/usr/bin/env python

# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.

import sys, urllib, urllib2, time, os, math
import httplib
from optparse import OptionParser

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

def seed (svc, layer, levels = (0, 5), bbox = None, padding = 0, force = False, reverse = False ):
    from Layer import Tile
    try:
        padding = int(padding)
    except:
        raise Exception('Your padding parameter is %s, but should be an integer' % padding)

    if not bbox: bbox = layer.bbox

    start = time.time()
    total = 0
    
    for z in range(*levels):
        bottomleft = layer.getClosestCell(z, bbox[0:2])
        topright   = layer.getClosestCell(z, bbox[2:4])
        # Why Are we printing to sys.stderr??? It's not an error.
        # This causes a termination if run from cron or in background if shell is terminated
        #print >>sys.stderr, "###### %s, %s" % (bottomleft, topright)
        print "###### %s, %s" % (bottomleft, topright)
        zcount = 0 
        metaSize = layer.getMetaSize(z)
        ztiles = int(math.ceil(float(topright[1] - bottomleft[1]) / metaSize[0]) * math.ceil(float(topright[0] - bottomleft[0]) / metaSize[1]))
        if reverse:
            startX = topright[0] + metaSize[0] + (1 * padding)
            endX = bottomleft[0] - (1 * padding)
            stepX = -metaSize[0]
            startY = topright[1] + metaSize[1] + (1 * padding)
            endY = bottomleft[1] - (1 * padding)
            stepY = -metaSize[1]
        else:
            startX = bottomleft[0] - (1 * padding)
            endX = topright[0] + metaSize[0] + (1 * padding)
            stepX = metaSize[0]
            startY = bottomleft[1] - (1 * padding)
            endY = topright[1] + metaSize[1] + (1 * padding)
            stepY = metaSize[1]
        for y in range(startY, endY, stepY):
            for x in range(startX, endX, stepX):
                tileStart = time.time()
                tile = Tile(layer,x,y,z)
                bounds = tile.bounds()
                svc.renderTile(tile,force=force)
                total += 1
                zcount += 1
                box = "(%.4f %.4f %.4f %.4f)" % bounds
                print "[%s] %02d (%06d, %06d) = %s [%.4fs : %.3f/s] %s/%s" \
                     % (layer.name, z,x,y, box, time.time() - tileStart, total / (time.time() - start + .0001), zcount, ztiles)
