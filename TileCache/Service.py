#!/usr/bin/python

# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.

import sys
import cgi
import time
import os
import traceback
import ConfigParser

from TileCache.Cache import Cache
from TileCache.Utils.ImageMerger import ImageMergeMerger, PILMerger
import Layer

class TileCacheException(Exception):
    pass

# Windows doesn't always do the 'working directory' check correctly.
if sys.platform == 'win32':
    workingdir = os.path.abspath(os.path.join(os.getcwd(), os.path.dirname(sys.argv[0])))
    cfgfiles = (os.path.join(workingdir, "tilecache.cfg"), os.path.join(workingdir,"..","tilecache.cfg"))
else:
    cfgfiles = ("/etc/tilecache.cfg", os.path.join("..", "tilecache.cfg"), "tilecache.cfg")


class Capabilities (object):
    def __init__ (self, format, data):
        self.format = format
        self.data = data

class Request (object):
    def __init__ (self, service):
        self.service = service
    def getLayer(self, layername):    
        if layername in self.service.layers:
            return self.service.layers[layername]
        else:
            raise TileCacheException("The requested layer (%s) does not exist. Available layers are: \n * %s" % (layername, "\n * ".join(self.service.layers.keys()))) 

    
def import_module(name):
    """Helper module to import any module based on a name, and return the module."""
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class Service (object):
    __slots__ = ("layers", "cache", "metadata", "tilecache_options", "config", "files", "image_mergers")

    def __init__ (self, cache, layers, metadata = {}):
        self.cache    = cache
        self.layers   = layers
        self.metadata = metadata
        
        self.image_mergers = []
        for merger_class in [ImageMergeMerger, PILMerger]:
            if merger_class.available():
                self.image_mergers.append(merger_class(self))

    def teardown(self):
        self.cache.teardown()
 
    def _loadFromSection (cls, config, section, module, **objargs):
        type  = config.get(section, "type")
        for opt in config.options(section):
            if opt not in ["type", "module"]:
                objargs[opt] = config.get(section, opt)
        
        object_module = None
        
        if config.has_option(section, "module"):
            object_module = import_module(config.get(section, "module"))
        else: 
            if module is Layer:
                type = type.replace("Layer", "")
                object_module = import_module("TileCache.Layers.%s" % type)
            else:
                type = type.replace("Cache", "")
                object_module = import_module("TileCache.Caches.%s" % type)
        if object_module == None:
            raise TileCacheException("Attempt to load %s failed." % type)
        
        section_object = getattr(object_module, type)
        
        if module is Layer:
            return section_object(section, **objargs)
        else:
            return section_object(**objargs)
    loadFromSection = classmethod(_loadFromSection)

    def _load (cls, *files):
        cache = None
        metadata = {}
        layers = {}
        config = None
        try:
            config = ConfigParser.ConfigParser()
            config.read(files)
            
            if config.has_section("metadata"):
                for key in config.options("metadata"):
                    metadata[key] = config.get("metadata", key)
            
            if config.has_section("tilecache_options"):
                if 'path' in config.options("tilecache_options"): 
                    for path in config.get("tilecache_options", "path").split(","):
                        sys.path.insert(0, path)
            
            cache = cls.loadFromSection(config, "cache", Cache)

            layers = {}
            for section in config.sections():
                if section in cls.__slots__: continue
                layers[section] = cls.loadFromSection(
                                        config, section, Layer, 
                                        cache = cache)
        except Exception, E:
            metadata['exception'] = E
            metadata['traceback'] = "".join(traceback.format_tb(sys.exc_traceback))
        service = cls(cache, layers, metadata)
        service.files = files
        service.config = config
        return service 
    load = classmethod(_load)

    def generate_crossdomain_xml(self):
        """Helper method for generating the XML content for a crossdomain.xml
           file, to be used to allow remote sites to access this content."""
        xml = ["""<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM
  "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
        """]
        if self.metadata.has_key('crossdomain_sites'):
            sites = self.metadata['crossdomain_sites'].split(',')
            for site in sites:
                xml.append('  <allow-access-from domain="%s" />' % site)
        xml.append("</cross-domain-policy>")        
        return ('text/xml', "\n".join(xml))       

    def renderTile (self, tile, force = False):
        # do more cache checking here: SRS, width, height, layers 
        layer = tile.layer
        image = None
        if not force:
            image = self.cache.get(tile)
        if not image and (not self.cache.readonly or force):
            data = layer.render(tile)
            if data:
                image = self.cache.set(tile, data, force)
            else:
                raise Exception("Zero length data returned from layer.")

        return (layer.mime_type, image)

    def dispatchRequest (self, params, path_info="/", req_method="GET", host="http://example.com/"):
        if self.metadata.has_key('exception'):
            raise TileCacheException("%s\n%s" % (self.metadata['exception'], self.metadata['traceback']))
        if path_info.find("crossdomain.xml") != -1:
            return self.generate_crossdomain_xml()

        if path_info.split(".")[-1] == "kml":
            from TileCache.Services.KML import KML 
            return KML(self).parse(params, path_info, host)
        
        if params.has_key("scale") or params.has_key("SCALE"): 
            from TileCache.Services.WMTS import WMTS
            tile = WMTS(self).parse(params, path_info, host)
        elif params.has_key("service") or params.has_key("SERVICE") or \
           params.has_key("REQUEST") and params['REQUEST'] == "GetMap" or \
           params.has_key("request") and params['request'] == "GetMap": 
            from TileCache.Services.WMS import WMS
            tile = WMS(self).parse(params, path_info, host)
        elif params.has_key("L") or params.has_key("l") or \
             params.has_key("request") and params['request'] == "metadata":
            from TileCache.Services.WorldWind import WorldWind
            tile = WorldWind(self).parse(params, path_info, host)
        elif params.has_key("interface"):
            from TileCache.Services.TileService import TileService
            tile = TileService(self).parse(params, path_info, host)
        elif params.has_key("v") and \
             (params['v'] == "mgm" or params['v'] == "mgmaps"):
            from TileCache.Services.MGMaps import MGMaps 
            tile = MGMaps(self).parse(params, path_info, host)
        elif params.has_key("tile"):
            from TileCache.Services.VETMS import VETMS 
            tile = VETMS(self).parse(params, path_info, host)
        elif params.has_key("format") and params['format'].lower() == "json":
            from TileCache.Services.JSON import JSON 
            return JSON(self).parse(params, path_info, host)
        else:
            from TileCache.Services.TMS import TMS
            tile = TMS(self).parse(params, path_info, host)
        
        if isinstance(tile, Layer.Tile):
            # <shameful part>
            # was:
            #return self.renderTile(tile, params.has_key('FORCE'))
            format, data = self.renderTile(tile, params.has_key('FORCE'))
            return (format, postprocess(data, format, params))
            # </shameful part>
        elif isinstance(tile, list):
            tiles = tile
            assert len(tiles) > 0, "No tiles to merge"

            if len(self.image_mergers) == 0:
                raise Exception("You need either python-image-merge or "
                                "Python Imaging Library for combining "
                                "multiple layers")

            merger = self.image_mergers[0]
            # <shameful part>
            # was:
            #return merger.merge(tiles, params)
            format, data = merger.merge(tiles, params)
            return (format, postprocess(data, format, params))
            # </shameful part>
        else:
            # text (xml, json, ...) output
            # FIXME: possible bug here: this is not a tile instance so no format and data attributes
            return (tile.format, tile.data)

# <shameful part>
# On the fly image conversion.
# Only here because IE <= 6.0 can't handle RGBA png.
def postprocess(data, format, params):
    if params.has_key('FORMAT'):
        request_format = params['FORMAT'].lower()
    else:
        request_format = format

    request_extension = request_format.split('/')[1]    
    if request_extension not in format:
        from tempfile import mkstemp
        import os
        (inhandle, inpath) = mkstemp()
        os.write(inhandle, data)
        os.close(inhandle)
        
        outfile = inpath + '.' + request_extension
        os.system('convert %s %s' % (inpath, outfile))
        data = file(outfile, 'rb').read()
        
        os.remove(inpath)
        os.remove(outfile)

        return data
    else:
        return data
# </shameful part>

def modPythonHandler (apacheReq, service):
    from mod_python import apache, util
    try:
        if apacheReq.prev:
            path_info = apacheReq.prev.uri
        else:
            path_info = apacheReq.path_info
        
        if apacheReq.headers_in.has_key("X-Forwarded-Host"):
            host = "http://" + apacheReq.headers_in["X-Forwarded-Host"]
        else:
            host = "http://" + apacheReq.headers_in["Host"]
        host += apacheReq.uri[:-len(path_info)]
        format, image = service.dispatchRequest( 
                                util.FieldStorage(apacheReq), 
                                path_info,
                                apacheReq.method,
                                host )
        apacheReq.content_type = format
        if image is None:
            apacheReq.status = apache.HTTP_NO_CONTENT
        else:
            apacheReq.status = apache.HTTP_OK
        apacheReq.send_http_header()
        apacheReq.write(image or '')
    except TileCacheException, E:
        apacheReq.content_type = "text/plain"
        apacheReq.status = apache.HTTP_NOT_FOUND
        apacheReq.send_http_header()
        apacheReq.write("An error occurred: %s\n" % (str(E)))
    except Exception, E:
        apacheReq.content_type = "text/plain"
        apacheReq.status = apache.HTTP_INTERNAL_SERVER_ERROR
        apacheReq.send_http_header()
        apacheReq.write("An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback))))
    return apache.OK

def wsgiHandler (environ, start_response, service):
    from paste.request import parse_formvars
    try:
        path_info = host = ""


        if "PATH_INFO" in environ: 
            path_info = environ["PATH_INFO"]

        if "HTTP_X_FORWARDED_HOST" in environ:
            host      = "http://" + environ["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in environ:
            host      = "http://" + environ["HTTP_HOST"]

        host += environ["SCRIPT_NAME"]
        req_method = environ["REQUEST_METHOD"]
        fields = parse_formvars(environ)

        format, image = service.dispatchRequest( fields, path_info, req_method, host )
        start_response("200 OK", [('Content-Type',format)])
        return [image]

    except TileCacheException, E:
        start_response("404 Tile Not Found", [('Content-Type','text/plain')])
        return ["An error occurred: %s" % (str(E))]
    except Exception, E:
        start_response("500 Internal Server Error", [('Content-Type','text/plain')])
        return ["An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback)))]

def cgiHandler (service):
    try:
        params = {}
        input = cgi.FieldStorage()
        for key in input.keys(): params[key] = input[key].value
        path_info = host = ""

        if "PATH_INFO" in os.environ: 
            path_info = os.environ["PATH_INFO"]

        if "HTTP_X_FORWARDED_HOST" in os.environ:
            host      = "http://" + os.environ["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in os.environ:
            host      = "http://" + os.environ["HTTP_HOST"]

        host += os.environ["SCRIPT_NAME"]
        req_method = os.environ["REQUEST_METHOD"]
        format, image = service.dispatchRequest( params, path_info, req_method, host )
        print "Content-type: %s\n" % format

        if sys.platform == "win32":
            binaryPrint(image)
        else:    
            print image
    except TileCacheException, E:
        print "Cache-Control: max-age=10, must-revalidate" # make the client reload        
        print "Content-type: text/plain\n"
        print "An error occurred: %s\n" % (str(E))
    except Exception, E:
        print "Cache-Control: max-age=10, must-revalidate" # make the client reload        
        print "Content-type: text/plain\n"
        print "An error occurred: %s\n%s\n" % (
            str(E), 
            "".join(traceback.format_tb(sys.exc_traceback)))

theService = {}
lastRead = {}
def handler (apacheReq):
    global theService, lastRead
    options = apacheReq.get_options()
    cfgs    = cfgfiles
    fileChanged = False
    if options.has_key("TileCacheConfig"):
        configFile = options["TileCacheConfig"]
        lastRead[configFile] = time.time()
        
        cfgs = cfgs + (configFile,)
        try:
            cfgTime = os.stat(configFile)[8]
            fileChanged = lastRead[configFile] < cfgTime
        except:
            pass
    else:
        configFile = 'default'
        
    if not theService.has_key(configFile) or fileChanged:
        theService[configFile] = Service.load(*cfgs)
        
    return modPythonHandler(apacheReq, theService[configFile])

def wsgiApp (environ, start_response):
    global theService
    cfgs    = cfgfiles
    if not theService:
        theService = Service.load(*cfgs)
    return wsgiHandler(environ, start_response, theService)

def binaryPrint(binary_data):
    """This function is designed to work around the fact that Python
       in Windows does not handle binary output correctly. This function
       will set the output to binary, and then write to stdout directly
       rather than using print."""
    try:
        import msvcrt
        msvcrt.setmode(sys.__stdout__.fileno(), os.O_BINARY)
    except:
        pass
    sys.stdout.write(binary_data)    

def paste_deploy_app(global_conf, full_stack=True, **app_conf):
    if 'tilecache_config' in app_conf:
        cfgfiles = (app_conf['tilecache_config'],)
    else:
        raise TileCacheException("No tilecache_config key found in configuration. Please specify location of tilecache config file in your ini file.")
    theService = Service.load(*cfgfiles)
    if 'exception' in theService.metadata:
        raise theService.metadata['exception']
    
    def pdWsgiApp (environ,start_response):
        return wsgiHandler(environ,start_response,theService)
    
    return pdWsgiApp

if __name__ == '__main__':
    svc = Service.load(*cfgfiles)
    cgiHandler(svc)
