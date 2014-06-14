import uuid

class DBUnimplementedError(Exception) : pass

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
        self.threads[uuid_val] = dbname
        return dbid
    
    def insert(self,dbid):
        raise NotImplementedError
    
    def find(self, dbid,  query):
        raise NotImplementedError
    
    def match(self,template,data):
        raise NotImplementedError 
    
    
class VigDBFS(DbBaseAPI):
    
    def __init__(self,auditroot='/nas/reg/log/jiralab/vigilante/auditor'
                 , tlroot='/nas/reg/log/jiralab/vigilante/template_library'):
        self.auditroot_path = auditroot
        self.templib_path = tlrootl
        super(VigDBFS,self).__init__()

    def login(self,space="collector"):
        if space in ("collector", "template_library"):
            return super(VigDBFS,self).login(space)
        else :
            raise DBUnimplementedError
    
    
    
    