#!/usr/bin/env python
# encoding: utf-8
'''
phakgoDB - Run from crontab to collect facts from puppetdb, and store
           the information into mongo db.

@author:     minjzhang
@copyright:  2014 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    minjzhang@ebay.com
'''

import sys
import os
import httplib, urllib
import json
import re
from yaml import load

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER

__all__ = []
__version__ = 0.1
__date__ = '2014-07-23'
__updated__ = '2014-07-23'

PUPPET_DB_HOST = "puppetdb.stubcorp.dev"
PUPPET_DB_PORT = 8080
connection = httplib.HTTPConnection( PUPPET_DB_HOST, PUPPET_DB_PORT )

def get_nodes():
    connection.request( "GET", "/v3/nodes" )
    response = connection.getresponse()
    nodes = json.loads( response.read() )
    filtered_nodes = []
    for node in nodes:
        if ( not re.match( r".*\.stubcorp\..*", node['name'] ) ):
            filtered_nodes.append( node['name'] )

    return filtered_nodes

def generate_fact( hostname, template_facts ):
    connection.request( "GET", "/v3/nodes/%s/facts" % hostname )
    response = connection.getresponse()
    facts = json.loads( response.read() )

    final_facts = {}
    final_facts['meta'] = { 'type' : 'phakgoDB', 'name' : template_facts["meta"]["type"], 'version' : template_facts["meta"]["version"] }
    final_facts['body'] = {}

    for fact in facts:
        if fact['name'] in template_facts["body"]:
            final_facts['body'][ fact['name'] ] = fact['value']

    return final_facts

def get_facts_tempalte( fact_template_file ):
    try:
        q = open( fact_template_file, "r" )
    except IOError:
        print(" %s  : file not found or cannot open" % fact_template_file )
        sys.exit(1)
    template_facts = load( q )

    return template_facts

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
    program_shortdesc = "phakgoDB - crontab to collect facts from puppetdb, and store into mongodb"

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-c", "--config", dest="config_file", default="generic.yaml",
            help="file containing keys to save", metavar="FILE")
        parser.add_argument('-v', '--version', action='version', help="print the version ",
            version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
            action='store_true', help="turn on DEBUG switch")

        args = parser.parse_args()

        if args.debug:
            DEBUG = True
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0

    template_facts = get_facts_tempalte( args.config_file )
    final_facts = {}
    nodes = get_nodes()
    for node in nodes:
        final_facts[ node ] = generate_fact( node, template_facts )

    print final_facts

if __name__ == "__main__":
    main()
