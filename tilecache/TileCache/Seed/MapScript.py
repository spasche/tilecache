import mapscript
from TileCache.Layer import MetaTile

def valid_extent(rectObj):
    """ return whatever 'rectObj' represents a valid extent """
    return rectObj.minx != -1 and rectObj.miny != -1 and \
           rectObj.maxx != -1 and rectObj.maxy != -1

def shapes(layerObj, extent=None):
    """ return all the shapes from 'layerObj' inside 'extent' """
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

def getCell():
    raise NotImplementedError('move to Layer')

def grid(tcLayer, extent):
    """ yield all the tiles indexes (x, y, z) for the given extent and for all the layer resolutions """
    for z in range(tcLayer.resolutions):
        xbuffer, ybuffer = tcLayer.getMetaBufferSize(z)
        minx, miny = getCell(tcLayer, bbox.minx - xbuffer, bbox.miny - ybuffer, z)
        maxx, maxy = getCell(tcLayer, bbox.maxx + xbuffer, bbox.maxy + ybuffer, z)
        for x in range(minx, maxx + 1):
            for y in range(miny, maxy + 1):
                yield x, y, z

def tiles(layersObj, tcLayer):
    """ yield all non empty tiles indexes (x, y, z) """
    done = set()
    for layerObj in layersObj:
        for shape in shapes(layerObj):
            for x, y, z in grid(tcLayer, shape.bounds):
                tile = MetaTile(tcLayer, x, y, z)
                if intersects(shape, tile.bounds()):
                    done.add((x, y, z))
                    yield x, y, z


