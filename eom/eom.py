#!/usr/bin/env python
# encoding: utf-8
'''
eom (env-o-matic) - Basic automation to build-out a virtual environment

@author:     Geoff White
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import errno
import re
from jira.client import JIRA
import jiralab
import json
import time
from datetime import date
import mylog
import logging
import yaml
import Queue
import getpass
import inspect
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER
from argparse import SUPPRESS
__all__ = []
__version__ = 1.097
__date__ = '2012-11-20'
__updated__ = '2013-05-30'

REGSERVER = "srwd00reg010.stubcorp.dev" # Use this server to run commands
DEFAULT_LOG_PATH = "/nas/reg/log/jiralab/env-o-matic.log"
DEBUG = 0
PEXTO = 0      # Pexpect command timed-out
PEXOK = 1      # Pexpect command returned OK

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
CTOOL_TO = 900
TJOIN_TO = 60.0
PREPOST_TO = 240
SIEBEL_TO = 1800

###############################################################################
#    Workhorse functions
###############################################################################

def assignSequence(seq):
    '''
    Decorator to assign a ranking to methods defined in the Eom class so that
    we can schedule the execution of the various stages.  If you don't use this
    decorator the method will not be scheduled. Not e there is no need to
    schedule __init__, it is the Eom constructor and will be the first routine
    to be executed on start-up.   Also any "private" methods should not be 
    sddigned a sequence number
    '''
    def do_assignment(to_func):
        to_func.seq = seq
        return to_func
    return do_assignment

def stage_entry(log):
    log.info("eom.stgentry: stage %s ENTRY" % inspect.stack()[1][3])

def stage_exit(log):
    log.info("eom.stgexit: stage %s EXIT" % inspect.stack()[1][3])

def execute(s, cmd, debug, log, to=CMD_TO, result_set=None, dbstring=None):
    """
    Execute a remote command and look at the output with pexpect
    """
    if result_set:
        rval = s.docmd(cmd, result_set, timeout=to)
    else:
        rval = s.docmd(cmd,[s.session.PROMPT],timeout=to)
    if debug:
        if dbstring:
            log.debug(dbstring % rval)
        else:
            log.debug ("eom.deb: Rval= %d; \nbefore: %s\nafter: %s"
                        % (rval, s.before, s.after))
    if rval == PEXTO:
        log.warn("eom.to: cmd: (%s) timed out after %d sec." % ( cmd, to))
    return rval


def main():
    '''
    This is the main routine.
    Note that the methods in the Eom class that are decorated with 
    @assignSequence are methods that will be called and executed, in sequence,
    based on the sequence number that is assigned to them. The methods are 
    gathered via the dir() and then only the methods that have the "seq" 
    attribute are sorted and executed in sequence
    '''
    try:  # Catch keyboard interrupts (^C)
        eom = Eom()
        functions = sorted(
                     #get a list of fields that have the sequence
                     [getattr(eom, field) for field in dir(eom)
                      if hasattr(getattr(eom, field), "seq")
                     ],
                     #sort them by their sequence
                     key = (lambda field: field.seq)
                    )
        for func in functions:
            func()
    
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        sys.exit(0)
###############################################################################
#    These classes implement threads that can be started in parallel
###############################################################################
class EOMreimage(jiralab.Job):
    '''
    This class is a container for the re-imaging task, it inherits from 
    jiralab.Job so it can be scheduled as a thread, the overlayed run() 
    method does the actual work as the super class has created a ssh session
    on a reg server to be used
    '''
    def run(self):
        try:
            q = self.stage_q
            ses = self.ses
            args = self.args
            user = self.auth.user
            log = self.log
            ppj = self.pprd["proproj"]
            name = self.name
            debug = self.debug
            if q :
                q.get()
    
            envid = self.args.env.upper()   # insure UPPERCASE env name
            envid_l = self.args.env.lower() # insure lowercase env name
            # Start re-imaging
            log.info("eom.reimg.start:(%s) Reimaging %s start @ %s UTC" %
                     (name, envid, time.asctime(time.gmtime(time.time()))))
            reimage_cmd = (('time provision -e %s reimage -v 2>&1'
            '|jcmnt -f -u %s -i %s -t "Re-Imaging Environment for code deploy"')
                % ( envid_l, user, ppj))
            rval = execute(ses, reimage_cmd, debug, log, to=args.REIMAGE_TO)
            if rval == PEXTO:
                log.warn("eom.rimgto: Re-image operation timed out")
                execute(ses,"jcmnt -u %s -i %s re-image operation time-out"
                        % (user,ppj), debug, log)
                return
    
            log.info("eom.sleep:(%s) Re-image complete, sleeping 5 minutes"
                          % name)
            time.sleep(300)
    
            log.info("eom.rimgval: Verifying re-imaging of roles in %s" % envid)
    
            reimage_validate_string = ('verify-reimage %s '
            '|jcmnt -f -u %s -i %s -t'
            ' "check this list for re-imaging status"'% (envid_l, user, ppj))
            rval = execute(ses, 
                           reimage_validate_string, debug, log, 
                           to=args.VERIFY_TO)
    
            log.info("eom.reimg.done:(%s) Reimaging done @ %s UTC" %
                          (name, time.asctime(time.gmtime(time.time()))))

        except:
            log.error(
                "eom.threadexcpt: exception occurred in thread %s" % name)
        finally:
            if q:
                q.task_done()
        return

                    
class EOMdbgen(jiralab.Job):
    '''
    This class is a container for the database generation task, it inherits from 
    jiralab.Job so it can be scheduled as a thread, the overlayed run() 
    method does the actual work as the super class has created a ssh session
    on a reg server to be used
    '''
    def run(self):
        try:
            q = self.stage_q
            ses = self.ses
            args = self.args
            user = self.auth.user
            log = self.log
            dbt = self.pprd["dbtask"]
            name = self.name
            debug = self.debug

            if q :
                q.get()
            envid = self.args.env.upper()       # insure UPPERCASE env name
    
            log.info(
                    "eom.dbcreate.start:(%s) Building Database start @ %s UTC,"
                    % (name, time.asctime(time.gmtime(time.time()))))
    
            if args.debug > 1:
                dbgendb = "-D"
            else:
                dbgendb = ""
    
    
            pp_path = ("" if args.nopostpatch else\
               '--postpatch="/nas/reg/bin/env_setup_patch/scripts/dbgenpatch"')
            dbgen_to = args.DBGEN_TO - 10
            dbgen_build_cmd = (
                'time dbgen -u %s -e %s -r %s %s %s --timeout=%d %s'
                ' |tee /dev/tty'
                ' |jcmnt -f -u %s -i %s -t "Automatic DB Generation"' %
                (user, envid, args.release, 
                 pp_path, self.use_siebel, dbgen_to, dbgendb,
                 user, dbt))
    
            rval = execute(ses, dbgen_build_cmd, debug, log, to=args.DBGEN_TO)
            if rval == PEXTO:
                log.warn(
                    "eom.dbcreate.to:(%s) dbgen did not complete within %d sec"
                    % (name, args.DBGEN_TO))
            # Look for errors in the delphix-auto-provision output
            if 'Error' in ses.session.before:
                log.warn("eom.dbcreate.err:(%s) dbgen encountered an error" % name)

            log.info("eom.dbcreate.done:(%s) Database DONE @ %s UTC," %
                     (name, time.asctime(time.gmtime(time.time()))))

        except:
            log.error(
                "eom.threadexcpt: exception occurred in thread %s" % self.name)
        finally:
            if q:
                q.task_done()

                            
class eom_startup(object):
    '''
    This class handles all of the argument parsing and eom_init config file
    parsing, it returns an argparse Namespace object that can be passed around
    Process command line arguments, pass them back to the main program
    Search for, open and parse the .eom.ini file
    '''
    def __init__(self):
        '''
        Process command line arguments
        '''

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
                            default=DEFAULT_LOG_PATH,
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
        to_grp.add_argument("--dbgen_to", dest="DBGEN_TO", 
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
        parser.add_argument('rem',
            nargs=REMAINDER, help=SUPPRESS)
        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)
        self.args = parser.parse_args()
        if self.args.rem:
            parser.print_help()
            exit()

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


###############################################################################
#                        Class Eom
###############################################################################
class Eom(object):
    def __init__(self,argv=None):
        #######################################################################
        # Get cmd line options, start logging, read ini file, validate options
        #######################################################################
        # This let's you provide arguments as callable parameters, if your not
        # running the program from __main__
        if argv:
            sys.argv.extend(argv)
            
        start_ctx = eom_startup()
        args = self.args = start_ctx.args
        
        # Authenticate user name and password
        self.auth = auth = jiralab.Auth(args)
        auth.getcred()
    
        self.envid = envid = args.env.upper()
        self.envid_l = envid_l = args.env.lower()
        self.envnum = envid[-2:]            #just the number
        self.stage_q = Queue.Queue()        # use this queue for thread seq
        
        #######################################################################
        #                  Set up and start Logging
        #######################################################################    
        try:
            if args.logfile:
                self.log = log = mylog.logg('env-o-matic', llevel='INFO', 
                        gmt=True, lfile=args.logfile, cnsl=True)
            else:
                self.log = log = mylog.logg('env-o-matic', llevel='INFO',
                        gmt=True, cnsl=True, sh=sys.stdout)
        except UnboundLocalError:
            print("Can't open Log file, check path\n")
            sys.exit(1)
    
        #set the formatter so that it adds the envid
        lfstr = ('%(asctime)s %(levelname)s: %(name)s:'
                 '[%(process)d] {0}:: %(message)s'.format(envid_l))
        formatter = logging.Formatter(lfstr,
            datefmt='%Y-%m-%d %H:%M:%S +0000')
        for h in log.handlers:
            h.setFormatter(formatter)
    
        if args.debug:
            DEBUG = True
            log.setLevel("DEBUG")
        else:
            DEBUG = False
    
    
        #######################################################################
        #                   Hello World!
        #######################################################################    
        log.info('eom.start: %s :: %s' % (start_ctx.program_log_id, args))    
        # Get the login credentials from the user or from the vault
    
    @assignSequence(100)
    def login_stage(self):
        # Login to the reg server
        # We do all orchestration from a single reg erver
        log = self.log
        auth = self.auth
        args = self.args
        stage_entry(log)

        log.info ("eom.login: Logging into %s  @ %s UTC" %\
                (REGSERVER, time.asctime(time.gmtime(time.time()))))
        self.ses = ses = jiralab.CliHelper(REGSERVER,log)
        # Die if the login failed.
        if not ses.login(auth.user,auth.password,prompt="\$[ ]"):
            log.error("eom.badexit: Exiting with error")
            sys.exit(2)

        if DEBUG:
            log.debug ("eom.deb: before: %s\nafter: %s" % (ses.before,
                                                           ses.after))
        # Become the relmgt user, all tools are run as this user
        log.info ("eom.relmgt: Becoming relmgt @ %s UTC" %\
                  time.asctime(time.gmtime(time.time())))
    
        rval = execute(ses,"sudo -i -u relmgt",DEBUG,log)
    
        try:
            jreg = jiralab.Reg(args.release) # get reg build mapping for JIRA
            self.jira_release = jreg.jira_release
        except jiralab.JIRALAB_CLI_ValueError :
            print( "eom.relerr: No release named %s" % args.release)
            exit(2)
        stage_exit(log)
        return rval

    @assignSequence(200)
    def create_issue_stage(self):
    #######################################################################
    #                   restart option
    #######################################################################
        args = self.args
        auth = self.auth
        envid = self.envid
        envid_l = self.envid_l
        log = self.log
        jira_release = self.jira_release
        ses = self.ses
        stage_entry(log)
        
        if  args.restart_issue:
            restart_issue = args.restart_issue
            # FIXME: we need code here to find the linked issue keys to fill
            # in the correct dbtask and potentially the correct proproj
            if 'PROPROJ' in restart_issue:
                proproj_result_dict = {
                        "dbtask" : "unknown",
                        "envid" : envid_l,
                        "proproj" : restart_issue,
                        "envreq"  : "unknown"
                        }
            else:
                proproj_result_dict = {
                        "dbtask" : "unknown",
                        "envid" : envid_l,
                        "proproj" : "unknown",
                        "envreq"  : restart_issue,
                        }
                
            if args.envreq:
                proproj_result_dict["envreq"] = args.envreq
                self.pprj = pprj = proproj_result_dict["envreq"]
            else:    
                self.pprj = pprj = proproj_result_dict["proproj"]
    
            if pprj == "unknown":
                log.error(
                        "eom.noticket: Invalid or no ticket specified for restart")
                sys.exit(2)
            self.proproj_result_dict = proproj_result_dict # fix crash after restart
            log.info("eom.rststruct: Restarting with structure: %s" %
                     json.dumps(proproj_result_dict))

        #######################################################################
        #                   First time ticket creation here
        #######################################################################
        else:
            # Create a PROPROJ and DB ticket for the ENV
            log.info ("eom.cjira: Creating JIRA issues")
            self. use_siebel = ("--withsiebel" if args.withsiebel else "")
            proproj_cmd =  "proproj -u %s -e %s -r %s %s " % (auth.user, 
                                            args.env, jira_release, 
                                            self.use_siebel)
    
            rval = execute(ses,proproj_cmd, DEBUG, log, result_set=["\{*\}",
                                                  ses.session.PROMPT])
            if rval == PEXOK :
                PPRESULT = 1
                proproj_result_string = (
                            ses.before + ses.after).split("\n")
                proproj_result_dict = json.loads(
                                                proproj_result_string[PPRESULT])
                self.proproj_result_dict = proproj_result_dict
                log.info("eom.tcreat: Ticket Creation Structure:: %s" %\
                         proproj_result_string[PPRESULT])
                self.pprj =  pprj = proproj_result_dict["proproj"]
            else:
                log.error(
                    "eom.tcreat.err: Error in ticket "
                    "creation: %s%s \nExiting.\n" %
                    (ses.before, ses.after))
                exit(2)
    
        # Login to JIRA so we can manipulate tickets...
        self.jira_options = jira_options = {'server': 'https://jira.stubcorp.dev/',
                    'verify' : False,
                    }
        jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
        
        # If there is an ENV ticket, and this is not a restart,
        # link the proproj to it. And set the ENVREQ Status to Provisioning
        if args.envreq and not args.restart_issue:
            log.info("eom.tlink: Linking propoj:%s to ENV request:%s" %\
                     (pprj, args.envreq))
    
            jira.create_issue_link(type="Dependency",
                                    inwardIssue=args.envreq,
                                    outwardIssue=pprj)
            env_issue = jira.issue(args.envreq)
            env_transitions = jira.transitions(env_issue)
            for t in env_transitions:
                if 'Provisioning' in t['name']:
                    jira.transition_issue(env_issue, int( t['id']), fields={})
                    env_issue.update(customfield_10761=(
                                                    date.today().isoformat()))
                    env_issue.update(fields={'customfield_10170': {'value' : envid}}) 
                    log.info(
                        "eom.prvsts: ENVREQ:%s set to Provisioning state" %
                        args.envreq)
                    break;
            else:
                log.warn(
                    "eom.notpro: ENV REQ:%s cannot be set to provision state" %
                     args.envreq)
      
        rval=1
        stage_exit(log)
        return rval

    @assignSequence(300)
    def prevalidate_stage(self):
        return None

    @assignSequence(400)
    def reimaging_stage(self):
        #######################################################################
        #                   Handle re-image here
        #######################################################################
        args = self.args
        auth = self.auth
        envid = self.envid
        log = self.log
        pprj = self.pprj
        stage_entry(log)

        
        if args.skipreimage:
            log.info("eom.noreimg: Skipping the re-image of %s" % envid)
            stage_exit(log)
            return None
        elif 'unknown' in pprj:
            log.info("eom.reimgenv: Reimaging with an ENV issue"
                     " not yet supported. Skipping...")
            args.skipreimage = True
            stage_exit(log) 
            return None
        else:
            # Start re-imaging in a thread
            reimage_task = EOMreimage(args, auth, log,
                            name="re-image-thread",
                            proproj_result_dict=self.proproj_result_dict,
                            queue = self.stage_q,
                            )
            self.stage_q.put(reimage_task)
            reimage_task.daemon = True
            reimage_task.start()
            self.reimage_task = reimage_task # FIXME need to refactor this for threads
            rval = 1
            stage_exit(log)
            return rval

    @assignSequence(410)
    def dbgen_stage(self):
        args = self.args
        auth = self.auth
        envid = self.envid
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)
        #######################################################################
        #                   Handle database creation here
        #######################################################################
        if args.skipdbgen:
            log.info("eom.nodbgen: Skipping the db creation of %s" % envid)
            stage_exit(log)
            return None
        elif 'unknown' in pprj:
            log.warn("eom.nodbgenrst: dbgen restart not yet supported")
            args.skipdbgen = True
            stage_exit(log)
            return None
        else:
            dbgen_task = EOMdbgen(args, auth, log,
                            name="dbgen-thread",
                            proproj_result_dict=self.proproj_result_dict,
#                            session=ses,
                            use_siebel=self.use_siebel,
                            queue=self.stage_q
                            )
            self.stage_q.put(dbgen_task)
            dbgen_task.daemon = True
            dbgen_task.start()
            self.dbgen_task = dbgen_task   
            rval = 1
            stage_exit(log)
            return rval

    @assignSequence(500)
    def validate_stage(self):
        args = self.args
        auth = self.auth
        envid_l = self.envid_l
        envnum = self.envnum
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)

        #######################################################################
        #   Wait for all the threads to complete
        #######################################################################

        if not args.skipdbgen or not args.skipreimage:
            time.sleep(10)
            log.info("eom.jobwait: waiting for parallel jobs from previous"
                     " stage to complete")
            self.stage_q.join()
            log.info("eom.jobdone: jobs are done, merging execution")
    
        #######################################################################
        # We should be done with Provisioning, run the env-validate suit
        #######################################################################
        log.info("eom.envval: Performing Automatic Validation of %s" %\
                 envid_l)
        args.enval_success = False
        # Set up the env_validate commands so that they write to the
        # tty as well as pipe to the jcomment utility.  We'll use the tty
        # output to determine whether to continue with app deploy.
        if 'srwe' in envid_l :
            env_validate_string = ('env-validate -d srwe -e %s 2>&1'
            '| tee /dev/tty'
            ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
            (envnum, auth.user, pprj)
        elif 'srwq' in envid_l :
            env_validate_string = ('env-validate -d srwq -e %s 2>&1'
            '| tee /dev/tty'
            ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
            (envnum, auth.user, pprj)
        else :
            env_validate_string = ('env-validate -e %s 2>&1 '
            '| tee /dev/tty'
            ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
            (envnum, auth.user, pprj)
    
        rval = execute(ses, env_validate_string, DEBUG, log, to=args.VERIFY_TO)
    
        #######################################################################
        # Check the results of env-validate to see if we can proceed
        #######################################################################
        if rval == PEXTO:   
        # env-validate timed out, write failure to log and ticket
            log.error("eom.envalto: env-validation"
                      " timed out after %d seconds, exiting." % args.VERIFY_TO)
            env_valfail_string = ('jcmnt -f -u %s -i %s'
                            ' -t "env-validate timed out after %d seconds."' % 
                            (auth.user, pprj, args.VERIFY_TO))
            rval = execute(ses, env_valfail_string, DEBUG, log)
            sys.exit(1)
        # regex's to look for PASS or if not PASS make sure that the failures
        # are not because of ssh or sudo failures
        rgx_envPASS = "env-validate\[[0-9]*\] results: PASS"
        rgx_envsudoFAIL = "env-validate\[[0-9]*\] PRIORITY=WARNING .+sudo test"
        rgx_envsshFAIL = "env-validate\[[0-9]*\] PRIORITY=WARNING .+ssh test"
        rgx_envdbFAIL = ("env-validate\[[0-9]*\] "
                        "PRIORITY=WARNING .+D(08|19|16)DE[0-9]{2}.+Failed")
        if not re.search(rgx_envPASS,ses.before):
            # validation didn't pass, see if we want to ignore it
            if args.ignorewarnings and (
                not re.search(rgx_envsudoFAIL, ses.before) and 
                not re.search(rgx_envsshFAIL, ses.before)  and
                not re.search(rgx_envdbFAIL, ses.before)

                ):
                log.warn("eom.prvwarn: Warnings present, proceeding anyway")
            else:
                log.info("eom.prvext Provision step had unrecoverable warnings"
                         " @ %s UTC. Exiting.\n" %\
                         time.asctime(time.gmtime(time.time())))
                sys.exit(1)
        else:
            log.info("eom.valpass: env-validation PASS for %s" % envid_l)
            args.enval_success = True
        stage_exit(log)
        return rval

    @assignSequence(600)
    def pre_deploy_stage(self):
        args = self.args
        auth = self.auth
        envid_l = self.envid_l
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)
        #######################################################################
        # Run the pre deploy script
        #######################################################################
        if not args.noprepatch and args.deploy[0] != 'no':
            envpatch_cmd = ("/nas/reg/bin/env_setup_patch/scripts/envpatch %s"
                    '| jcmnt -f -u %s -i %s -t "Automatic predeploy script"') %\
                (envid_l, auth.user, pprj)
            log.info ("eom.predeploy: Running predeploy script: %s" % 
                      envpatch_cmd)
            rval = execute(ses, envpatch_cmd, DEBUG, log, to=PREPOST_TO)
        else:
            rval = None
        stage_exit(log)
        return rval

    @assignSequence(700)
    def app_deploy_stage(self):
        args = self.args
        auth = self.auth
        envid_l = self.envid_l
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)
        #######################################################################
        # get deploy options and run eom-rabbit-deploy 
        #######################################################################
        # We set args.deploy_success initially to True incase we are running with
        # deploy set to no, that way the latter stagers will still execute, however
        # If a deploy was specified and it FAILs the latter stages will not be
        # performed without a restart and --deploy=no
        if args.deploy[0] == 'no':
            args.deploy_success = False
            log.info("eom.skipappdply: Skipping Application Deployment")
            stage_exit(log)
            return None
        else:
            args.deploy_success = True  
            # If there is an ENV ticket, and this is not a restart,
            # Set the ENV ticket to App Deployment
            if args.envreq and not args.restart_issue:
                log.info("eom.appstate: Setting %s App Deploy state"
                         % args.envreq)
                # Make sure were logged into JIRA
                jira = JIRA(self.jira_options ,
                            basic_auth=(auth.user,auth.password))
                env_issue = jira.issue(args.envreq)
                env_transitions = jira.transitions(env_issue)
                for t in env_transitions:
                    if 'App Deployment' in t['name']:
                        jira.transition_issue(env_issue, int( t['id']),
                                              fields={})
                        log.info(
                            "eom.appsts: ENVREQ:%s set to App Deployment state" %\
                            args.envreq)
                        break;
                else:
                    log.warn(
                        "eom.notpro: ENV REQ:%s cannot be set to"
                        " App Deployment state" % args.envreq)
    
            cr = "--content-refresh" if args.content_refresh else ""
            deploy_timeout = (args.DEPLOY_TO + args.CONTENT_TO 
                              if args.content_refresh else args.DEPLOY_TO)

            # get the release ID and build label from the eom arguments 
            r = args.release
            bl = args.build_label
            # Now fet a data structure containing the current reg info based
            # On the suppiled build label
            build_label_cmd = ( "export P4USER=readonly ; build-id-info %s" % bl)  
            rval = execute(ses,build_label_cmd, DEBUG, log, result_set=["\{*\}",
                                                  ses.session.PROMPT])
            if rval == PEXOK :
                bii_str_array = (ses.before + ses.after).split("\n")
                bl_result_string = "".join(
                        [" " + x.replace("\r","") for x in bii_str_array[1:]])
                bl_result_dict = json.loads(bl_result_string)
                self.bl_result_dict = bl_result_dict
                log.info("eom.tcreat: Build Artifacts Structure:: %s" %
                         bl_result_string)
                build_label = bl_result_dict["build_label"]
                build_tree = bl_result_dict["build_tree_iteration"]

                build_tree_opt = "--tree %s" % build_tree if build_tree else ""
            else:
                log.error("eom.bidfail: build-id-info failed, can't continue")
                sys.exit(2)
                
            deploy_opts = " ".join(["--" + x  for x in args.deploy])
            deply_issue = args.envreq if args.envreq else pprj
            
            eom_rabbit_deploy_cmd = (
            "eom-rabbit-deploy --env %s --release %s --build-label %s %s %s %s"
            '|tee /dev/tty | jcmnt -f -u %s -i %s -t "Deploy %s"')%\
            (envid_l, r, build_label, deploy_opts, build_tree_opt,
             cr, auth.user, deply_issue, bl_result_dict["build_tree_id"])
#
#            eom_rabbit_deploy_cmd = (
#            "eom-rabbit-deploy --env %s --release %s --build-label %s %s %s"
#            '|tee /dev/tty | jcmnt -f -u %s -i %s -t "Deploy %s"')%\
#            (envid_l, r, bl,deploy_opts,cr,auth.user, 
#             deply_issue,bl)
    
            if args.envreq:
                pass
            log.info("eom.appstrt: Starting App deploy : %s" % 
                     eom_rabbit_deploy_cmd)
            rval = execute(ses, eom_rabbit_deploy_cmd, DEBUG,
                           log, to=deploy_timeout)
            ###################################################################
            # Check the results of app deploy to see if we can proceed
            ###################################################################
            if rval == PEXTO:   # app deply timed out write failure to log and ticket
                log.error("eom.appto: application deployment"
                          " timed out after %d seconds, exiting."
                          % deploy_timeout)
                env_appfail_string = ('jcmnt -f -u %s -i %s'
                            ' -t "App Deploy timed out after %d seconds."' % 
                                (auth.user, pprj, args.VERIFY_TO))
                rval = execute(ses, env_appfail_string, DEBUG,
                               log, to=args.VERIFY_TO)
                sys.exit(1)
                
            dply_result = ses.before.split('\n')
    
            for line in dply_result:
                if 'RABBIT Deployment' in line:
                    if 'SUCCESSFUL' in line:
                        args.deploy_success = True
                        log.info("eom.appdeplyok: %s deployment SUCCESS" % bl)
                        log.info(
                            "eom.appdeplywait: Sleeping %d seconds after deploy" % 
                            DEPLOY_WAIT)
                        time.sleep(DEPLOY_WAIT)
                    elif 'FAILED' in line:
                        args.deploy_success = False
                        log.info("eom.appdeplyfail: %s deployment FAIL" % bl)
                if 'Deployment logs:' in line:
                    deploy_logs = line.rstrip()
                    log.info("eom.appdeplylog: %s" % deploy_logs)
            stage_exit(log)
            return rval

    @assignSequence(800)
    def post_deploy_stage(self):
        args = self.args
        auth = self.auth
        envid_l = self.envid_l
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)
    
        #######################################################################
        # Run the content tool
        #######################################################################
        if  args.content_tool and (args.deploy_success or args.deploy[0] == 'no'):
            if args.envreq:
                pprj = args.envreq
            content_cmd = ("/nas/reg/bin/jiralab/jcontent -u %s -e %s 3 3 %s_content"
                    '| jcmnt -f -u %s -i %s -t "Apply Content Tool"') %\
                (auth.user, envid_l, args.release, auth.user, pprj)
            log.info ("eom.ctntool: Running content tool: %s" % 
                      content_cmd)
    
            rval = execute(ses, content_cmd, DEBUG, log, to=CTOOL_TO)
            if rval == PEXTO:
                execute(ses, 'jcmnt -u %s -i %s -t "Content Tool time-out after %s secs"' %\
                (auth.user, pprj, CTOOL_TO), DEBUG, log) 
        else:
            rval = None
        stage_exit(log)
        return rval

    @assignSequence(810)
    def net_deploy_stage(self):
        return None

    @assignSequence(900)
    def verification_stage(self):
        args = self.args
        auth = self.auth
        envid_l = self.envid_l
        ses = self.ses
        log = self.log
        pprj = self.pprj
        stage_entry(log)
        #######################################################################
        #        Perform big_IP verification: 
        #######################################################################
        if args.validate_bigip:
    
            if args.envreq:
                pprj = args.envreq
            valbigip_cmd = ("/nas/reg/bin/validate_bigip -e %s"
                    '| jcmnt -f -u %s -i %s -t "Big IP validation"') %\
                (envid_l, auth.user, pprj)
            log.info ("eom.valbigip: Running BigIP validation: %s" % 
                      valbigip_cmd)
            rval = execute(ses, valbigip_cmd, DEBUG, log)
        else:
            rval = None
        stage_exit(log)
        return rval

    @assignSequence(950)
    def smoketest_stage(self):
        return None

    @assignSequence(1000)
    def delivery_stage(self):
        args = self.args
        auth = self.auth
        ses = self.ses
        log = self.log
        stage_entry(log)
        #######################################################################
        #                         EXECUTION COMPLETE
        #######################################################################
        
        if args.envreq and args.deploy_success:
            log.info("eom.appstate: Setting %s Verification state"
                     % args.envreq)
            # Make sure were logged into JIRA
            jira = JIRA(self.jira_options ,basic_auth=(auth.user,auth.password))
            env_issue = jira.issue(args.envreq)
            env_transitions = jira.transitions(env_issue)
            for t in env_transitions:
                if 'Verify' in t['name']:
                    jira.transition_issue(env_issue, int( t['id']),
                                          fields={})
                    log.info(
                        "eom.appsts: ENVREQ:%s set to Verification state" %\
                        args.envreq)
                    break;
            else:
                log.warn(
                    "eom.notpro: ENV REQ:%s cannot be set to"
                    " Verification state" % args.envreq)
    
        if args.close_tickets and args.enval_success and args.deploy_success:
            db_issue = self.proproj_result_dict["dbtask"]
            pp_issue = self.proproj_result_dict["proproj"]
            if db_issue != "unknown":
                jclose_cmd = "jclose -u %s %s %s" % (auth.user, db_issue, pp_issue )
            else:
                jclose_cmd = "jclose -u %s %s" % (auth.user, pp_issue )
    
            log.info("eom.close: Closing build tickets: %s" % jclose_cmd)
            execute(ses, jclose_cmd, DEBUG, log)
        log.info("eom.done: Execution Complete @ %s UTC. Exiting.\n" %\
                 time.asctime(time.gmtime(time.time())))
        rval = 1
        stage_exit(log)
        return rval

###############################################################################
#                        program entry point 
###############################################################################    

if __name__ == "__main__":
    
    main()
