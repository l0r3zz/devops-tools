#!/usr/bin/env python
# encoding: utf-8
'''
jclose -- close JIRA tickets from any command line

jclose is a CLI based tool that allows you to close a JIRA issue from any
         CLI that can access the JIRA server.  All that is required is your
         JIRA login and the Issue ID. This program uses jiralab.auth so it
         will cache your password in an encrypted file so that you don't have
         to keep entering it, for subsequent commands. If you pipe input into
         stdin, this input will show up in the comment field of the issue
         between two {code} tags.

@author:     geowhite
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
from jira.exceptions import JIRAError
from jira.client import JIRA
import jiralab

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER

__all__ = []
__version__ = 1.1
__date__ = '2013-04-05'
__updated__ = '2013-06-24'


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
    program_shortdesc ="jclose -- close JIRA tickets from any command line"

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user",
            default=None, help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password",
            default=None, help="password to access JIRA")
        parser.add_argument("-r", "--resolution", dest="resolution",
            default=None, help="resolution (not yet implemented)")
        parser.add_argument("-c", "--rootcause", dest="rootcause",
            default=None, help="Root Cause code(not yet implemented)")
        parser.add_argument("-t", "--text", dest="text",
            help='"text" (in quotes) to add to the comment field IN BOLD')
        parser.add_argument("-f", "--file", dest="ifile",
            nargs="?", const="-", default=None,
            help="input file, if no value, assume stdin")
        parser.add_argument('-v', '--version', action='version',
            version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
            action='store_true', help="turn on DEBUG switch")
        parser.add_argument('rem',
            nargs=REMAINDER, help="list of JIRA issues to close")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()

        if args.debug:
            DEBUG = True
        # Get username and password from the token file or if one doesn't
        # exist. Create one.
        auth = jiralab.Auth(args)
        auth.getcred()

        if not args.rem:
            sys.stderr.write(program_name + ": please provide issue id(s)\n")
            parser.print_usage()
            exit(1)

        issuelist = args.rem

        if DEBUG:
            print("Closing issue: %s" % args.issueid)

        if args.ifile:
            if args.ifile == '-':
                fp = sys.stdin
            else:
                fp = open(args.ifile, 'r')

            piped_text = fp.read()
            # Put the output into the ticket as a "code" block
            body_text = "{code}\n%s\n{code}" % piped_text
        else:
            piped_text = None
            body_text = ""

        if args.text:
            comment_text = "*%s*\n%s" % (args.text, body_text)
        else:
            comment_text = "%s" %  body_text
            if (not args.text) or (not body_text):
                comment_text = "resolved"

        jira_options = {'server': 'https://jira.stubcorp.com/',
                        'verify' : False,
                        }
        jira = JIRA(jira_options, basic_auth=(auth.user, auth.password))

        exitstatus = 0
        for issueid in issuelist:
            try:
                issue = jira.issue(issueid)
                transitions = jira.transitions(issue)
            except JIRAError:
                print( "No ticket found for %s" % issueid)
                continue
                 
            if DEBUG :
                print [(t['id'], t['name']) for t in transitions]

            for t in transitions:
                if 'Close' in t['name']:
                    jira.transition_issue(issue, int( t['id']),
                                        comment=comment_text,
                                        fields={
                                        u'resolution':{u'id':u'10'},
                                        u'customfield_10013':{u'id':u'10621'},
                                        #u'customfield_10761':{u'id':u'10621'},
                                        #u'customfield_10013:1':{u'id':u'-1'},
                                        }
                                    )
                    break
            else:
                print "%s : No Close Method Found" % issue.key
                exitstatus = 1 
        sys.exit(exitstatus)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
#    except Exception, e:
#        if DEBUG :
#            raise(e)
#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + str(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help\n")
#        return 2


if __name__ == "__main__":
    main()
