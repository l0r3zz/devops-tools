#!/usr/bin/env python
# encoding: utf-8
'''
proproj -- Create Provisioning and DB tickets in JIRA

@author:     geowhite

@copyright:  2013 StubHub. All rights reserved.

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
__version__ = 0.78
__date__ = '2012-10-28'
__updated__ = '2013-06-07'

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


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
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc ="proproj -- Create Provisioning and DB tickets in JIRA"

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env", help="environment name to provision (example: srwd03" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument('-v', '--version', action='version', version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug", action='store_true',help="turn on DEBUG switch")
        parser.add_argument('-S', '--smoke', dest="smoke", action='store_true',
                            help="create a smoke test ticket (not implemented)")
        parser.add_argument("--withsiebel", dest="withsiebel", action='store_true',
                            default=False, help="set to build a Siebel database along with Delphix")        
        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()

        if not args.release:
            print("No release specified\n")
            parser.print_help()
            exit(1)

        try:
            jreg = jiralab.Reg(args.release)
            jira_release = jreg.jira_release
        except jiralab.JIRALAB_CLI_ValueError :
            print( "eom.relerr: No release named %s" % args.release)
            exit(2)

        if args.debug:
            DEBUG = True

        auth = jiralab.Auth(args)
        auth.getcred()
        jira_options = {'server': 'https://jira.stubcorp.com/',
                        'verify' : False,
                        }
        jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
        if DEBUG: 
            print( "Creating ticket for Environment: %s with release %s " %\
               (args.env,jira_release))
        envid = args.env.upper()
        envnum = envid[-2:] #just the number
        pp_summary = "%s: Configure readiness for code deploy" % envid
        use_siebel = ("/Siebel" if args.withsiebel else "")
        db_summary = "%s: Create Delphix%s Database for %s environment" % (envid,use_siebel,jira_release)

        # Create the PROPROJ ticket
        proproj_dict = {
                        'project': {'key':'PROPROJ'},
                        'issuetype': {'name':'Task'},
                        'assignee': {'name': auth.user},
                        'customfield_10170': {'value':envid},
                        'components': [{'name':'decommission'},{'name':'tokenization'}],
                        'summary': pp_summary,
                        'description': pp_summary,
                        'customfield_10130': {'value': jira_release},
                        }
        if DEBUG :
            print( json.dumps(proproj_dict))

        new_proproj = jira.create_issue(fields=proproj_dict)

        #Create the DB ticket
        db_dict = {
                        'project': {'key':'DB'},
                        'issuetype': {'name':'Task'},
                        'assignee': {'name': auth.user},
                        'customfield_10170': {'value':envid},
                        'customfield_10100': {'value':'unspecified'},
                        'components': [{'name':'General'}],
                        'summary': db_summary,
                        'description': db_summary,
                        'customfield_10130': {'value': jira_release},
                        }


        new_db = jira.create_issue(fields=db_dict)

        # Now block the PROPROJ ticket with the DB ticket.
        link = jira.create_issue_link(type="Dependency",inwardIssue=new_proproj.key, outwardIssue=new_db.key)

        # output a JSON dict so we can use it as piped input into a latter stage.
        result_dict = { "envid": envid, 
                       "proproj": new_proproj.key, 
                       "dbtask": new_db.key,
                       "envreq" : "unknown", }
        print( json.dumps(result_dict,sort_keys=True))
        sys.exit(0)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0

#   except Exception, e:

#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + str(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help\n")
#        return 2


if __name__ == "__main__":
    main()