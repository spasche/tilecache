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
    rect = rectObj
    return shapeObj.intersects(rect.toPolygon()) == mapscript.MS_TRUE

def getLayersByName(mapObj, name):
    """ just like mapObj.getLayerByName but take the layer.group into account """
    layers = []
    for layer in [mapObj.getLayer(l) for l in range(mapObj.numlayers)]:
        if layer.name == name or layer.group == name:
            layers.append(layer)
    return layers

def projectArray(rect, source, dest):
    if (source != None and dest != None):
	reporjected = mapscript.rectObj(rect[0], rect[1], rect[2], rect[3])
        reporjected.project(source, dest)
        return [reporjected.minx, reporjected.miny, reporjected.maxx, reporjected.maxy]
    else:
        return rect

def projectRect(rect, source, dest):
    if (source != None and dest != None):
        reporjected = mapscript.rectObj(rect.minx, rect.miny, rect.maxx, rect.maxy)
        reporjected.project(source, dest)
        return reporjected
    else:
        return rect

def tiles(layersObj, tcLayer, bbox=None, levels=None, dataProjectionString=None, tilesProjectionString=None):
    dataProj = None
    if (dataProjectionString != None):
        print("Data projection: %s"%dataProjectionString)
        dataProj = mapscript.projectionObj(dataProjectionString)

    tilesProj = None
    if (tilesProjectionString != None):
        print("Tiles projection: %s"%tilesProjectionString)
        tilesProj = mapscript.projectionObj(tilesProjectionString)
    elif (tcLayer.srs != None and tcLayer.srs != ""):
        print("Tiles projection: %s"%tcLayer.srs)
        tilesProj = mapscript.projectionObj("+init=" + tcLayer.srs.lower())

    """ yield all non empty tiles indexes (x, y, z) """
    pad = pack('x')
    done = {}
    for layerObj in layersObj:
        if (dataProj == None and layerObj.map.getProjection() != ""):
            print("Data projection: %s"%layerObj.map.getProjection())
            dataProj = mapscript.projectionObj(layerObj.map.getProjection())

        for shapeObj in shapes(layerObj, projectArray(bbox, tilesProj, dataProj)): # reprojet bbox tiles -> data
            for x, y, z in tcLayer.range(projectRect(shapeObj.bounds, dataProj, tilesProj), levels):   # first filter using shapes bbox, reprojet bounds data -> tiles
                key = pack('3i', x, y, z)
                if key not in done:
                    tile = MetaTile(tcLayer, x, y, z)
                    # FIXME: handle metaSize
                    rect = mapscript.rectObj(*tile.bufferbounds())
                    if intersects(shapeObj, projectRect(rect, tilesProj, dataProj)):    # second filter using shapes geometry, reprojet bufferbounds tiles -> data
                        done[key] = pad
                        yield layerObj, shapeObj, x, y, z

