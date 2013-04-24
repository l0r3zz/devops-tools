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
import errno
import re
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
CMD_TO = 120
DEPLOY_WAIT = 600
CTOOL_TO = 600
TJOIN_TO = 60.0

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
                                  [self.ses.session.PROMPT],
                                  timeout=self.args.REIMAGE_TO)
            if self.debug:
                self.log.debug ("eom.deb:(%s) Rval= %d; \nbefore: %s\nafter: %s"
                        % (self.name, rval, self.ses.before, self.ses.after))
            self.log.info("eom.sleep:(%s) Re-image complete, sleeping 5 minutes"
                          % self.name)
            time.sleep(300)
    
            self.log.info("eom.rimgval: Verifying re-imaging of roles in %s"
                          % envid)

            reimage_validate_string = ('verify-reimage %s '
            '|jcmnt -f -u %s -i %s -t'
            ' "check this list for re-imaging status"'%
                (envid_lower, self.auth.user, self.pprd["proproj"]))
            rval = self.ses.docmd(reimage_validate_string,
                            [self.ses.session.PROMPT],
                            timeout=self.args.VERIFY_TO)
            if DEBUG:
                self.log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                           (rval, self.ses.before, self.ses.after))

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
                    "eom.dbcreate.start:(%s) Building Database start @ %s UTC,"
                    % (self.name, time.asctime(time.gmtime(time.time()))))

            if self.args.debug > 1:
                dbgendb = "-D"
            else:
                dbgendb = ""


            pp_path = ("" if self.args.nopostpatch else\
               '--postpatch="/nas/reg/bin/env_setup_patch/scripts/dbgenpatch"')

            dbgen_build_cmd = ('time dbgen -u %s -e %s -r %s %s %s %s'
            ' |jcmnt -f -u %s -i %s -t "Automatic DB Generation"') % \
                (self.auth.user, envid, self.args.release, 
                 pp_path, self.use_siebel, dbgendb,
                 self.auth.user, self.pprd["dbtask"])

            rval = reg_session.docmd(dbgen_build_cmd,
                                [reg_session.session.PROMPT],
                                timeout=self.args.DBGEN_TO)
            if rval > 1:
                self.log.warn(
                    "eom.dbcreate.to:(%s) dbgen did not complete within %d sec"
                    % (self.name, self.args.DBGEN_TO))
            if DEBUG:
                self.log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %
                           (rval, reg_session.before, reg_session.after))
            self.log.info("eom.dbcreate.done:(%s) Database DONE @ %s UTC," %
                     (self.name, time.asctime(time.gmtime(time.time()))))

def main(argv=None): # IGNORE:C0111

    #######################################################################
    # Get cmd line options, start logging, read ini file, validate options
    #######################################################################

    start_ctx = eom_startup(argv)
    args = start_ctx.args
    exit_status =0

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


    try:
        jreg = jiralab.Reg(args.release) # get reg build mapping for JIRA
        jira_release = jreg.jira_release
    except jiralab.JIRALAB_CLI_ValueError :
        print( "eom.relerr: No release named %s" % args.release)
        exit(2)

    #######################################################################
    #                   restart option
    #######################################################################
    if  args.restart_issue:
        restart_issue = args.restart_issue
        # FIXME: we need code here to find the linked issue keys to fill
        # in the correct dbtask and potentially the correct proproj
        if 'PROPROJ' in restart_issue:
            proproj_result_dict = {
                    "dbtask" : "unknown",
                    "envid" : envid_lower,
                    "proproj" : restart_issue,
                    "envreq"  : "unknown"
                    }
        else:
            proproj_result_dict = {
                    "dbtask" : "unknown",
                    "envid" : envid_lower,
                    "proproj" : "unknown",
                    "envreq"  : restart_issue,
                    }
            
        if args.envreq:
            proproj_result_dict["envreg"] = args.envreq
            pprj = proproj_result_dict["envreg"]
        else:    
            pprj =proproj_result_dict["proproj"]

        log.info("eom.rststruct: Restarting with structure: %s" %
                 json.dumps(proproj_result_dict))
    #######################################################################
    #                   First time ticket creation here
    #######################################################################
    else:
        # Create a PROPROJ and DB ticket for the ENV
        log.info ("eom.cjira: Creating JIRA issues")
        use_siebel = ("--withsiebel" if args.withsiebel else "")
        proproj_cmd =  "proproj -u %s -e %s -r %s %s " % (auth.user, 
                                        args.env, jira_release, use_siebel)
        rval = reg_session.docmd(proproj_cmd, ["\{*\}",
                                               reg_session.session.PROMPT])
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))
        if rval == 1 :
            PPRESULT = 1
            proproj_result_string = (
                        reg_session.before + reg_session.after).split("\n")
            proproj_result_dict = json.loads(
                                            proproj_result_string[PPRESULT])
            log.info("eom.tcreat: Ticket Creation Structure:: %s" %\
                     proproj_result_string[PPRESULT])
            pprj =proproj_result_dict["proproj"]
        else:
            log.error(
                "eom.tcreat.err: Error in ticket "
                "creation: %s%s \nExiting.\n" %
                (reg_session.before, reg_session.after))
            exit(2)

    # Login to JIRA so we can manipulate tickets...
    jira_options = {'server': 'https://jira.stubcorp.dev/',
                'verify' : False,
                }
    jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
    
    # If there is an ENV ticket, and this is not a restart,
    # link the proproj to it. And set the ENVREQ Status to Provisioning
    if args.envreq and not args.restart_issue:
        log.info("eom.tlink: Linking propoj:%s to ENV request:%s" %\
                 (pprj, args.envreq))

        link = jira.create_issue_link(type="Dependency",
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

    #######################################################################
    #                   Handle re-image here
    #######################################################################
    if args.skipreimage:
        log.info("eom.noreimg: Skipping the re-image of %s" % envid)
    elif 'unknown' in pprj:
        log.info("eom.reimgenv: Reimaging with an ENV issue"
                 " not yet supported. Skipping...")
        args.skipreimage = True 
    else:
        # Start re-imaging in a thread
        reimage_task = EOMreimage(args, auth, log,
                        name="re-image-thread",
                        proproj_result_dict=proproj_result_dict)
        reimage_task.daemon = True
        reimage_task.start()
        log.info("eom.rimwait: Waiting for re-image to complete")
    #######################################################################
    #                   Handle database creation here
    #######################################################################
    if args.skipdbgen:
        log.info("eom.nodbgen: Skipping the db creation of %s" % envid)
    elif 'unknown' in pprj:
        log.warn("eom.nodbgenrst: dbgen restart not yet supported")
        args.skipdbgen = True
    else:
        dbgen_task = EOMdbgen(args, auth, log,
                        name="dbgen-thread",
                        proproj_result_dict=proproj_result_dict,
                        session=reg_session,
                        use_siebel=use_siebel)
        dbgen_task.daemon = True
        dbgen_task.start()
        log.info("eom.dbgwait: Waiting for dbgen to complete")


    #######################################################################
    #   Wait for all the threads to complete
    #######################################################################
    if not args.skipdbgen:
        while dbgen_task.is_alive():
            dbgen_task.join(TJOIN_TO)
        log.info("eom.dbtdone: Dbgen thread DONE")
    if not args.skipreimage:
        while reimage_task.is_alive():
            reimage_task.join(TJOIN_TO)
        log.info("eom.reimtdone: reimage thread DONE")
#    if not args.skipreimage and not args.skipdbgen:
#        reimage_running, dbgen_running = True
#        while dbgen_task.is_alive() or reimage_task.is_alive():
#            reimage_task.join(TJOIN_TO)
#            if reimage_running and not reimage_task.is_alive():
#                reimage_running = False
#                log.info("eom.reimtdone: Reimage task DONE")
#            dbgen_task.join(TJOIN_TO)
#            if dbgen_running and not dbgen_task.is_alive():
#                dbgen_running = False
#                log.info("eom.dbtdone: Dbgen task DONE")


    #######################################################################
    # We should be done with Provisioning, run the env-validate suit
    #######################################################################
    log.info("eom.envval: Performing Automatic Validation of %s" %\
             envid_lower)
    args.enval_success = False
    # Set up the env_validate commands so that they write to the
    # tty as well as pipe to the jcomment utility.  We'll use the tty
    # output to determine whether to continue with app deploy.
    if 'srwe' in envid_lower :
        env_validate_string = ('env-validate -d srwe -e %s 2>&1'
        '| tee /dev/tty'
        ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
        (envnum, auth.user, pprj)
    else :
        env_validate_string = ('env-validate -e %s 2>&1 '
        '| tee /dev/tty'
        ' | jcmnt -f -u %s -i %s -t "Automatic env-validation"') % \
        (envnum, auth.user, pprj)

    rval = reg_session.docmd(env_validate_string,
                             [reg_session.session.PROMPT],timeout=args.VERIFY_TO)
    if DEBUG:
        log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                   (rval, reg_session.before, reg_session.after))
    #######################################################################
    # Check the results of env-validate to see if we can proceed
    #######################################################################
    if rval > 1:   # env-validate timed out write failure to log and ticket
        log.error("eom.envalto: env-validation"
                  " timed out after %d seconds, exiting." % args.VERIFY_TO)
        env_valfail_string = ('jcmnt -f -u %s -i %s'
                        ' -t "env-validate timed out after %d seconds."' % 
                        (auth.user, pprj, args.VERIFY_TO))
        rval = reg_session.docmd(env_valfail_string,
                             [reg_session.session.PROMPT],timeout=args.VERIFY_TO)
        sys.exit(1)
    # regex's to look for PASS or if not PASS make sure that the failures
    # are not because of ssh or sudo failures
    rgx_envPASS = "env-validate\[[0-9]*\] results: PASS"
    rgx_envsudoFAIL = "env-validate\[[0-9]*\] PRIORITY=WARNING .+sudo test"
    rgx_envsshFAIL = "env-validate\[[0-9]*\] PRIORITY=WARNING .+ssh test"
    
    if not re.search(rgx_envPASS,reg_session.before):
        # validation didn't pass, see if we want ti ignore it
        if args.ignorewarnings and (
            not re.search(rgx_envsudoFAIL, reg_session.before)) and (
            not re.search(rgx_envsshFAIL, reg_session.before)):
            log.warn("eom.prvwarn: Warnings present, proceeding anyway")
        else:
            log.info("eom.prvext Provision step had unrecoverable warnings"
                     " @ %s UTC. Exiting.\n" %\
                     time.asctime(time.gmtime(time.time())))
            sys.exit(1)
    else:
        log.info("eom.valpass: env-validation PASS for %s" % envid_lower)
        args.enval_success = True
    #######################################################################
    # Run the pre deploy script
    #######################################################################
    if not args.noprepatch and args.deploy[0] != 'no':
        envpatch_cmd = ("/nas/reg/bin/env_setup_patch/scripts/envpatch %s"
                '| jcmnt -f -u %s -i %s -t "Automatic predeploy script"') %\
            (envid_lower, auth.user, pprj)
        log.info ("eom.predeploy: Running predeploy script: %s" % 
                  envpatch_cmd)
        rval = reg_session.docmd(envpatch_cmd,
                            [reg_session.session.PROMPT], timeout=CMD_TO)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))
    #######################################################################
    # get deploy options and run eom-rabbit-deploy 
    #######################################################################
    # We set args.deploy_success initially to True incase we are running with
    # deploy set to no, that way the latter stagers will still execute, however
    # If a deploy was specified and it FAILs the latter stages will not be
    # performed without a restart and --deploy=no
    args.deploy_success = True  
    if args.deploy[0] != 'no':
        # If there is an ENV ticket, and this is not a restart,
        # Set the ENV ticket to App Deployment
        if args.envreq and not args.restart_issue:
            log.info("eom.appstate: Setting %s App Deploy state"
                     % args.envreq)
            # Make sure were logged into JIRA
            jira = JIRA(jira_options ,basic_auth=(auth.user,auth.password))
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
        r = args.release
        bl = args.build_label
        deploy_opts = " ".join(["--" + x  for x in args.deploy])
        deply_issue = args.envreq if args.envreq else pprj
        eom_rabbit_deploy_cmd = (
        "eom-rabbit-deploy --env %s --branch %s --build-label %s %s %s"
        '|tee /dev/tty | jcmnt -f -u %s -i %s -t "Deploy %s"')%\
        (envid_lower,r,bl,deploy_opts,cr,auth.user, 
         deply_issue,bl)

        if args.envreq:
            pass
        log.info("eom.appstrt: Starting App deploy : %s" % 
                 eom_rabbit_deploy_cmd)
        rval = reg_session.docmd(eom_rabbit_deploy_cmd,
                    [reg_session.session.PROMPT], timeout=deploy_timeout)
        ###################################################################
        # Check the results of app deploy to see if we can proceed
        ###################################################################
        if rval > 1:   # env-validate timed out write failure to log and ticket
            log.error("eom.appto: application deployment"
                      " timed out after %d seconds, exiting."
                      % deploy_timeout)
            env_appfail_string = ('jcmnt -f -u %s -i %s'
                        ' -t "App Deploy timed out after %d seconds."' % 
                            (auth.user, pprj, args.VERIFY_TO))
            rval = reg_session.docmd(env_appfail_string,
                            [reg_session.session.PROMPT],timeout=CMD_TO)
            sys.exit(1)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))
        dply_result = reg_session.before.split('\n')

        for line in dply_result:
            if 'RABBIT Deployment' in line:
                if 'SUCCESSFUL' in line:
                    args.deploy_success = True
                    log.info("eom.appdeplyok: %s deployment SUCCESS" % bl)
                elif 'FAILED' in line:
                    args.deploy_success = False
                    log.info("eom.appdeplyfail: %s deployment FAIL" % bl)
            if 'Deployment logs:' in line:
                deploy_logs = line.rstrip()
                log.info("eom.appdeplylog: %s" % deploy_logs)
        
    #######################################################################
    #        Perform big_IP verification: 
    #######################################################################
    if args.validate_bigip and args.deploy_success:
        log.info("eom.appdeplywait: Sleeping %d seconds after deploy" % 
                 DEPLOY_WAIT)
        time.sleep(DEPLOY_WAIT)
        if args.envreq:
            pprj = args.envreq
        valbigip_cmd = ("/nas/reg/bin/validate_bigip -e %s"
                '| jcmnt -f -u %s -i %s -t "Big IP validation"') %\
            (envid_lower, auth.user, pprj)
        log.info ("eom.valbigip: Running BigIP validation: %s" % 
                  valbigip_cmd)
        rval = reg_session.docmd(valbigip_cmd,
                            [reg_session.session.PROMPT], timeout=CMD_TO)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))                         
    #######################################################################
    # Run the content tool
    #######################################################################
    if  args.content_tool and args.deploy_success:
        if args.envreq:
            pprj = args.envreq
        content_cmd = ("/nas/reg/bin/jiralab/jcontent -u %s -e %s 3 3 %s_content"
                '| jcmnt -f -u %s -i %s -t "Apply Content Tool"') %\
            (auth.user, envid_lower, args.release, auth.user, pprj)
        log.info ("eom.ctntool: Running content tool: %s" % 
                  content_cmd)
        rval = reg_session.docmd(content_cmd,
                            [reg_session.session.PROMPT], timeout=CTOOL_TO)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))

    #######################################################################
    #                         EXECUTION COMPLETE
    #######################################################################
    
    if args.envreq and args.deploy_success:
        log.info("eom.appstate: Setting %s Verification state"
                 % args.envreq)
        # Make sure were logged into JIRA
        jira = JIRA(jira_options ,basic_auth=(auth.user,auth.password))
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
        db_issue = proproj_result_dict["dbtask"]
        pp_issue = proproj_result_dict["proproj"]
        if db_issue != "unknown":
            jclose_cmd = "jclose -u %s %s %s" % (auth.user, db_issue, pp_issue )
        else:
            jclose_cmd = "jclose -u %s %s" % (auth.user, pp_issue )

        rval = reg_session.docmd(jclose_cmd,
                            [reg_session.session.PROMPT], timeout=CTOOL_TO)
        log.info("eom.close: Closing build tickets: %s" % jclose_cmd)

        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" %\
                       (rval, reg_session.before, reg_session.after))

    log.info("eom.done: Execution Complete @ %s UTC. Exiting.\n" %\
             time.asctime(time.gmtime(time.time())))
    exit(0)



if __name__ == "__main__":
    try:  # Catch keyboard interrupts (^C)
        exit_status = main()
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        sys.exit(0)

#    except Exception, e:
#        if DEBUG:
#            raise
#        indent = len(program_name) * " "
#        sys.stderr.write(program_name + ": " + str(e) + "\n")
#        log.error(program_name + ": " + str(e) + "\n")
#        sys.stderr.write(indent + "  for help use --help\n")
#        return 2
    sys.exit(exit_status)

    