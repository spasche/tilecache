import mapscript
import time
from MapScript import getLayersByName, tiles

def seed(service, layer, skip_empty=True, levels=None, bbox=None, padding=0, force=False, reverse=False):
    if skip_empty and hasattr(layer, 'mapfile'):
        # a mapserver layer
        mapObj = mapscript.mapObj(layer.mapfile)
        layersObj = []
        for layerName in layer.layers.split(','):
            for layerObj in getLayersByName(mapObj, layerName):
                if layerObj.type == mapscript.MS_RASTER:
                    # FIXME: find all the raster bbox from the tileindex
                    pass
                else:
                    layersObj.append(layerObj)
    else:
        # fallback to the default mode
        skip_empty = False

    if skip_empty:
        for x, y, z in tiles(layersObj, layer):
            start = time.time()
            tile = Tile(layer, x, y, z)
            service.renderTile(tile, force=force)
            print "['%s'] (x: %04d, y: %04d, z: %04d) in %4fs"%(layer.name, x, y, z, time.time() - start))
            
    else:
        # call the 'old' function
        pass
