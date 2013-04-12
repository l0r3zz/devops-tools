#!/nas/reg/local/bin/python
# encoding: utf-8
'''
env-o-matic - Basic automation to buildout a virtual environment
              given an ENVIRONMENT ID and ENV request ticket
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
from eom_init import eom_startup

DEBUG = 0
REGSERVER = "srwd00reg010.stubcorp.dev"
REIMAGE_TO = 3600
DBGEN_TO = 3600
VERIFY_TO = 600

class EOMreimage(jiralab.Job):
    '''
    This class is a container for the re-imaging task, it inherits from 
    jiralab.Job so it can be scheduled as a thread, the overlayed run() 
    method does the actual work as the super class has created a ssh session
    on a reg server to be used
    '''
    def run(self):
            envid = self.args.env.upper()       # insure UPPERCASE env name
            envid_lower = self.args.env.lower() # insure lowercase env name
            envnum = envid[-2:]                 #just the number
            # Start re-imaging
            self.log.info("eom.reimg.start:(%s) Reimaging %s start @ %s UTC" %\
                     (self.name, envid, time.asctime(time.gmtime(time.time()))))
            reimage_cmd = (('time provision -e %s reimage -v 2>&1'
            '|jcmnt -f -u %s -i %s -t "Re-Imaging Environment for code deploy"')\
                % ( envid_lower, self.auth.user, self.pprd["proproj"]))
            if self.debug:
                self.log.debug("eom.deb:(%s) Issuing Re-image command: %s" %\
                               (self.name, reimage_cmd))
            rval = self.ses.docmd(reimage_cmd,
                                  [self.ses.session.PROMPT],timeout=REIMAGE_TO)
            if self.debug:
                self.log.debug ("eom.deb:(%s) Rval= %d; \nbefore: %s\nafter: %s"
                        % (self.name, rval, self.ses.before, self.ses.after))
            self.log.info("eom.sleep:(%s) Re-image complete, sleeping 5 minutes"
                          % self.name)
            time.sleep(300)
            self.log.info("eom.reimg.done:(%s) Reimaging done @ %s UTC" %
                          (self.name, time.asctime(time.gmtime(time.time()))))

class EOMdbgen(jiralab.Job):
    '''
    This class is a container for the database generation task, it inherits from 
    jiralab.Job so it can be scheduled as a thread, the overlayed run() 
    method does the actual work as the super class has created a ssh session
    on a reg server to be used
    '''
    def run(self):
            reg_session = self.ses
            envid = self.args.env.upper()       # insure UPPERCASE env name
            envid_lower = self.args.env.lower() # insure lowercase env name
            envnum = envid[-2:]                 #just the number
            self.log.info(
                    "eom.dbcreate.start: Building Database start @ %s UTC," %\
                     time.asctime(time.gmtime(time.time())))

            if self.args.debug > 1:
                dbgendb = "-D"
            else:
                dbgendb = ""


            pp_path = ("" if self.args.nopostpatch else\
               '--postpatch="/nas/reg/bin/env_setup_patch/scripts/dbgenpatch"')

            dbgen_build_cmd = ('time dbgen -u %s -e %s -r %s %s %s %s'
            ' |jcmnt -f -u %s -i %s -t "Automatic DB Generation"') % \
                (self.auth.user, envid, self.args.release, pp_path, self.use_siebel, dbgendb,
                 self.auth.user, self.pprd["dbtask"])

            rval = reg_session.docmd(dbgen_build_cmd,
                                [reg_session.session.PROMPT],timeout=DBGEN_TO)
            if DEBUG:
                self.log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                           (rval, reg_session.before, reg_session.after))
            self.log.info("eom.dbcreate.done: Database DONE @ %s UTC," %\
                     time.asctime(time.gmtime(time.time())))

def main(argv=None): # IGNORE:C0111

    try:  # Catch keyboard interrupts (^C)
        start_ctx = eom_startup(argv)
        args = start_ctx.args
        exit_status =0
        # Check for various valid options configurations here
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

        # Log the start of the show
        log.info('eom.start: %s :: %s' % (start_ctx.program_log_id, args))

        if args.debug:
            DEBUG = True
            log.setLevel("DEBUG")
        else:
            DEBUG = False

        envid = args.env.upper()       # insure UPPERCASE environment name
        envid_lower = args.env.lower() # insure lowercase environment name
        envnum = envid[-2:]            #just the number
        
        # Get the login credentials from the user or from the vault
        auth = jiralab.Auth(args)
        auth.getcred()

        # Login to the reg server
        # We do all orchestration from a single reg erver
        log.info ("eom.login: Logging into %s  @ %s UTC" %\
                (REGSERVER, time.asctime(time.gmtime(time.time()))))
        reg_session = jiralab.CliHelper(REGSERVER)
        rval = reg_session.login(auth.user,auth.password,prompt="\$[ ]")
        if DEBUG:
            log.debug ("eom.deb: before: %s\nafter: %s" % (reg_session.before,
                                                           reg_session.after))
        # Become the relmgt user, all tools are run as this user
        log.info ("eom.relmgt: Becoming relmgt @ %s UTC" %\
                  time.asctime(time.gmtime(time.time())))
        rval = reg_session.docmd("sudo -i -u relmgt",
                                 [reg_session.session.PROMPT])
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))

        # Create a PROPROJ and DB ticket for the ENV
        log.info ("eom.cjira: Creating JIRA issues")
        try:
            jreg = jiralab.Reg(args.release) # get reg build mapping for JIRA
            jira_release = jreg.jira_release
        except jiralab.JIRALAB_CLI_ValueError :
            print( "eom.relerr: No release named %s" % args.release)
            exit(2)

        use_siebel = ("--withsiebel" if args.withsiebel else "")
        proproj_cmd =  "proproj -u %s -e %s -r %s %s " % (auth.user, args.env,
                                                    jira_release, use_siebel)
        rval = reg_session.docmd(proproj_cmd, ["\{*\}",
                                               reg_session.session.PROMPT])
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval,
                                        reg_session.before, reg_session.after))
        if rval == 1 :
            PPRESULT = 1
            proproj_result_string = (
                            reg_session.before + reg_session.after).split("\n")
            proproj_result_dict = json.loads(proproj_result_string[PPRESULT])
            log.info("eom.tcreat: Ticket Creation Structure:: %s" %\
                     proproj_result_string[PPRESULT])
        else:
            log.error(
                "eom.tcreat.err: Error in ticket creation: %s%s \nExiting.\n" %\
                (reg_session.before, reg_session.after))
            exit(2)

        # If there is an ENV ticket, link the proproj to it.
        # And set the ENVREQ Status to Provisioning
        if args.envreq:
            log.info("eom.tlink: Linking propoj:%s to ENV request:%s" %\
                     (proproj_result_dict["proproj"], args.envreq))
            jira_options = {'server': 'https://jira.stubcorp.dev/',
                        'verify' : False,
                        }
            jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
            link = jira.create_issue_link(type="Dependency",
                                    inwardIssue=args.envreq,
                                    outwardIssue=proproj_result_dict["proproj"])
            env_issue = jira.issue(args.envreq)
            env_transitions = jira.transitions(env_issue)
            for t in env_transitions:
                if 'Provisioning' in t['name']:
                    jira.transition_issue(env_issue, int( t['id']), fields={})
                    env_issue.update(customfield_10761=(
                                                    date.today().isoformat()))
                    log.info(
                        "eom.prvsts: ENVREQ:%s set to Provisioning state" %\
                        args.envreq)
                    break;
            else:
                log.warn(
                    "eom.notpro: ENV REQ:%s cannot be set to provision state" %\
                     args.envreq)

        # Handle re-imaging here
        if args.skip_reimage:
            log.info("eom.noreimg: Skipping the re-image of %s" % envid)
        else:
            # Start re-imaging in a thread
            reimage_task = EOMreimage(args, auth, log,
                            name="re-image-thread",
                            proproj_result_dict=proproj_result_dict)
            reimage_task.daemon = True
            reimage_task.start()
        #######################################################################
        #                   Handle database creation here
        #######################################################################
        if args.skip_dbgen:
            log.info("eom.nodbgen: Skipping the db creation of %s" % envid)
        else:
            dbgen_task = EOMdbgen(args, auth, log,
                            name="re-image-thread",
                            proproj_result_dict=proproj_result_dict,
                            session=reg_session,
                            use_siebel=use_siebel)
            dbgen_task.daemon = True
            dbgen_task.start()
            log.info("eom.dbgwait: Waiting for dbgen to complete")
            dbgen_task.join() #wait for the dbgen task to complete

        #######################################################################
        #   If we are re-imaging, run the validation script on the results
        #######################################################################
        if not args.skip_reimage:
            log.info("eom.rimwait: Waiting for re-image to complete")
            reimage_task.join() # wait for the re-image to complete if it hasn't
            log.info("eom.rimgval: Verifying re-imaging of roles in %s" % envid)
            reimage_validate_string = ('verify-reimage %s '
            '|jcmnt -f -u %s -i %s -t "check this list for re-imaging status"')%\
                (envid_lower, auth.user, proproj_result_dict["proproj"])
            rval = reg_session.docmd(reimage_validate_string,
                            [reg_session.session.PROMPT],timeout=VERIFY_TO)
            if DEBUG:
                log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                           (rval, reg_session.before, reg_session.after))

        #######################################################################
        # We should be done with Provisioning, run the env-validate suit
        #######################################################################
        log.info("eom.envval: Performing Automatic Validation of %s" %\
                 envid_lower)
        if 'srwe' in envid_lower :
            env_validate_string = ('env-validate -d srwe -e %s 2>&1'
            ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
            (envnum, auth.user, proproj_result_dict["proproj"])
        else :
            env_validate_string = ('env-validate -e %s 2>&1 '
            '| jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
            (envnum, auth.user, proproj_result_dict["proproj"])

        rval = reg_session.docmd(env_validate_string,
                                 [reg_session.session.PROMPT],timeout=VERIFY_TO)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))
            
        #######################################################################
        #                         EXECUTION COMPLETE
        #######################################################################
        log.info("eom.done: Execution Complete @ %s UTC. Exiting.\n" %\
                 time.asctime(time.gmtime(time.time())))
        exit(0)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
#    except Exception, e:
#        if DEBUG:
#            raise
#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + str(e) + "\n")
#        log.error(program_name + ": " + str(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help\n")
#        return 2

if __name__ == "__main__":
    sys.exit(main())
