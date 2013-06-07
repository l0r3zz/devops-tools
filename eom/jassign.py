#!/usr/bin/python
# encoding: utf-8
'''
jassign -- Open and assign a ticket through JIRA
@author:     geowhite
        
@copyright:  2013 StubHub. All rights reserved.
        
@license:    Apache License 2.0

@contact:    geowhite@stubhub.com

'''

import sys
import os
from jira.client import JIRA
import jiralab
import json


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER
__all__ = []
__version__ = 0.4
__date__ = '2013-01-13'
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



def main(argv=None): # IGNORE:C0111
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
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, 
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,
            help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,
            help="password to access JIRA")
        parser.add_argument("-a", "--assignee", dest="assignee",
            help="person to assign the ticket to" )
        parser.add_argument("-w", "--watchers", dest="watchers",
            help="comma separated list of watchers" )
        parser.add_argument("-t", "--text", dest="text",
            help='"text" (in quotes) to add to the title field')
        parser.add_argument('-v', '--version', action='version',
            version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
            action='store_true', help="turn on DEBUG switch")
        parser.add_argument('rem',
            nargs=REMAINDER, help="rest of the command goes to the description field")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)
            
        args = parser.parse_args()
            
             
        if args.debug:
            DEBUG = True
                   
        auth = jiralab.Auth(args)
        auth.getcred()
        jira_options = {'server': 'https://jira.stubcorp.com/',
                        'verify' : False,
                        }
        jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
        if DEBUG: 
            print( "Creating ticket for  %s " % args.text)

        
        # Create the TOOLS ticket
        tools_dict = {
                        'project': {'key':'TOOLS'},
                        'issuetype': {'name':'Task'},
                        'assignee': {'name': args.assignee},
                        'components': [{'name':'decommission'},{'name':'tokenization'}],
                        'summary': args.test,
                        'description': args.rem,
                        }       
        new_tools = jira.create_issue(fields=tools_dict)
        
        sys.exit()
        

        

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    
    except Exception, e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2
    

if __name__ == "__main__":

    main()