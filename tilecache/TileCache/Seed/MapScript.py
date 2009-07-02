import mapscript

def valid_rectObj(rectObj):
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



