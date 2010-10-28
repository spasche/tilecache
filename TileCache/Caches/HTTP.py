from urllib2 import Request, urlopen
from urlparse import urljoin
from TileCache.Cache import Cache

class HTTP(Cache):
    default_structure = 'disk'

    def __init__(self, url=None, referer='http://map.geo.admin.ch/', **kwargs):
        Cache.__init__(self, **kwargs)
        self.host = url
        self.readonly = True
        self.headers = {'Referer': referer}

    def get(self, tile):
        request = Request(urljoin(self.host, self.getKey(tile)),
                          headers=self.headers)
        try:
            response = urlopen(request)
        except IOError:
            return None
        else:
            return response.read()
