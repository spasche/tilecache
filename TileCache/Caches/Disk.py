# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.

import sys
import os
import time
import warnings
from TileCache.Cache import Cache

class Disk (Cache):

    default_structure = 'disk'

    def __init__ (self, base = None, umask = '002', **kwargs):
        Cache.__init__(self, **kwargs)
        self.basedir = base
        self.umask = int(umask, 0)
        
        if sys.platform.startswith("java"):
            from java.io import File
            self.file_module = File
            self.platform = "jython"
        else:
            self.platform = "cpython"
        
        if not self.access(base, 'read'):
            self.makedirs(base)
        
    def makedirs(self, path, hide_dir_exists=True):
        if hasattr(os, "umask"):
            old_umask = os.umask(self.umask)
        try:
            os.makedirs(path)
        except OSError, E:
            # os.makedirs can suffer a race condition because it doesn't check
            # that the directory  doesn't exist at each step, nor does it
            # catch errors. This lets 'directory exists' errors pass through,
            # since they mean that as far as we're concerned, os.makedirs
            # has 'worked'
            if E.errno != 17 or not hide_dir_exists:
                raise E
        if hasattr(os, "umask"):
            os.umask(old_umask)
        
    def access(self, path, type='read'):
        if self.platform == "jython":
            if type == "read":
                return self.file_module(path).canRead()
            else:
                return self.file_module(path).canWrite()
        else:
            if type =="read":
                return os.access(path, os.R_OK)
            else:
                return os.access(path, os.W_OK)

    def get (self, tile):
        filename = os.path.join(self.basedir, self.getKey(tile))
        if self.access(filename, 'read'):
            tile.data = file(filename, "rb").read()
            return tile.data
        else:
            return None

    def set (self, tile, data, force=False):
        if self.readonly and not force: return data
        filename = os.path.join(self.basedir, self.getKey(tile))
        dirname  = os.path.dirname(filename)
        if not self.access(dirname, 'write'):
            self.makedirs(dirname)
        tmpfile = filename + ".%d.tmp" % os.getpid()
        if hasattr(os, "umask"):
            old_umask = os.umask(self.umask)
        output = file(tmpfile, "wb")
        output.write(data)
        output.close()
        if hasattr(os, "umask"):
            os.umask( old_umask );
        try:
            os.rename(tmpfile, filename)
        except OSError:
            os.unlink(filename)
            os.rename(tmpfile, filename)
        tile.data = data
        return data
    
    def delete (self, tile):                
        if not self.readonly:
            filename = os.path.join(self.basedir, self.getKey(tile))
            if self.access(filename, 'read'):
                os.unlink(filename)

    def getLockName (self, tile):
        return os.path.join(self.basedir, self.getKey(tile) + ".lck")

    def attemptLock (self, tile):
        name = self.getLockName(tile)
        try: 
            self.makedirs(name, hide_dir_exists=False)
            return True
        except OSError:
            pass
        try:
            st = os.stat(name)
            if st.st_ctime + self.stale < time.time():
                warnings.warn("removing stale lock %s" % name)
                # remove stale lock
                self.unlock(tile)
                self.makedirs(name)
                return True
        except OSError:
            pass
        return False 
     
    def unlock (self, tile):
        name = self.getLockName(tile)
        try:
            os.rmdir(name)
        except OSError, E:
            print >>sys.stderr, "unlock %s failed: %s" % (name, str(E))
