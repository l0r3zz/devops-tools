#!/usr/bin/python
# encoding: utf-8
'''
jcontent - wrapper around REGs content tool
@author:     geowhite
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import re
import jiralab

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER

__all__ = []
__version__ = 0.1
__date__ = '2013-04-20'
__updated__ = '2013-04-20'

def main(argv=None):  # IGNORE:C0111
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
    program_version_message = '%%(prog)s %s (%s)' % (program_version,
                                                     program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]


    # Setup argument parser
    parser = ArgumentParser(description=program_shortdesc,
                    formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-u", "--user", dest="user",
                    default=None, help="user to access JIRA")
    parser.add_argument("-p", "--password",
                    dest="password", default=None,
                    help="password to access JIRA")
    parser.add_argument("-e", "--env", dest="env",
                    help="environment name to provision (example:srwd03")
    parser.add_argument('-v', '--version', action='version',
                    version=program_version_message)
    parser.add_argument('-D', '--debug', dest="debug",
                    action='store_true', help="turn on DEBUG switch")
    parser.add_argument('rem',
        nargs=REMAINDER, help="interactive commands")
    # Process arguments
    if len(sys.argv) == 1:
        parser.print_help()
        exit(1)

    args = parser.parse_args()
    exit_status = 0

    if not args.env:
        print("ERROR: No environment specified")
        exit_status = 1
    if exit_status:
        print("\n")
        parser.print_help()
        exit(exit_status)

    if args.debug:
        DEBUG = True

    envid = args.env.upper()
    envid_lower = args.env.lower()
    envnum = envid[-2:]  # just the number

    auth = jiralab.Auth(args)
    auth.getcred()

    # Login to the reg server
    print("Logging into %s" % REGSERVER)
    reg_session = jiralab.CliHelper(REGSERVER)
    reg_session.login(auth.user, auth.password, prompt="\$[ ]")
    if DEBUG:
        print("before: %s\nafter: %s" % (reg_session.before,
                    reg_session.after))

    print ("Becoming relmgt")
    rval = reg_session.docmd("sudo -i -u relmgt", [reg_session.session.PROMPT])
    if DEBUG:
        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                    reg_session.before, reg_session.after))

    print ("Running content tool...")
    rval = reg_session.docmd("/nas/reg/bin/content -i", ["choice?"])
    if DEBUG:
        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                    reg_session.before, reg_session.after))
    for i in xrange(3):
        rval = reg_session.docmd(args.rem[i], ["choice?"])
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

    # Apply the environment ID        
    rval = reg_session.docmd(envid_lower, ["choice?"])
    if DEBUG:
        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                    reg_session.before, reg_session.after))
        
    # Hit the "go" button
    rval = reg_session.docmd("1", [reg_session.session.PROMPT])
    if DEBUG:
        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                    reg_session.before, reg_session.after))

    print ("%s%s" % (reg_session.before, reg_session.after))
    sys.exit(0)
    
if __name__ == "__main__":

    sys.exit(main())
