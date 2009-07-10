import mapscript
from TileCache.Layer import MetaTile

def valid_extent(rectObj):
    """ return whatever 'rectObj' represents a valid extent """
    return rectObj.minx != -1 and rectObj.miny != -1 and \
           rectObj.maxx != -1 and rectObj.maxy != -1

# def shapes(layerObj, extent=None):
#     # FIXME: extent
#     tileindex = os.path.join(layerObj.map.shapepath, layerObj.tileindex + ".shp")
#     ds = ogr.Open(tileindex)
#     layer = ds.GetLayerByIndex(0) # ?
#     tile = layer.GetNextFeature()
#     while tile:
#         miny, maxy, minx, maxx = tile.GetGeometryRef().GetEnvelope()
#         yield mapscript.rectObj(minx, miny, maxx, maxy).toPolygon()
#         tile = layer.GetNextFeature()
#     ds.Destroy()

def shapes(layerObj, extent=None):
    """ return all the shapes from 'layerObj' inside 'extent' """
    # convert the extent to a rectObj if needed
    if extent is not None and not isinstance(extent, mapscript.rectObj):
        extent = mapscript.rectObj(*extent)

    if extent is None or not valid_extent(extent):
        if valid_extent(layerObj.extent):
            extent = layerObj.extent
        else:
            extent = layerObj.map.extent

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


