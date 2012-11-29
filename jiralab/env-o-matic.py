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
import jiralab
import json

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.41
__date__ = '2012-11-20'
__updated__ = '2012-11-28'

DEBUG = 1
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
        parser.add_argument("-q", "--envreq", dest="envreq", help="environment request issue ID (example: ENV_707" )
        parser.add_argument("-r", "--release", dest="release", help="release ID (example: rb1218" )
        parser.add_argument('-v', '--version', action='version', version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug", action='store_true',help="turn on DEBUG switch")
        
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
        if not args.envreq:
            print("ERROR: No environment request ticket")
            exit_status = 1
        if exit_status:
            print("\n")
            parser.print_help()
            exit(exit_status)

             
        if args.debug:
            DEBUG = True
            
        envid = args.env.upper()
        envid_lower = args.env.lower()
        envnum = envid[-2:] #just the number
          
        authtoken = jiralab.Auth(args)


        # Login to the reg server
        print ("Logging into %s" % REGSERVER)
        reg_session = jiralab.CliHelper(REGSERVER)
        rval = reg_session.login(authtoken.user,authtoken.password,prompt="\$[ ]")
        if DEBUG:
            print ("before: %s\nafter: %s" % (reg_session.before, reg_session.after)) 

        

        print ("Becoming relmgt")
        rval = reg_session.docmd("sudo -i -u relmgt",[reg_session.session.PROMPT])
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))

        # Create a PROPROJ and DB ticket for the ENV
        print ("Creating JIRA issues")
        # 
        rval = reg_session.docmd("proproj -u %s -e %s -r %s" % (args.user, args.env, args.release),["\{*\}", reg_session.session.PROMPT])
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
        if rval == 1 :
            PPRESULT = 1
            proproj_result_string = (reg_session.before + reg_session.after).split("\n")
            proproj_result_dict = json.loads(proproj_result_string[PPRESULT])
            print("Ticket Creation Structure:: %s \n" % proproj_result_string)
        else:
            print("Error in ticket creation: %s%s \nExiting.\n" %(reg_session.before, reg_session.after))
            exit(2)
        
        # Start re-imaging     
        print("Reimaging %s, this may take over 1 Hour!..." % envid)
        reimage_cmd = 'time provision -e %s reimage -v 2>&1 |jcmnt -f -u %s -i %s -t "Re-Imaging Environment for code deploy"' % \
            ( envid_lower, args.user, proproj_result_dict["proproj"])
        rval = reg_session.docmd(reimage_cmd,[reg_session.session.PROMPT],timeout=4800)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
            

        print("Building Database, this may take up to 40 minutes...")
        dbgen_build_cmd = 'time dbgen -u %s -e %s -r %s |jcmnt -f -u %s -i %s -t "Automatic DB Generation"' % \
            (args.user, envid, args.release, args.user, proproj_result_dict["dbtask"])
        rval = reg_session.docmd(dbgen_build_cmd,[reg_session.session.PROMPT],timeout=2400)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
            
        print("Performing Automatic Validation of %s \n" % envid)
        env_validate_string = 'env-validate -e %s 2>&1 | jcmnt -f -u %s -i %s -t "Automatic env-validation"' % \
            (envnum, args.user, proproj_result_dict["proproj"])
        rval = reg_session.docmd(env_validate_string,[reg_session.session.PROMPT],timeout=1000)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval, reg_session.before, reg_session.after))
         
        print("Execution Complete. Exiting.\n")
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