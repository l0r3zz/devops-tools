#!/usr/local/bin/python2.7
# encoding: utf-8
'''
jcomment -- annotate JIRA tickets from any command line

jcomment is a CLI based tool that allows you to annotate a JIRA issue from any CLI that can access the JIRA server
         All that is required is your JIRA login and the Issue ID. This program uses jiralab.auth so it will cache 
         your password in an encrypted file so that you don't have keep entering it, for subsequent commands. If you
         pipe input into stdin, this input will show up in the comment field of the issue between two {code} tags.


@author:     geowhite
        
@copyright:  2012 StubHub. All rights reserved.
        
@license:    Apache License 2.0

@contact:    geowhite@stubhub.com

'''

import sys
import os
from jira.client import JIRA
import jiralab

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2012-11-04'
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

  Created by user_name on %s.
  Copyright 2012 organization_name. All rights reserved.
  
  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0
  
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-i", "--issue", dest="issueid", default=None,help="JIRA issue ID")
        parser.add_argument("-t", "--text", dest="text", help="text to add to the comment field of the ticket" )
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        
        # Process arguments
        args = parser.parse_args()
        
        # Get login information
        authtoken = jiralab.auth(args)
        issueid = args.issueid.upper()
        jira_options = { 'server': 'https://jira.stubcorp.dev/' }
        jira = JIRA(jira_options,basic_auth= (args.user,args.password))
        if DEBUG: 
            print( "Adding comment to issue: %s" % args.issueid)        
        jira.add_comment(issueid, args.text)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        pass
    if TESTRUN:
        import doctest
        doctest.testmod()

    sys.exit(main())