#!/usr/bin/python
# encoding: utf-8
'''
dbgen -- Create Delphix based Databases

@author:     geowhite
        
@copyright:  2012 StubHub. All rights reserved.
        
@license:    Apache License 2.0

@contact:    geowhite@stubhub.com
@deffield    updated: Updated
'''

import sys
import os
from jira.client import JIRA
import jiralab
import json



from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2012-11-15'
__updated__ = '2012-11-15'

TESTRUN = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg



def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    DEBUG = 0
    REGSERVER = "srwd00reg010.stubcorp.dev"
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env", help="environment name to provision (example: srwd03" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument("-f", "--frontend", dest="frontdb", help="frontend database (example: srwd00dbs008" )
        parser.add_argument("-b", "--backend", dest="backdb", help="backend database (example: srwd00dbs015" )
        parser.add_argument('-v', '--version', action='version', version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug", action='store_true',help="turn on DEBUG switch")
        
        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)
            
        args = parser.parse_args()
        exit_status =0
        
        if not args.release:
            print("ERROR: No release specified")
            exit_status = 1
        if not args.env:
            print("ERROR: No environment specified")
            exit_status = 1
        if not args.frontdb or not args.backdb:
            print ("ERROR: Please provide correct database locations")
            exit_status =1

        if exit_status:
            print("\n")
            parser.print_help()
            exit(exit_status)

             
        if args.debug:
            DEBUG = True
                   
        authtoken = jiralab.Auth(args)
#        jira_options = { 'server': 'https://jira.stubcorp.dev/' }
#        jira = JIRA(jira_options,basic_auth= (args.user,args.password))

        reg_session = jiralab.CliHelper(REGSERVER)
        reg_session.login(authtoken.user,authtoken.password)
        rval = reg_session.docmd("sudo -i -u relmgt",["$"],consumeprompt=False)
        print ("Rval= %d; before: %s, after: %s" % (rval, reg_session.before, reg_session.after))
        exit()

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2
    

if __name__ == "__main__":

    if TESTRUN:
        import doctest
        doctest.testmod()

    sys.exit(main())