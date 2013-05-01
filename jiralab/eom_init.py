#!/usr/bin/env python
# encoding: utf-8
'''
eom_init - Argument parsing and init file parsing for env-o-matic
@author:     geowhite
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''
import sys
import os
import errno
import yaml
import getpass
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter


__all__ = []
__version__ = 1.05
__date__ = '2012-11-20'
__updated__ = '2013-05-01'

###############################################################################
#    Hardwired Timeout values that can be overridden by options
###############################################################################
REIMAGE_TO = 3600
DBGEN_TO = 3600
VERIFY_TO = 720
CMD_TO = 120
DEPLOY_TO = 4800
CONTENT_TO = 3600
DEPLOY_WAIT = 600
CONTENT_TO = 1200

class eom_startup(object):
    '''
    Process command line arguments, pass them back to the main program
    Search for, open and parse the .eom.ini file
    '''
    def __init__(self,argv):
        '''
        Process command line arguments
        '''

        if argv is None:
            argv = sys.argv
        else:
            sys.argv.extend(argv)

        self.program_name = os.path.basename(sys.argv[0])
        self.program_version = "v%s" % __version__
        self.program_build_date = str(__updated__)
        self.program_version_message = '%%(prog)s %s (%s)' % (
                                                self.program_version,
                                                self.program_build_date)
        self.program_shortdesc = ("eom (env-o-matic)--"
                        "Basic Automation to build out DEV/QA environments")
        self.program_log_id = "%s %s (%s)" % (self.program_name,
                                              self.program_version,
                                              self.program_build_date)
        # Setup argument parser
        parser = ArgumentParser(description=self.program_shortdesc,
                                formatter_class=RawDescriptionHelpFormatter,
                                epilog="Notes:\n"
                                "Most of these options can be placed in "
                                "the YAML .eom.ini file.\nCommand line options "
                                "will always override anything set in the "
                                ".eom.ini.\nFor more information, see the "
                                "env-o-matic man page")
        parser.add_argument("-u", "--user", dest="user",
                            default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password",
                            default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env",
                        help="environment name to provision (example: srwd03" )
        parser.add_argument("-q", "--envreq",
                            dest="envreq", default=None,
                        help="environment request issue ID (example: ENV_707" )
        parser.add_argument("-r", "--release", dest="release",
                            help="release ID (example: rb1218" )
        parser.add_argument("-b", "--build_label", dest="build_label",
                            help="build label to deploy, ex. "
                            "--build_label=rb_ecomm_13_5-186593.209")
        parser.add_argument("-R", "--restart", dest="restart_issue",
                            help="ENV or PROPROJ issue to restart from, ")
        parser.add_argument("-l", "--logfile", dest="logfile",
                            default="/nas/reg/log/jiralab/env-o-matic.log",
                            help="file to log to (if none, log to console)" )
        parser.add_argument("-c", "--config", dest="eom_ini_file",
                            default=None, help="load a specific .eom.ini file")
        parser.add_argument("-P", "--profile", dest="eom_profile",
                            help="specify a label present in the "
                            ".eom.ini file to load options from")
        parser.add_argument("-d", "--deploy", dest="deploy",
                            action='append',
                            help="Deploy full|properties|java|restart|no"
                            "can be used more than once "
                            "ex. -d java -d properties")
        parser.add_argument('--confirm', action='store_true',
                            dest="confirm", default=None,
                            help="print out actions before executing the job ")
        parser.add_argument('--ignoreini', action='store_true',
                            dest="ignore_ini", default=None,
                            help="ignore any .eom.ini file present")
        parser.add_argument('--ignorewarnings', action='store_true',
                            dest="ignorewarnings", default=None,
                            help="continue with deploy, even with env-validate"
                            " warnings. note: sudo/ssh warnings will not"
                            " be ignored")
        switch_grp = parser.add_argument_group('Switches',
                            "Example: --skipreimage=no will TURN ON re-imaging "
                            "if skipreimage was set to true in the eom.ini file"
                            )
        switch_grp.add_argument('--content_refresh', nargs='?',const=True,
                            dest="content_refresh", default=None, metavar='no',
                            help="assert to run content refresh during "
                            "deploy")
        switch_grp.add_argument('--content_tool', nargs='?', const=True,
                            dest="content_tool", default=None, metavar='no',
                            help="assert to run the portable content tool "
                            "after deploy")
        switch_grp.add_argument('--validate_bigip', nargs='?', const=True,
                            dest="validate_bigip", default=None, metavar='no',
                            help="assert to validate BigIP after deploy")
        switch_grp.add_argument('--close_tickets', nargs='?',const=True,
                            dest="close_tickets", default=None, metavar='no',
                            help="assert to close DB & PROPROJ tickets")
        switch_grp.add_argument('--skipreimage', nargs='?',const=True,
                            dest="skipreimage", default=None, metavar='no',
                            help="assert to skip the re-image operation")
        switch_grp.add_argument('--skipdbgen',  nargs='?',const=True, 
                            dest="skipdbgen", default=None, metavar='no',
                            help="assert to skip the db creation operation")
        switch_grp.add_argument("--noprepatch", dest="noprepatch",
                            default=None, nargs='?',const=True, metavar='no',
                            help="assert to DISABLE pre deploy patch script")
        switch_grp.add_argument("--nopostpatch", dest="nopostpatch",
                            default=None,  nargs='?',const=True, metavar='no',
                            help="assert to DISABLE  DB creation patching")
        switch_grp.add_argument("--withsiebel", dest="withsiebel",
                             default=None, nargs='?',const=True, metavar='no',
                    help="assert to build a Siebel database along with Delphix")

        to_grp = parser.add_argument_group("Time out adjustments")
        to_grp.add_argument("--deploy_to", dest="DEPLOY_TO",
                            default=DEPLOY_TO, type=int,
                            help="set the timeout for deploy step in sec.")
        to_grp.add_argument("--reimage_to", dest="REIMAGE_TO", 
                            default=REIMAGE_TO, type=int,
                            help="set the timeout for reimage operation in sec.")
        to_grp.add_argument("--content_to", dest="CONTENT_TO", 
                            default=CONTENT_TO, type=int,
                            help="set the timeout for content refresh in sec.")
        to_grp.add_argument("--dbggen_to", dest="DBGEN_TO", 
                            default=DBGEN_TO, type=int,
                            help="set the timeout for database creation in sec.")
        to_grp.add_argument("--verify_to", dest="VERIFY_TO", 
                            default=VERIFY_TO, type=int,
                            help="set the timeout for verification ops in sec.")
        
        p_info_grp = parser.add_argument_group('Informational')
        p_info_grp.add_argument('-D', '--debug', dest="debug", action='count',
                                default=0,
                        help="turn on DEBUG additional Ds increase verbosity")
        p_info_grp.add_argument('-v', '--version', action='version',
                            version=self.program_version_message)
        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)
        self.args = parser.parse_args()

        #######################################################################
        # Check for various valid options configurations here
        #######################################################################
        # Scan to see if the .eom directory is present, if not create it.

        # Search path for the .eom_ini file, first look in cwd, if not found
        # there look in the home directory of the user specified in the --user
        # option, if the user option is not specified, try the home directory 
        # of the user running the program.
        eom_dir_path = [
                        "./.eom",
                        "~%s/.eom" % ( self.args.user 
                                      if self.args.user else getpass.getuser()),
                        "~%s/.eom" % getpass.getuser(),
                        ]

        for eomp in eom_dir_path:
            try:
                eom_path = os.path.expanduser(eomp)
                os.makedirs(eom_path)
            except OSError as exc: # Python >2.5
                if (exc.errno == errno.EEXIST) and os.path.isdir(eom_path):
                    break
                else:
                    continue
            break   # We were successful creating a directory so break from the 
                    # for loop and don't execute the else attached
        else:
            print("eom.noinidir: Can't find or open an"
                  " .eom directory writing to /dev/null")
            eom_path = "/dev/null"

        # Check for the presence of the .eom.ini
        if not self.args.ignore_ini:
            if self.args.eom_ini_file:
                pass
            else:
                if eom_path == "/dev/null":
                    eom_ini_file = None
                else:
                    eom_ini_file = eom_path + "/.eom_ini"
            self._parse_ini_file(eom_ini_file)

        exit_status = 0
        if not self.args.release:
            print("ERROR: No release specified")
            exit_status = 1
        if not self.args.env:
            print("ERROR: No environment specified")
            exit_status = 1
        if not self.args.deploy:
            self.args.deploy = ["full-deploy"]  # default to full-deploy
        if not (self.args.deploy[0] == 'no') and (not self.args.build_label):
            print("ERROR: Deploy specified without build label")
            exit_status = 1

        if exit_status:
            print("\n")
            parser.print_usage()
            exit(exit_status)

    def _parse_ini_file(self, inifile):
        if os.path.isfile(inifile)and os.access(inifile, os.R_OK):
            with open(inifile) as yi:
                try:
                    ini_args = yaml.load(yi)
                except yaml.YAMLError, exc:
                    if hasattr(exc, 'problem_mark'):
                        mark = exc.problem_mark
                        print( "Error in .eom_ini file:"
                               " %s, Error position: (%s:%s)" 
                               % (exc, mark.line+1, mark.column+1))
                if self.args.eom_profile:
                    profile = self.args.eom_profile
                else:
                    profile = "default"
                if not (profile in ini_args):
                    print(
                     'eom.noiniprofile: No profile named'
                     ' "%s" found in .eom_ini, ignoring...' % profile)
                else:
                    for key, value  in ini_args[profile].iteritems():
                        if getattr(self.args, key) is None:
                            if (value == "False") or (value =="false"):
                                value = False
                            elif (value =="True") or (value == "true"):
                                value = True
                            setattr(self.args, key, value)
                        elif getattr(self.args, key) == "no":
                            setattr(self.args, key, False)
        else:
            print("eom.noini: No .eom_ini found or cannot access %s" % inifile)
        return 
