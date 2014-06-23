#!/usr/bin/env python
# encoding: utf-8
'''
env-audit -- cli tool to perform auditing operations on Dev/QA collection data

@author:     geowhite
@copyright:  2014 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import urllib2


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER

__all__ = []
__version__ = 0.1
__date__ = '2014-06-09'
__updated__ = '2014-06-18'

def http_get( request ):
    return urllib2.urlopen( request ).read()

def api_request( query_type, query_dict ):
    BASE_URL = 'http://srwd00dvo002.stubcorp.dev:7000/vigilante/api/v0.1'
    request_url = ''
    if ( query_type == "collector" ):
        if "fqdn" in query_dict:
            request_url = "collector/role/current/%s" % query_dict[ "fqdn" ]
    elif ( query_type == "query" ):
        if "fqdn" in query_dict and "template" in query_dict:
            request_url = "query/template/%s/collector/role/current/%s" % ( query_dict["template"], query_dict["fqdn"] )
    else:
        pass

    if request_url == '':
        return ''

    return http_get( "%s/%s" % ( BASE_URL, request_url ) )

def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''
    DEBUG = 0
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version,
            program_build_date)
    program_shortdesc ="env-audit - get audit information for Dev/QA environments"

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-e", "--env", dest="envid",
            default=None, help="target environment")
        parser.add_argument("-t", "--template", dest="template",
            default=None, help="template to use for auditing")
        parser.add_argument("-r", "--role", dest="role",
            default=None, help="fqdn of the role  to be used ")
        parser.add_argument('-l', '--list', action='store_true', help="list the template or collection data ",
            dest="list" )
        parser.add_argument('-v', '--version', action='version', help="print the version ",
            version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
            action='store_true', help="turn on DEBUG switch")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()

        if args.debug:
            DEBUG = True
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG :
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2

    if args.list:
        print api_request( "collector", { "fqdn" : args.role } )
    if args.template and args.role:
        print api_request( "query", { "fqdn" : args.role, "template" : args.template } )

if __name__ == "__main__":
    main()
