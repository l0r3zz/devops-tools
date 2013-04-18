#!/nas/reg/local/bin/python
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
import json
import time
from datetime import date
import mylog
import yaml
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter


__all__ = []
__version__ = 0.9979
__date__ = '2012-11-20'
__updated__ = '2013-04-18'

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
        self.program_version_message = '%%(prog)s %s (%s)' % (self.program_version,
                                                        self.program_build_date)
        self.program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
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
        switch_grp.add_argument('--skipreimage', nargs='?',const=True,
                            dest="skip_reimage", default=None, metavar='no',
                            help="assert to skip the re-image operation")
        switch_grp.add_argument('--skipdbgen',  nargs='?',const=True, 
                            dest="skip_dbgen", default=None, metavar='no',
                            help="assert to skip the db creation operation")
        switch_grp.add_argument("--noprepatch", dest="noprepatch",
                            default=None, nargs='?',const=True, metavar='no',
                            help="assert to DISABLE pre deploy patch script")
        switch_grp.add_argument("--nopostpatch", dest="nopostpatch",
                            default=None,  nargs='?',const=True, metavar='no',
                            help="assert to DISABLE scanning patch directory")
        switch_grp.add_argument("--withsiebel", dest="withsiebel",
                             default=None, nargs='?',const=True, metavar='no',
                    help="assert to build a Siebel database along with Delphix")

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
        # Check for various valid options configurations here
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

    def parse_ini_file(self, inifile):
        if os.path.isfile(inifile)and os.access(inifile, os.R_OK):
            with open(inifile) as yi:
                ini_args = yaml.load(yi)
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
                        if self.args.key is None:
                            if (value == "False") or (value =="false"):
                                value = False
                            elif (value =="True") or (value == "true"):
                                value = True
                            setattr(self.args, key, value)
        else:
            print("eom.noini: No .eom_ini found or cannot access %s" % inifile)
        return self.args
