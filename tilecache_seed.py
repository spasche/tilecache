#!/usr/bin/env python

# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.
"""This is intended to be run as a command line tool. See the accompanying
   README file or man page for details."""

import sys
import fnmatch
from optparse import OptionParser

from TileCache.Seed import seed
from TileCache.Service import Service, cfgfiles
from TileCache.Layer import Layer

def main():
    usage = "usage: %prog <layer> [<zoom start> <zoom stop>]"
    
    parser = OptionParser(usage=usage, version="%prog $Id$")

    parser.add_option("-f","--force", action="store_true", dest="force", default = False,
                      help="force recreation of tiles even if they are already in cache")
    parser.add_option("-b","--bbox",action="store", type="string", dest="bbox", default = None,
                      help="restrict to specified bounding box")
    parser.add_option("-c","--config", action="store", type="string", dest="tilecacheconfig",
                      help="path to configuration file")
    parser.add_option("-p","--padding",action="store", type="int", dest="padding", default = 0,
                      help="extra margin tiles to seed around target area. Defaults to 0 "+
                      "(some edge tiles might be missing).      A value of 1 ensures all tiles "+
                      "will be created, but some tiles may be wholly outside your bbox")
    parser.add_option("-r","--reverse", action="store_true", dest="reverse", default = False,
                      help="Reverse order of seeding tiles")
    parser.add_option("-a", "--all", action="store_false", dest="skip_empty", default = True,
                      help="Generate all the tiles, the default is to skip the empty tiles if the "+
                      "layer is a vector and mapserver layer.")
    parser.add_option("", "--data-projection", action="store", type="string", dest="dataProjectionString", default=None,
                      help="Proj4 string to force the data projection.")
    parser.add_option("", "--tiles-projection", action="store", type="string", dest="tilesProjectionString", default=None,
                      help="Proj4 string to force the tiles projection.")

    (options, args) = parser.parse_args()

    if len(args) > 3:
        parser.error("Incorrect number of arguments. bbox and padding are now options (-b and -p)")

    cfgs = cfgfiles
    if options.tilecacheconfig:
        cfgs = cfgs + (options.tilecacheconfig,)
        
    svc = Service.load(*cfgs)

    if options.bbox:
        bboxlist = map(float, options.bbox.split(","))
    else:
        bboxlist = None

    if len(args) > 1:
        levels = map(int, args[1:3])
    else:
        # not level given, generate all
        levels = None            

    if len(args) == 0:
        parser.print_help()
        sys.exit(-1)

    for key in fnmatch.filter(svc.layers.keys(), args[0]):
        seed(svc, svc.layers[key], levels=levels, bbox=bboxlist,
             skip_empty=options.skip_empty, padding=options.padding,
             force = options.force, reverse = options.reverse,
             dataProjectionString = options.dataProjectionString,
             tilesProjectionString = options.tilesProjectionString)
        
    svc.teardown()
                
if __name__ == "__main__":
    main()
#     # see http://docs.python.org/library/profile.html
#     import cProfile
#     import pstats
#     cProfile.run('main()', 'seed')
#     p = pstats.Stats('seed')
#     p.strip_dirs().sort_stats('time').print_stats(20)
