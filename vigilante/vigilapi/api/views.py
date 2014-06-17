from django.shortcuts import render
from django.http import HttpResponse
import json
import re
import os.path
from dbapi import VigDB

s = VigDB()
collector = s.login()

# Create your views here.

def version( request, version ):
    response_data = {}
    response_data[ 'version' ] = "v%s" % version
    return HttpResponse( json.dumps( response_data ),
            content_type='application/json' )

def collector_role_current( request, version, hostname ):
    rs = s.find_one(collector, {"fqdn" : hostname,})
    return HttpResponse( json.dumps( rs ), content_type='application/json' )

def collector_env_current( request, version, envid ):
    rs = s.find(collector, {"domain" : envid,})
    return HttpResponse( json.dumps( rs ), content_type='application/json' )
