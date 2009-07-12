import mapscript
import time
from TileCache.Utils.MapScript import getLayersByName, tiles
from TileCache.Layer import Tile

def seed(service, layer, levels=None, bbox=None, skip_empty=True, padding=0, force=False, reverse=False):
    if levels is None:
        levels = (0, len(layer.resolutions))
    else:
        levels[0] = max(0, levels[0])
        levels[1] = min(len(layer.resolutions), levels[1])
        
    if bbox is None:
        bbox = layer.bbox

    if skip_empty and hasattr(layer, 'mapfile'):
        # a mapserver layer
        mapObj = mapscript.mapObj(layer.mapfile)
        layersObj = []
        for layerName in layer.layers.split(','):
            layersObj.extend(getLayersByName(mapObj, layerName))

        # metaSize, reverse, padding not managed
        for x, y, z in tiles(layersObj, layer, bbox, levels):
            start = time.time()
            tile = Tile(layer, x, y, z)
            service.renderTile(tile, force=force)
            print "['%s'] (x: %04d, y: %04d, z: %04d) in %4fs"%(layer.name, x, y, z, time.time() - start)

    else:
        for z in range(*levels):
            minx, miny, _ = layer.getClosestCell(z, bbox[0:2])
            maxx, maxy, _ = layer.getClosestCell(z, bbox[2:4])
            metax, metay = layer.getMetaSize(z)

            startx = minx - (1 * padding)
            endx = maxx + metax + (1 * padding)
            starty = miny - (1 * padding)
            endy = maxy + metay + (1 * padding)

            if reverse:
                startx, endx = endx, startx
                starty, endy = endy, starty
                metax = -metax
                metay = -metay

            for y in range(starty, endy, metay):
                for x in range(startx, endx, metax):
                    start = time.time()
                    tile = Tile(layer, x, y, z)
                    service.renderTile(tile, force=force)
                    print "['%s'] (x: %04d, y: %04d, z: %04d) in %4fs"%(layer.name, x, y, z, time.time() - start)
