#!/usr/bin/env python

# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.
"""This is intended to be run as a command line tool. See the accompanying
   README file or man page for details."""

import sys
from optparse import OptionParser

from TileCache.Client import seed
from TileCache.Service import Service, cfgfiles
from TileCache.Layer import Layer

if __name__ == "__main__":
    usage = "usage: %prog <layer> [<zoom start> <zoom stop>]"
    
    parser = OptionParser(usage=usage, version="%prog $Id$")

    parser.add_option("-f","--force", action="store_true", dest="force", default = False,
                      help="force recreation of tiles even if they are already in cache")
    parser.add_option("-b","--bbox",action="store", type="string", dest="bbox", default = None,
                      help="restrict to specified bounding box")
    parser.add_option("-p","--padding",action="store", type="int", dest="padding", default = 0,
                      help="extra margin tiles to seed around target area. Defaults to 0 "+
                      "(some edge tiles might be missing).      A value of 1 ensures all tiles "+
                      "will be created, but some tiles may be wholly outside your bbox")
    parser.add_option("-r","--reverse", action="store_true", dest="reverse", default = False,
                      help="Reverse order of seeding tiles")
    parser.add_option("--skip_empty", action="store_true", dest="skip_empty", default = False,
                      help="Don't generate empty tiles: the layer must be a mapserver and a vector layer")

    (options, args) = parser.parse_args()

    if len(args)>3:
        parser.error("Incorrect number of arguments. bbox and padding are now options (-b and -p)")

    svc = Service.load(*cfgfiles)
    layer = svc.layers[args[0]]

    if options.bbox:
        bboxlist = map(float,options.bbox.split(","))
    else:
        bboxlist=None

    if len(args) > 1:
        seed(svc, layer, map(int, args[1:3]), bboxlist , padding=options.padding, force = options.force, reverse = options.reverse)
    else:
        for line in sys.stdin.readlines():
            lat, lon, delta = map(float, line.split(","))
            bbox = (lon - delta, lat - delta, lon + delta, lat + delta)
            print "===> %s <===" % (bbox,)
            seed(svc, layer, (5, 17), bbox , force = options.force )
