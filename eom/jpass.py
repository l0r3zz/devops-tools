#!/usr/bin/python
# encoding: utf-8
'''
jpass -- setup the password vault for a user


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
__version__ = 0.2
__date__ = '2013-01-02'
__updated__ = '2013-05-01'


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
    program_shortdesc = "jpass -- setup the password vault for a user"

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user",
            default=None, help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password",
            default=None, help="password to access JIRA")
        parser.add_argument('-d', '--delete', dest="delete", action='count', default=0,
            help="remove vault file from current working directory")
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
        # Get username and password from the token file or if one doesn't
        # exist. Create one.
        auth = jiralab.Auth(args)
        if args.delete :
            try:
                os.remove("./" + auth.vault_file)
            except IOError:
                print( "%WARNING: no vault file found in cwd\n")
            if args.delete > 1:
                try:
                    os.remove(("~%s/" % auth.user) + auth.vault_file)
                except IOError:
                    print( '%WARNING: no vault file found in $HOME directory\n')
        
        auth.cred()

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
