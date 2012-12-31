#!/usr/bin/python
# encoding: utf-8
'''
jcomment -- annotate JIRA tickets from any command line

jcomment is a CLI based tool that allows you to annotate a JIRA issue from any
         CLI that can access the JIRA server.  All that is required is your
         JIRA login and the Issue ID. This program uses jiralab.auth so it
         will cache your password in an encrypted file so that you don't have
         to keep entering it, for subsequent commands. If you pipe input into
         stdin, this input will show up in the comment field of the issue
         between two {code} tags.

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
from argparse import REMAINDER

__all__ = []
__version__ = 0.7
__date__ = '2012-11-04'
__updated__ = '2012-12-30'


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
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user",
            default=None, help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password",
            default=None, help="password to access JIRA")
        parser.add_argument("-i", "--issue", dest="issueid",
            default=None, help="JIRA issue ID")
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
            nargs=REMAINDER, help="rest of the command is the comment")

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

        if not args.issueid:
            sys.stderr.write(program_name + ": please provide issue id\n")
            parser.print_usage()
            exit(1)

        issueid = args.issueid.upper()

        if DEBUG:
            print("Adding comment to issue: %s" % args.issueid)

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
            comment_text = "*%s*\n %s\n%s" % (args.text, " ".join(args.rem),
                                              body_text)
        else:
            comment_text = "%s\n%s" % (" ".join(args.rem), body_text)

        jira_options = {'server': 'https://jira.stubcorp.dev/'}
        jira = JIRA(jira_options, basic_auth=(auth.user, auth.password))
        jira.add_comment(issueid, comment_text)

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
