#!/usr/bin/python
# encoding: utf-8
'''
dbgen -- Create Delphix based Databases
@author:     geowhite
@copyright:  2012 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import jiralab

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.5
__date__ = '2012-11-15'
__updated__ = '2012-11-30'

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

    try:
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
        parser.add_argument("-r", "--release", dest="release",
                        help="release ID (example: rb1218")
        parser.add_argument('-v', '--version', action='version',
                        version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
                        action='store_true', help="turn on DEBUG switch")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()
        exit_status = 0

        if not args.release:
            print("ERROR: No release specified")
            exit_status = 1
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
        envnum = envid[-2:]  # just the number

        authtoken = jiralab.Auth(args)

        # Login to the reg server
        print("Logging into %s" % REGSERVER)
        reg_session = jiralab.CliHelper(REGSERVER)
        reg_session.login(authtoken.user, authtoken.password, prompt="\$[ ]")
        if DEBUG:
            print("before: %s\nafter: %s" % (reg_session.before,
                        reg_session.after))

        print ("Becoming relmgt")
        rval = reg_session.docmd("sudo -i -u relmgt", [])
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        #login to the db server
        print("Logging into DB Server : srwd00dbs008")
        rval = reg_session.docmd("ssh srwd00dbs008.stubcorp.dev",
                        ["yes", reg_session.session.PROMPT],
                        consumeprompt=False)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        if rval == 1:  # need to add ssh key
            rval = reg_session.docmd("yes",
                        [reg_session.session.PROMPT], consumeprompt=False)
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            if rval != 1:  # something else printed
                print("Could not log into srwd00dbs008. Exiting")
                exit(2)
        elif rval == 2:  # go right in
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        else:  # BAD
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            print("Something bad happened, exiting")
            exit(2)

        # become the oracle user
        print("Becoming oracle user")
        rval = reg_session.docmd("sudo su - oracle", ["oracle>"],
                        consumeprompt=False)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        # Run the auto provision script
        print("Running the auto-provision script")
        auto_provision_cmd = "/nas/reg/bin/delphix-auto-provision %s %s Ecomm"\
            % (envnum, args.release)
        rval = reg_session.docmd(auto_provision_cmd,
                        ["Tokenized", "Error"], timeout=3600)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        if rval == 1:
            print("%s%s\nSuccess. Exiting.\n" % (reg_session.before,
                        reg_session.after))
            exit(0)
        else:
            print ("Error occurred: %s%s\n" % (reg_session.before,
                        reg_session.after))
            exit(2)

        print("Execution Complete. Exiting.")
        exit(0)
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
