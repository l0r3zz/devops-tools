#!/nas/reg/local/bin/python
# encoding: utf-8
'''
jenvp -- Print the JIRA status of an Environment
@author:     geowhite

@copyright:  2013 StubHub. All rights reserved.

@license:    Apache License 2.0

@contact:    geowhite@stubhub.com

'''

import sys
import os
from jira.client import JIRA
from jira.exceptions  import JIRAError
import jiralab
import json


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
__all__ = []
__version__ = 0.1
__date__ = '2013-06-11'
__updated__ = '2013-06-11'

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
    program_version_message = '%%(prog)s %s (%s)' % (program_version,
                                                     program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    parser = ArgumentParser(description=program_shortdesc,
        formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-u", "--user", dest="user", default=None,
        help="user to access JIRA")
    parser.add_argument("-p", "--password", dest="password", default=None,
        help="password to access JIRA")
    parser.add_argument("-e", "--env", dest="env",
        help="environment  to query" )
    parser.add_argument('-v', '--version', action='version',
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

    auth = jiralab.Auth(args)
    auth.getcred()
    jira_options = {'server': 'https://jira.stubcorp.com/',
                    'verify' : False,
                    }
    jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
    if DEBUG:
        print( "Looking up:  %s " % args.env)



    project = ('issuetype = "Env Request" AND status = Delivered AND '
               'issuetype != Sub-task AND "Environment Name" = %s '
               'ORDER BY cf[10170] ASC, key DESC') % args.env
    try:
        issues = jira.search_issues(project)
    except :
        print "Invalid"
        sys.exit(2)
    for i in issues:
        print i.fields.status.name
        sys.exit()
    print "Pool"
    sys.exit()

if __name__ == "__main__":
    main()

