#!/usr/local/bin/python2.7
# encoding: utf-8
'''
proproj -- Create a Provisioning project in JIRA and kick off provisioning processes

proproj is a standalone cli program 

It defines classes_and_methods

@author:     geowhite
        
@copyright:  2012 StubHub. All rights reserved.
        
@license:    license

@contact:    geowhite@stubhub.com
@deffield    updated: Updated
'''

import sys
import os
from jira.client import JIRA
import getpass


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.2
__date__ = '2012-10-28'
__updated__ = '2012-11-04'

DEBUG = 0
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

class JIRAauth():
    def __init__(self,args):
        if (not args.user):
            user = raw_input("Username [%s]: " % getpass.getuser())
            if not user:
                args.user = getpass.getuser()
            args.user = user
        if (not args.password):
            args.password = getpass.getpass()

        self.user = args.user
        self.password = args.password

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by geowhite on %s.
  Copyright 2012 StubHub. All rights reserved.
  
  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0
  
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-y", "--yestoall", dest="yestoall", action="store_true",default=False, help="answer 'yes' to all [y/n] questions")
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env", help="environment name to provision (example: srwd03" )
        parser.add_argument("-d", "--dbfront", dest="dbfront", help="DB frontend (example: srwd00dbs008.stubcorp.dev)" )
        parser.add_argument("-b", "--dbback", dest="dbback", help="backend db server (example: srwd00dbs015.stubcorp.dev" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        
        # Process arguments
        args = parser.parse_args()
        
        authtoken = JIRAauth(args)
        jira_options = { 'server': 'https://jira.stubcorp.dev/' }
        jira = JIRA(jira_options,basic_auth= (args.user,args.password))
        print( "Creating ticket for Environment: %s with release %s using host %s as the DB front end and %s as the DB backend" %\
               (args.env,args.release,args.dbfront,args.dbback))
        envid = args.env.upper()
        envnum = envid[-2:] #just the number
        pp_summary = "%s: TEST Configure readiness for code deploy" % envid
        db_summary = "%s: TEST Create Delphix Database for %s environment" % (envid,args.release)
        
        # Create the PROPROJ ticket
        proproj_dict = {
                        'project': {'key':'PROPROJ'},
                        'issuetype': {'name':'Task'},
                        'assignee': {'name': authtoken.user},
                        'customfield_10170': {'value':envid},
                        'summary': pp_summary,
                        'description': pp_summary,
                        'customfield_10130': {'value': args.release},
                        }       
        new_proproj = jira.create_issue(fields=proproj_dict)
        
        #Create the DB ticket
        db_dict = {
                        'project': {'key':'DB'},
                        'issuetype': {'name':'Task'},
                        'assignee': {'name': authtoken.user},
                        'customfield_10170': {'value':envid},
                        'customfield_10100': {'value':'unspecified'},
                        'components': [{'name':'General'}],
                        'summary': db_summary,
                        'description': db_summary,
                        'customfield_10130': {'value': args.release},
                        }
        new_db = jira.create_issue(fields=db_dict)
        
        # Now block the PROPROJ ticket with the DB ticket.
        link = jira.create_issue_link(type="Blocks",inwardIssue=new_db.key, outwardIssue=new_proproj.key)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
#    except Exception, e:
#        if DEBUG or TESTRUN:
#            raise(e)
#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + repr(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help")
#        return 2
    

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-h")
        sys.argv.append("-V")
    if TESTRUN:
        import doctest
        doctest.testmod()

    sys.exit(main())