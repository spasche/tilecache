# BSD Licensed, Copyright (c) 2006-2008 MetaCarta, Inc.

import time
from boto import s3
from TileCache.Cache import Cache

class AWSS3(Cache):

    default_structure = 's3'
    
    def __init__ (self, access_key, secret_access_key, bucket_name=None, location=None, policy=None, **kwargs):
        Cache.__init__(self, **kwargs)
        if policy in s3.acl.CannedACLStrings:
            self.policy = policy
        else:
            self.policy = 'private'
            
        self.bucket_name = bucket_name or "%s-tilecache" % access_key.lower() 
        self.cache = self.s3.connection.S3Connection(access_key, secret_access_key)
        self.bucket = self.cache.lookup(self.bucket_name)
        if not self.bucket:
            self.bucket = self.cache.create_bucket(self.bucket_name, location=location, policy=self.policy)
    
    def getBotoKey(self, key):
        boto_key = self.s3.key.Key(self.bucket)
        boto_key.key = key
        return boto_key

    def get(self, tile):
        key = self.getKey(tile)
        tile.data = self.getObject(key)
        return tile.data
    
    def getObject(self, key):
        try:
            data = self.getBotoKey(key).get_contents_as_string()
        except:
            data = None
        self.bucket.connection.connection.close()    
        return data
        
    def set(self, tile, data):
        if self.readonly:
            return data
        else:
            key = self.getKey(tile)
            self.setObject(key, data)
            return data
    
    def setObject(self, key, data):
        self.getBotoKey(key).set_contents_from_string(data, policy=self.policy)
        self.bucket.connection.connection.close()    
    
    def delete(self, tile):
        if not self.readonly:
            key = self.getKey(tile)
            self.deleteObject(key)
    
    def deleteObject(self, key):
        self.getBotoKey(key).delete()
            
    def getLockName (self, tile):
        return "lock-%s" % self.getKey(tile)
    
    def attemptLock (self, tile):
        data = self.getObject(self.getLockName(tile))
        if not data:
            self.setObject(self.getLockName(tile), str(time.time() + self.timeout))
            return True
    
    def unlock (self, tile):
        self.deleteObject( self.getLockName(tile) )
    
    def keys (self, options = {}):
        prefix = "" 
        if options.has_key('prefix'):
            prefix = options['prefix']
        response = self.bucket.list(prefix=prefix)
        return [k.key for k in response]

if __name__ == "__main__":
    import sys
    from optparse import OptionParser
    parser = OptionParser(usage="""%prog [options] action    
    action is one of: 
      list_locks
      count_tiles
      show_tiles
      delete <object_key> or <list>,<of>,<keys>
      delete_tiles""")
    parser.add_option('-z', dest='zoom', help='zoom level for count_tiles (requires layer name)')  
    parser.add_option('-l', dest='layer', help='layer name for count_tiles')  
    parser.add_option('-k', dest='key', help='access key for S3')  
    parser.add_option('-s', dest='secret', help='secret access key for S3') 
    
    (options, args) = parser.parse_args()
    if not options.key or not options.secret or not args:
        parser.print_help()
        sys.exit()
    
    def create_prefix(options):
        prefix = "" 
        if options.layer:
            prefix = "%s-" % options.layer 
            if options.zoom:
                prefix = "%s%s-" % (prefix, options.zoom)
        return prefix        
    
    # Debug mode. 
    a = AWSS3(options.key, 
              options.secret)
    if args[0] == "list_locks":           
        print ','.join(a.keys({'prefix':'lock-'}))
    elif args[0] == "list_keys":
        print ','.join(a.keys())
    elif args[0] == "count_tiles" or args[0] == "show_tiles":
        opts = { 
            'prefix': create_prefix(options)
        }
        if args[0] == "show_tiles":
            print ",".join(a.keys(opts))
        else:
            print len(a.keys(opts))
    elif args[0] == "delete":
        for key in args[1].split(","):
            a.deleteObject(key)
    elif args[0] == "delete_tiles":
        opts = { 
            'prefix': create_prefix(options)
        }
        keys = a.keys(opts)
        val = raw_input("Are you sure you want to delete %s tiles? (y/n) " % len(keys))
        if val.lower() in ['y', 'yes']:
            for key in keys:
                a.deleteObject(key)
            
    else:
        parser.print_help() 
        
