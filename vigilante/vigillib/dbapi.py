import uuid
import re
import json
import yaml
import os.path
import sys
import collections
from os import listdir
from datetime import datetime, timedelta

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
    
    def match(self, tdbid, template_dict, cdbid, data_dict):
        """
        Match strategy: If the template value of a key is "None",
        then any data value is a match. If the template value is a 
        scalar (not a list) then the value is interpreted as a string
        and only an exact match is considered a match.  If the template
        value is a list, then the first element of the list is an
        operator and the following arguments are the operands. Roles
        templates match their body keys to collector data on a 1-to-1
        basis.  Env templates iterate through the keys in the body and
        calls match on each role lookup found.
        """
        raise NotImplementedError
    
    def _update(self,d, u):
        for k, v in u.iteritems():
            if isinstance(v, collections.Mapping):
                r = self._update(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

    def _resolve_template(self,dbid,template_dict):
        super = template_dict["meta"]["super"]
        if not super or (super == "none") or (super == "None"):
            return template_dict
        else:
            next_template = self.find_one(dbid,{"name" : super})
            merged_template = self._resolve_template(dbid, next_template)
            return self._update(merged_template, template_dict)
    
class VigDBFS(DbBaseAPI):
    """ This is the current implementation that store data in the file system.
    Don't call this implementation dependent class, use the generic wrapper instead.
    
    """
    
    def __init__(self,auditroot='/nas/reg/log/jiralab/vigilante/auditor'
                 , tlroot='/nas/reg/log/jiralab/vigilante/template_library'):
        self.auditroot_path = auditroot
        self.templib_path = tlroot
        super(VigDBFS,self).__init__()

    def login(self,space="collector"):
        """ There are currently two possible databases, the "collector" database which holds raw data
        gathered from the Environments, and the "template_library" which contains JSON templates that
        are used in matching operations 
        """
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
            name = query_dict["name"]
            result_path = "%s/%s.yaml" % (self.templib_path, name)
            if ( os.path.isfile( result_path ) ):
                    return_dict = yaml.load(open( result_path ).read() )
        return return_dict

    def find(self, dbid, query_dict):
        if dbid not in self.threads :
            raise DBIDnotpresentError
        dbtype = self.threads[dbid]
        return_dict = {}
        if dbtype == "collector":
            if "iso8601" not in query_dict:
                timestamp = "current"
            else:
                timestamp = query_dict["iso8601"]
            envid = query_dict["domain"]
            m = re.match( r"(^[A-z]+[0-9]{2})", envid)
            return_dict[ 'envid' ] = envid
            result_set_path = "%s/%s" % ( self.auditroot_path, envid )
            env_role_paths = [ role_path for role_path in listdir( result_set_path ) if os.path.isdir( os.path.join( result_set_path, role_path ) ) ]
            for role_path in env_role_paths:
                file_dict = self._find_file_in_time( os.path.join( result_set_path, role_path ), timestamp )
                role_facter_in_time_range = []
                for file_key, file_value in file_dict.iteritems():
                    if ( os.path.isfile( file_value ) ):
                        role_facter_in_time_range.append( { file_key: json.loads( open( file_value ).read() ) } )
                return_dict[ role_path ] = role_facter_in_time_range
        elif dbtype == "template_library":
            tl_list = os.listdir(self.templib_path)
            for file in tl_list :
                result_path = "%s/%s" % (self.templib_path, file)
                return_dict[os.path.splitext(file)[0]] = yaml.load(open( result_path ).read() )
        return return_dict

    # Find the files in the directory based on timestamp
    def _find_file_in_time(self, role_dir_path, timestamp):
        if timestamp == "current":
            return { "current" : os.path.join( role_dir_path, "current" ) }
        elif "starttime" in timestamp and "endtime" in timestamp:
            RANGE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
            FILE_TIME_FORMAT = '%Y%m%dT%H%M%S'
            range_start_time = datetime.strptime( timestamp[ "starttime"], RANGE_TIME_FORMAT )
            range_end_time = datetime.strptime( timestamp[ "endtime"], RANGE_TIME_FORMAT )
            historical_file_paths = [ hist_file for hist_file in listdir( role_dir_path ) ]
            file_dict = {}
            for hist_file in historical_file_paths:
                if not hist_file == "current":
                    m = re.match( r"[^\.]+\.([^\.]+)", hist_file )
                    file_timestamp = m.group( 1 )
                    file_time = datetime.strptime( file_timestamp, FILE_TIME_FORMAT )
                    if ( ( file_time - range_start_time ) > timedelta( seconds = 0 )
                            and ( range_end_time - file_time ) > timedelta( seconds = 0 ) ):
                        file_dict[ file_time.strftime( RANGE_TIME_FORMAT ) ] = os.path.join( role_dir_path, hist_file )
            return file_dict

# This is the interface that you should use in your code
class VigDB(VigDBFS):
    def __init__(self):
        super(VigDB,self).__init__()


if __name__ == "__main__" :
    s= VigDB()
    collector =  s.login()
    # rs = s.find_one(collector, {"fqdn" : "srwd66api001.srwd66.com",})
    # print "Result Set : ", rs
    rs = s.find(collector, {"domain" : "srwd83",} )
    print "Result Set : ", json.dumps( rs)
    rs = s.find(collector, {"domain" : "srwd83", "iso8601" : { "starttime" : "2014-06-17T00:03:01Z", "endtime" : "2014-06-18T18:24:01Z" } } )
    print "Result Set : ", json.dumps( rs)
    templates = s.login("template_library")
    print "Result Set : ", json.dumps( rs)
    rs = s.find(templates, {})
    rs = s.find_one(templates, {"name" : "generic"})
    print "Result Set : ", json.dumps( rs)
    spectpl = s.find_one(templates, {"name" : "special"})
    rs = s._resolve_template(templates,spectpl)
    sys.exit()
    
    
