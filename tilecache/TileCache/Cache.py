# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.
import time
import os

class Cache (object):
    def __init__ (self, timeout = 30.0, stale_interval = 300.0, readonly = False, structure=None, **kwargs):
        self.stale = float(stale_interval)
        self.timeout = float(timeout)

        if structure is None:
            # default_structure is defined is child classes
            self.structure = self.default_structure
        else:
            self.structure = structure.lower()
            
        if isinstance(readonly, str):
            self.readonly = readonly.lower() in ["yes", "y", "t", "true"]
        else:
            self.readonly = readonly
                
    def lock (self, tile, blocking = True):
        start_time = time.time()
        result = self.attemptLock(tile)
        if result:
            return True
        elif not blocking:
            return False
        while result is not True:
            if time.time() - start_time > self.timeout:
                raise Exception("You appear to have a stuck lock. You may wish to remove the lock named:\n%s" % self.getLockName(tile)) 
            time.sleep(0.25)
            result = self.attemptLock(tile)
        return True

    def getLockName (self, tile):
        return self.getKey(tile) + ".lck"

    def getKey (self, tile):
        if self.structure == 'disk':
            return os.path.join(self.basedir,
                                tile.layer.name,
                                "%02d" % int(tile.z),
                                "%03d" % int(tile.x / 1000000),
                                "%03d" % (int(tile.x / 1000) % 1000),
                                "%03d" % (int(tile.x) % 1000),
                                "%03d" % int(tile.y / 1000000),
                                "%03d" % (int(tile.y / 1000) % 1000),
                                "%03d.%s" % (int(tile.y) % 1000, tile.layer.extension))

        elif self.structure == 'tms':
            return os.path.join("1.0.0",
                                tile.layer.name,
                                "%s" % int(tile.z),
                                "%s" % int(tile.x),
                                "%s.%s" % (int(width - 1 - tile.y), tile.layer.extension))
        
        elif self.structure == 'flipped-tms':
            width, _ = tile.layer.grid(tile.z)
            return os.path.join("1.0.0",
                                tile.layer.name,
                                "%s" % int(tile.z),
                                "%s" % int(tile.x),
                                "%s.%s" % (tile.y, tile.layer.extension))
            
        elif self.structure == 'google':
            width, _ = tile.layer.grid(tile.z)
            return os.path.join(self.basedir,
                                tile.layer.name,
                                "%s" % int(tile.z),
                                "%s" % int(tile.x),
                                "%s.%s" % (int(width - 1 - tile.y), tile.layer.extension))        

        elif self.structure == 's3':
            return "-".join(map(str, [tile.layer.name, tile.z , tile.x, tile.y]))
    
        elif self.structure == 'memcached':
            return "/".join(map(str, [tile.layer.name, tile.x, tile.y, tile.z]))
        else:
            raise NotImplementedError("unknown structure '%s'"%self.structure)

    def attemptLock (self, tile):
        raise NotImplementedError()

    def unlock (self, tile):
        raise NotImplementedError()

    def get (self, tile):
        raise NotImplementedError()

    def set (self, tile, data):
        raise NotImplementedError()
    
    def delete(self, tile):
        raise NotImplementedError()
