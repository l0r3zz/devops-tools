#!/usr/local/bin/python2.7
# encoding: utf-8
'''
env-o-matic - Basic automation to buildout a virtual environment given an ENVIRONMENT ID
              and ENV request ticket
@author:     geowhite 
@copyright:  2012 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com    
'''

import sys
import os
from jira.client import JIRA
import jiralab
import json
import time
import mylog

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.8
__date__ = '2012-11-20'
__updated__ = '2013-01-06'

TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def main(argv=None): # IGNORE:C0111
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
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-u", "--user", dest="user", default=None,help="user to access JIRA")
        parser.add_argument("-p", "--password", dest="password", default=None,help="password to access JIRA")
        parser.add_argument("-e", "--env", dest="env", help="environment name to provision (example: srwd03" )
        parser.add_argument("-q", "--envreq", dest="envreq", default=None, help="environment request issue ID (example: ENV_707" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument("-l", "--logfile", dest="logfile", default=None,  help="file to log to (if none, log to console" )
        parser.add_argument('-v', '--version', action='version', version=program_version_message)
        parser.add_argument('--skipreimage', action='store_true', dest="skip_reimage", default=False, help="set to skip the re-image operation")
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
        if args.logfile: 
            log = mylog.logg('env-o-matic', llevel='INFO', gmt=True,
                              lfile=args.logfile, cnsl=True)
        else:
            log = mylog.logg('env-o-matic', llevel='INFO', gmt=True,
                              cnsl=True, sh=sys.stdout)            
        log.info('eom.start: %s' % args)

             
        if args.debug:
            DEBUG = True
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
        if args.release[-2:] == "_1":
            jira_release = args.release[:-2] + "_bugfix"
        else:
            jira_release = args.release

        proproj_cmd =  "proproj -u %s -e %s -r %s " % (auth.user, args.env, jira_release)
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
        
        # If there is an ENV ticket, link the proproj to it.
        if args.envreq:
            log.info("eom.tlink: Linking propoj:%s to ENV request:%s" % (proproj_result_dict["proproj"], args.envreq))
            jira_options = { 'server': 'https://jira.stubcorp.dev/' }
            jira = JIRA(jira_options,basic_auth= (auth.user,auth.password))
            link = jira.create_issue_link(type="Dependency", inwardIssue=args.envreq,
                                      outwardIssue=proproj_result_dict["proproj"])

        if args.skip_reimage:
            log.info("eom.noreimg: Skipping the re-image of %s" % envid)
        else:        
            # Start re-imaging     
            log.info("eom.reimg.start: Reimaging %s start @ %s UTC, ..." % (envid,
                            time.asctime(time.gmtime(time.time()))))
            reimage_cmd = 'time provision -e %s reimage -v 2>&1 |jcmnt -f -u %s -i %s -t "Re-Imaging Environment for code deploy"' % \
                ( envid_lower, auth.user, proproj_result_dict["proproj"])
            rval = reg_session.docmd(reimage_cmd,[reg_session.session.PROMPT],timeout=4800)
            if DEBUG:
                log.debug ("eom.deb: Rval= %d; \nbefore: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
            log.info("eom.reimg.done: Reimaging done @ %s UTC" % time.asctime(time.gmtime(time.time())))
            

        log.info("eom.dbcreate.start: Building Database start @ %s UTC," % time.asctime(time.gmtime(time.time())))
        # If -DD turn on debugging for dbgen
        if args.debug > 1:
            dbgen_build_cmd = 'time dbgen -u %s -e %s -r %s -D |jcmnt -f -u %s -i %s -t "Automatic DB Generation"' % \
                (args.user, envid, args.release, auth.user, proproj_result_dict["dbtask"])
        else:
            dbgen_build_cmd = 'time dbgen -u %s -e %s -r %s  |jcmnt -f -u %s -i %s -t "Automatic DB Generation"' % \
                (auth.user, envid, args.release, auth.user, proproj_result_dict["dbtask"])
        rval = reg_session.docmd(dbgen_build_cmd,[reg_session.session.PROMPT],timeout=3600)
        if DEBUG:
            log.debug ("eom.deb: Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
        log.info("eom.dbcreate.done: Database DONE @ %s UTC," % time.asctime(time.gmtime(time.time())))

        log.info("eom.sleep5: Sleeping 5 minutes")
        time.sleep(300)

        log.info("eom.envval: Performing Automatic Validation of %s" % envid)
        env_validate_string = 'env-validate -e %s 2>&1 | jcmnt -f -u %s -i %s -t "Automatic env-validation"' % \
            (envnum, auth.user, proproj_result_dict["proproj"])
        rval = reg_session.docmd(env_validate_string,[reg_session.session.PROMPT],timeout=1800)
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

