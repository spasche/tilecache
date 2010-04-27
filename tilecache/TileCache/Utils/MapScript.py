import os
from struct import pack
from osgeo import ogr, gdal
import mapscript
from TileCache.Layer import MetaTile

def valid_extent(rectObj):
    """ return whatever 'rectObj' represents a valid extent """
    return rectObj.minx != -1 and rectObj.miny != -1 and \
           rectObj.maxx != -1 and rectObj.maxy != -1

def shapes(layerObj, extent=None):
    if layerObj.type == mapscript.MS_LAYER_RASTER:
        return raster_shapes(layerObj, extent)
    else:
        return vector_shapes(layerObj, extent)

def vector_shapes(layerObj, extent=None):
    """ return all the shapes from 'layerObj' inside 'extent' """
    if extent is None:
        if valid_extent(layerObj.extent):
            extent = layerObj.extent
        else:
            extent = layerObj.map.extent
    else:
        extent = mapscript.rectObj(*extent)

    layerObj.open()
    status = layerObj.whichShapes(extent)
    if status == mapscript.MS_SUCCESS:
        shapes = []
        shape = layerObj.nextShape()
        while shape:
            shapes.append(shape)
            shape = layerObj.nextShape()
        layerObj.close()
        return shapes

    elif status == mapscript.MS_FAILURE:
        raise mapscript.MapServerError("error while querying layer: '%s'"%layerObj.name)

    elif status == mapscript.MS_DONE:
        # extent and shapefile don't overlap
        layerObj.close()
        return []
    
    else:
        raise mapscript.MapServerError("unknown status returned by whichShapes: '%s'"%status)

def raster_shapes(layerObj, extent=None):
    if layerObj.tileindex is None:
        # no tileindex, use DATA
        filename = os.path.join(layerObj.map.shapepath, layerObj.data)
        layer = gdal.Open(filename, gdal.GA_ReadOnly)

        geotransform = layer.GetGeoTransform()
        minx = geotransform[0]
        maxy = geotransform[3]
        miny = maxy + layer.RasterYSize * geotransform[5]
        maxx = minx + layer.RasterXSize * geotransform[1]

        return [mapscript.rectObj(minx, miny, maxx, maxy).toPolygon()]
    else:
        filename = os.path.join(layerObj.map.shapepath, layerObj.tileindex + ".shp")
        ds = ogr.Open(filename)
        layer = ds.GetLayerByIndex(0)
        layer.ResetReading()

        if extent is not None:
            layer.SetSpatialFilterRect(*extent)

        tiles = []
        tile = layer.GetNextFeature()
        while tile:
            minx, maxx, miny, maxy = tile.GetGeometryRef().GetEnvelope() # WTF ?
            tiles.append(mapscript.rectObj(minx, miny, maxx, maxy).toPolygon())
            tile = layer.GetNextFeature()
        ds.Destroy()

        return tiles

def intersects(shapeObj, rectObj):
    """ return whatever 'shapeObj' and 'rectObj' intersect """
    rect = mapscript.rectObj(*rectObj)
    return shapeObj.intersects(rect.toPolygon()) == mapscript.MS_TRUE

def getLayersByName(mapObj, name):
    """ just like mapObj.getLayerByName but take the layer.group into account """
    layers = []
    for layer in [mapObj.getLayer(l) for l in range(mapObj.numlayers)]:
        if layer.name == name or layer.group == name:
            layers.append(layer)
    return layers

def tiles(layersObj, tcLayer, bbox=None, levels=None):
    """ yield all non empty tiles indexes (x, y, z) """
    pad = pack('x')
    done = {}
    for layerObj in layersObj:
        for shapeObj in shapes(layerObj, bbox):
            for x, y, z in tcLayer.range(shapeObj.bounds, levels):
                key = pack('3i', x, y, z)
                if key not in done:
                    tile = MetaTile(tcLayer, x, y, z)
                    # FIXME: handle metaSize
                    if intersects(shapeObj, tile.bufferbounds()):
                        done[key] = pad
                        yield layerObj, shapeObj, x, y, z
