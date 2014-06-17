import uuid
import re
import json
import os.path

class DBUnimplementedError(Exception) : pass
class DBIDnotpresentError(Exception) : pass

class DbBaseAPI(object):
    """This is a Base or Abstract class and is not meant to be instantiated
    or used directly.

    The DbBaseAPI object defines a set of methods that can be
    reused across different versions of the  API. If querying for a
    certain resource is done in an identical fashion across different versions
    it will be implemented here and should be overridden in their respective
    versions if they deviate.  So currently the implementation supports the filesystem
    based database for vigilante, but you could easily create classes for puppetdb and 
    mongo db back ends.


    """
    def __init__(self, host='localhost', timeout=10):
        """Initialises our BaseAPI object passing the parameters needed in
        order to be able to create the connection strings """

        self.api_version = "v0.1"
        self.host = host
        self.timeout = timeout
        self.threads = {}

    @property
    def version(self):
        """The version of the API we're querying against.

        :returns: Current API version.
        :rtype: :obj:`string`"""
        return self.api_version
    
    def login(self, dbname):
        dbid = uuid.uuid1()
        self.threads[dbid] = dbname
        return dbid
    
    def insert(self,dbid, insert_dict):
        raise NotImplementedError

    def find_one(self, dbid,  query_dict):
        raise NotImplementedError
        
    def find(self, dbid,  query_dict):
        raise NotImplementedError
    
    def match(self,template_dict,data_dict):
        raise NotImplementedError 
    
    
class VigDBFS(DbBaseAPI):
    
    def __init__(self,auditroot='/nas/reg/log/jiralab/vigilante/auditor'
                 , tlroot='/nas/reg/log/jiralab/vigilante/template_library'):
        self.auditroot_path = auditroot
        self.templib_path = tlroot
        super(VigDBFS,self).__init__()

    def login(self,space="collector"):
        if space in ("collector", "template_library"):
            return super(VigDBFS,self).login(space)
        else :
            raise DBUnimplementedError
    
    def find_one(self, dbid,  query_dict):
        if dbid not in self.threads :
            raise DBIDnotpresentError
        dbtype = self.threads[dbid]
        return_dict = {}
        if dbtype == "collector":
            name = query_dict["fqdn"]
            if "iso8601" not in query_dict:
                timestamp = "current"
            else:
                timestamp = query_dict["iso8601"]
            m = re.match( r"([^\.]+)\.([^\.]+)\.com", name )
            hostname = m.group( 1 )
            m = re.match( r"(^[A-z]+[0-9]{2})", hostname)
            envid = m.group(1)
            if timestamp == "current":
                result_path = "%s/%s/%s/current" % ( self.auditroot_path, envid, hostname)
                if ( os.path.isfile( result_path ) ):
                    return_dict = json.loads( open( result_path ).read() )
        elif dbtype == "template_library":
            pass
        return return_dict
        
if __name__ == "__main__" :
    s= VigDBFS()
    collector =  s.login()
    rs = s.find_one(collector, {"fqdn" : "sctv00pup001.cybertribe.com",})