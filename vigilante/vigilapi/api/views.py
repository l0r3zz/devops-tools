from django.shortcuts import render
from django.http import HttpResponse
import json
import re
import os.path

# Create your views here.

def version( request, version ):
    response_data = {}
    response_data[ 'version' ] = "v%s" % version
    return HttpResponse( json.dumps( response_data ),
            content_type='application/json' )

def collector_role_current( request, version, host ):
    AUDIT_DATA_PATH = '/nas/reg/log/jiralab/vigilante/auditor'
    m = re.match( r"([^\.]+)\.([^\.]+)\.com", host )
    hostname = m.group( 1 )
    envid = m.group( 2 )
    current_status_path = "%s/%s/%s/srwd83bpm001.20140611T025001.bak" % ( AUDIT_DATA_PATH, envid, hostname )
    # current_status_path = "%s/%s/%s/current" % ( AUDIT_DATA_PATH, envid, hostname )
    if ( os.path.isfile( current_status_path ) ):
        response_data = json.loads( open( current_status_path ).read() )
        return HttpResponse( json.dumps( response_data ),
                content_type='application/json' )

