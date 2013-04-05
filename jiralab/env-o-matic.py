#!/nas/reg/local/bin/python
# encoding: utf-8
'''
env-o-matic - Basic automation to buildout a virtual environment given an ENVIRONMENT ID
              and ENV request ticket
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
import time
from datetime import date
import mylog
import threading

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.994
__date__ = '2012-11-20'
__updated__ = '2013-04-04'

TESTRUN = 0
DEBUG = 0
REGSERVER = "srwd00reg010.stubcorp.dev"
REIMAGE_TO = 3600
DBGEN_TO = 3600
VERIFY_TO = 600

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

class Job(threading.Thread):
    '''
    Inherit this class to create parallelizable tasks, just add run() ;)
    '''
    def __init__(self, args, auth, log, **kwargs):
        '''
        Initialize the job, set up required values and log into a REG server
        Required Args:
            args    - args that eom was invoked with.
            auth    - the authentication/authorization context to perform the job in.
            log     - logging object
        Optional Args:
            debug   - set to True to print out debugging
            session - if set, don't perform a login, but use this session context to run the job.
        '''
        #  Call the initializer of the superclass
        threading.Thread.__init__(self)

        self.args = args
        self.auth = auth
        self.log = log
        # set some defaults for kwargs not supplied
        self.debug = kwargs.get('debug', False)
        self.ses = kwargs.get('session', None)
        self.pprd = kwargs.get('proproj_result_dict', None)
        self.name = kwargs.get('name', None)


        if not self.ses :
            # Login to the reg server
            log.info ("eom.login:(%s) Logging into %s  @ %s UTC" %
                      (self.name, REGSERVER, time.asctime(time.gmtime(time.time()))))
            # Create a remote shell object
            self.ses = jiralab.CliHelper(REGSERVER)
            self.ses.login(self.auth.user, self.auth.password,prompt="\$[ ]")
            if self.debug:
                log.debug ("eom.deb:(%s) before: %s\nafter: %s" %
                           (self.name, self.session.before, self.session.after))
            # sudo to the relmgt user
            log.info ("eom.relmgt:(%s) Becoming relmgt @ %s UTC" %
                      (self.name, time.asctime(time.gmtime(time.time()))))
            rval = self.ses.docmd("sudo -i -u relmgt",[self.ses.session.PROMPT])
            if self.debug:
                log.debug ("eom.deb:(%s) Rval= %d; before: %s\nafter: %s" %
                           (self.name, rval, self.ses.before, self.ses.after))

class EOMreimage(Job):
    def run(self):
            envid = self.args.env.upper()       # insure UPPERCASE environment name
            envid_lower = self.args.env.lower() # insure lowercase environment name
            envnum = envid[-2:]                 #just the number
            # Start re-imaging
            self.log.info("eom.reimg.start:(%s) Reimaging %s start @ %s UTC, ..." %
                     (self.name, envid, time.asctime(time.gmtime(time.time()))))
            reimage_cmd = 'time provision -e %s reimage -v 2>&1 |jcmnt -f -u %s -i %s -t "Re-Imaging Environment for code deploy"' % \
                ( envid_lower, self.auth.user, self.pprd["proproj"])
            if self.debug:
                self.log.debug("eom.deb:(%s) Issuing Re-image command: %s" % (self.name, reimage_cmd))
            rval = self.ses.docmd(reimage_cmd,[self.ses.session.PROMPT],timeout=REIMAGE_TO)
            if self.debug:
                self.log.debug ("eom.deb:(%s) Rval= %d; \nbefore: %s\nafter: %s" % (self.name, rval, self.ses.before, self.ses.after))
            self.log.info("eom.sleep5: (%s) Re-image complete, sleeping 5 minutes" % self.name)
            time.sleep(300)
            self.log.info("eom.reimg.done:(%s) Reimaging done @ %s UTC" % (self.name, time.asctime(time.gmtime(time.time()))))



def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_log_id = "%s %s (%s)" % (program_name,program_version, program_build_date)

    try:  # Catch keyboard interrupts (^C)
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env", help="environment name to provision (example: srwd03" )
        parser.add_argument("-q", "--envreq", dest="envreq", default=None, help="environment request issue ID (example: ENV_707" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument("-l", "--logfile", dest="logfile", default="/nas/reg/log/jiralab/env-o-matic.log",  help="file to log to (if none, log to console" )
        parser.add_argument('-v', '--version', action='version', version=program_version_message)
        parser.add_argument('--skipreimage', action='store_true', dest="skip_reimage", default=False, help="set to skip the re-image operation")
        parser.add_argument('--skipdbgen', action='store_true', dest="skip_dbgen", default=False, help="set to skip the db creation operation")
        parser.add_argument("--nopostpatch", dest="nopostpatch", action='store_true', default=False, help="set to DISABLE scanning patch directory")
        parser.add_argument("--withsiebel", dest="withsiebel", action='store_true', default=False, help="set to build a Siebel database along with Delphix")
        parser.add_argument('-D', '--debug', dest="debug", action='count', default=0, help="turn on DEBUG additional Ds increase verbosity")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()
        exit_status =0

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

        # Start Logging
        try:
            if args.logfile:
                log = mylog.logg('env-o-matic', llevel='INFO', gmt=True,
                                  lfile=args.logfile, cnsl=True)
            else:
                log = mylog.logg('env-o-matic', llevel='INFO', gmt=True,
                                  cnsl=True, sh=sys.stdout)
        except UnboundLocalError:
            print("Can't open Log file, check path\n")
            sys.exit(1)

        log.info('eom.start: %s :: %s' % (program_log_id, args))


        if args.debug:
            DEBUG = True
            log.setLevel("DEBUG")
        else:
            DEBUG = False

        envid = args.env.upper()       # insure UPPERCASE environment name
        envid_lower = args.env.lower() # insure lowercase environment name
        envnum = envid[-2:]            #just the number

        auth = jiralab.Auth(args)
        auth.getcred()


        # Login to the reg server
        log.info ("eom.login: Logging into %s  @ %s UTC" % (REGSERVER, time.asctime(time.gmtime(time.time()))))
        reg_session = jiralab.CliHelper(REGSERVER)
        rval = reg_session.login(auth.user,auth.password,prompt="\$[ ]")
        if DEBUG:
            log.debug ("eom.deb: before: %s\nafter: %s" % (reg_session.before, reg_session.after))


        log.info ("eom.relmgt: Becoming relmgt @ %s UTC" % time.asctime(time.gmtime(time.time())))
        rval = reg_session.docmd("sudo -i -u relmgt",[reg_session.session.PROMPT])
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))

        # Create a PROPROJ and DB ticket for the ENV
        log.info ("eom.cjira: Creating JIRA issues")
        # if -DDD turn on debugging for proproj

        # FIX ME  just a quick hack, this should be done by a mapping function so that we don't have
        # to continuously track it
        jira_dict = {"rb1304" : "ecomm_13.4",
                     "rb1304.1" : "ecomm_13.4.1",
                     "rb1305" : "ecomm_13.5",
                     "rb1305.1" : "ecomm_13.5.1",
                     "rb_ecomm_13_4_1" : "ecomm_13.4.1",
                     "rb_ecomm_13_5" : "ecomm_13.5",
                     "rb_ecomm_13_5_1" : "ecomm_13.5.1",
                      }
        if args.release in jira_dict:
            jira_release = jira_dict[args.release]
        else:
            log.error( "eom.relerr: No release named %s" % args.release)
            exit(2)


        use_siebel = ("--withsiebel" if args.withsiebel else "")
        proproj_cmd =  "proproj -u %s -e %s -r %s %s " % (auth.user, args.env, jira_release, use_siebel)
        rval = reg_session.docmd(proproj_cmd, ["\{*\}", reg_session.session.PROMPT])
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
        if rval == 1 :
            PPRESULT = 1
            proproj_result_string = (reg_session.before + reg_session.after).split("\n")
            proproj_result_dict = json.loads(proproj_result_string[PPRESULT])
            log.info("eom.tcreat: Ticket Creation Structure:: %s" % proproj_result_string[PPRESULT])
        else:
            log.error("eom.tcreat.err: Error in ticket creation: %s%s \nExiting.\n" %(reg_session.before, reg_session.after))
            exit(2)

        # If there is an ENV ticket, link the proproj to it. And set the ENVREQ Status to Provisioning
        if args.envreq:
            log.info("eom.tlink: Linking propoj:%s to ENV request:%s" % (proproj_result_dict["proproj"], args.envreq))
            jira_options = { 'server': 'https://jira.stubcorp.dev/' }
            jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
            link = jira.create_issue_link(type="Dependency", inwardIssue=args.envreq,
                                      outwardIssue=proproj_result_dict["proproj"])
            env_issue = jira.issue(args.envreq)
            env_transitions = jira.transitions(env_issue)
            for t in env_transitions:
                if 'Provisioning' in t['name']:
                    jira.transition_issue(env_issue, int( t['id']), fields={})
                    env_issue.update(customfield_10761=(date.today().isoformat()))
                    log.info("eom.prvsts: ENVREQ:%s set to Provisioning state" % args.envreq)
                    break;
            else:
                log.warn("eom.notpro: ENV REQ:%s cannot be set to provision state" % args.envreq)

        if args.skip_reimage:
            log.info("eom.noreimg: Skipping the re-image of %s" % envid)
        else:
            # Start re-imaging in a thread
            reimage_task = EOMreimage(args, auth, log,
                            name="re-image-thread", proproj_result_dict=proproj_result_dict)
            reimage_task.daemon = True
            reimage_task.start()

        if args.skip_dbgen:
            log.info("eom.nodbgen: Skipping the db creation of %s" % envid)
        else:
            log.info("eom.dbcreate.start: Building Database start @ %s UTC," % time.asctime(time.gmtime(time.time())))

            if args.debug > 1:
                dbgendb = "-D"
            else:
                dbgendb = ""


            pp_path = ("" if args.nopostpatch else '--postpatch="/nas/reg/bin/env_setup_patch/scripts/dbgenpatch"')

            dbgen_build_cmd = 'time dbgen -u %s -e %s -r %s %s %s %s |jcmnt -f -u %s -i %s -t "Automatic DB Generation"' % \
                (args.user, envid, args.release, pp_path, use_siebel, dbgendb, auth.user, proproj_result_dict["dbtask"])

            rval = reg_session.docmd(dbgen_build_cmd,[reg_session.session.PROMPT],timeout=DBGEN_TO)
            if DEBUG:
                log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
            log.info("eom.dbcreate.done: Database DONE @ %s UTC," % time.asctime(time.gmtime(time.time())))

        if not args.skip_reimage:
            log.info("eom.rimwait: Waiting for re-image to complete")
            reimage_task.join() # wait for the re-image to complete if it hasn't
            log.info("eom.rimgval: Verifying re-imaging of roles in %s" % envid)
            reimage_validate_string = 'verify-reimage %s | jcmnt -f -u %s -i %s -t "check this list for re-imaging status"' % \
                (envid_lower, auth.user, proproj_result_dict["proproj"])
            rval = reg_session.docmd(reimage_validate_string,[reg_session.session.PROMPT],timeout=VERIFY_TO)
            if DEBUG:
                log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))

        log.info("eom.envval: Performing Automatic Validation of %s" % envid_lower)
        if 'srwe' in envid_lower :
            env_validate_string = 'env-validate -d srwe -e %s 2>&1 | jcmnt -f -u %s -i %s -t "Automatic env-validation"' % \
            (envnum, auth.user, proproj_result_dict["proproj"])
        else :
            env_validate_string = 'env-validate -e %s 2>&1 | jcmnt -f -u %s -i %s -t "Automatic env-validation"' % \
            (envnum, auth.user, proproj_result_dict["proproj"])

        rval = reg_session.docmd(env_validate_string,[reg_session.session.PROMPT],timeout=VERIFY_TO)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))

        log.info("eom.done: Execution Complete @ %s UTC. Exiting.\n" %  time.asctime(time.gmtime(time.time())))
        exit(0)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        log.error(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2

if __name__ == "__main__":

    if TESTRUN:
        import doctest
        doctest.testmod()

    sys.exit(main())
