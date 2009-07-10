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
    if status != mapscript.MS_SUCCESS:
        layerObj.close()
        raise mapscript.MapServerError('error while querying layer')

    shapes = []
    shape = layerObj.nextShape()
    while shape:
        shapes.append(shape)
        shape = layerObj.nextShape()
    layerObj.close()

    return shapes

def raster_shapes(layerObj, extent=None):    
    tileindex = os.path.join(layerObj.map.shapepath, layerObj.tileindex + ".shp")
    ds = ogr.Open(tileindex)
    layer = ds.GetLayerByIndex(0)
    layer.ResetReading()
    
    tiles = []
    if extent is not None:
        # FIXME: use SetSpatialFilter here
        pass
    tile = layer.GetNextFeature()
    while tile:
        miny, maxy, minx, maxx = tile.GetGeometryRef().GetEnvelope()
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
    done = []
    for layerObj in layersObj:
        for shape in shapes(layerObj, bbox):
            for x, y, z in tcLayer.range(shape.bounds, levels):
                if (x, y, z) not in done:
                    tile = MetaTile(tcLayer, x, y, z)
                    if intersects(shape, tile.bounds()):
                        done.append((x, y, z))
                        yield x, y, z


