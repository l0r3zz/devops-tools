#!/usr/bin/env python
# encoding: utf-8
'''
dbgen -- Create Delphix and Siebel  based Databases
@author:     geowhite
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import re
import jiralab
import mylog
import logging

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 1.14
__date__ = '2012-11-15'
__updated__ = '2013-10-23'

def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''
    DEBUG = 0
    REGSERVER = "srwd00reg010.stubcorp.dev"
    GLOBAL_TNSNAMES = "/nas/home/oracle/DevOps/global_tnsnames/tnsnames.ora"
    QA_TNSNAMES = "/nas/home/oracle/OraHome/network/admin/tnsnames.ora"
    TT_ENV_BASED_RO = "/nas/reg/etc//dev/properties/tokenization/token-table-env-based"
    AUTOPROV_TO = 4000
    CMD_TO = 120
    
    env_de_prefix_dict = {
                           "srwd00dbs008" : "$<delphix_db_prefix>",
                           "srwd00dbs012" : "$<delphix_db_prefix_12>",
                           "srwd00dbs016" : "$<delphix_db_prefix_16>",
                           "srwd00dbs019" : "$<delphix_db_prefix_19>",
                           }
    
    env_dq_prefix_dict = {
                           "srwd00dbs008" : "$<delphix_dbq_prefix>",
                           "srwd00dbs012" : "$<delphix_dbq_prefix_12>",
                           "srwd00dbs016" : "$<delphix_dbq_prefix_16>",
                           "srwd00dbs019" : "$<delphix_dbq_prefix_19>",
                           }

    delphix_host_dict = {
                            "srwd00dbs008" : "$<delphix_host01>",
                            "srwd00dbs016" : "$<delphix_host02>",
                            "srwd00dbs019" : "$<delphix_host03>",
                            "srwd00dbs012" : "$<delphix_host04>",
                         }
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version,
                                                     program_build_date)
    program_shortdesc ="dbgen -- Create Delphix and Siebel based Databases"

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
        parser.add_argument("--postpatch", dest="postpatch", default=None,
                        help="path to post db create patch script")
        parser.add_argument("--withsiebel", dest="withsiebel", action='store_true',
                         default=False, 
                         help="set to build a Siebel database along with Delphix")
        parser.add_argument("--timeout", dest="timeout",
                        default=AUTOPROV_TO, type=int,
                        help="number of sec to wait for db"
                        "creation to complete. default(%d)" % AUTOPROV_TO)
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

    
        log = log = mylog.logg('dbgen', llevel='INFO',
                gmt=True, cnsl=True, sh=sys.stdout)
        #set the formatter so that it adds the envid
        lfstr = ('%(asctime)s %(levelname)s: %(name)s:'
                 '[%(process)d] {0}:: %(message)s'.format(args.env))
        formatter = logging.Formatter(lfstr,
            datefmt='%Y-%m-%d %H:%M:%S +0000')
        for h in log.handlers:
            h.setFormatter(formatter)
    
        if args.debug:
            DEBUG = True
            log.setLevel("DEBUG")

        envid = args.env.upper()
        if not re.search("SRW[DQE][0-9]{2}",envid):
            print("Error:Please check your supplied environment id")
            exit(2)            
        envnum = envid[-2:]  # just the number
        if not envnum.isdigit():
            print("Error:Please check your supplied environment id")
            exit(2)
        envbank = envid[3].upper() # get the letter indicating the QA/Dev bank
        if envbank == 'E':
            print( "Sorry, dbgen does not yet support PE environments")
            exit(2)

        auth = jiralab.Auth(args)
        auth.getcred()

        # Login to the reg server
        log.info("Logging into %s" % REGSERVER)
        reg_session = jiralab.CliHelper(REGSERVER)
        reg_session.login(auth.user, auth.password, prompt="\$[ ]",
                          timeout=CMD_TO)
        if DEBUG:
            log.debug("before: %s\nafter: %s" % (reg_session.before,
                        reg_session.after))

        log.info ("Becoming relmgt")
        rval = reg_session.docmd("sudo -i -u relmgt", [reg_session.session.PROMPT],
                                 timeout=CMD_TO)
        if DEBUG:
            log.debug ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        #login to the db server
        log.info("Logging into DB Server : srwd00dbs008")
        rval = reg_session.docmd("ssh srwd00dbs008.stubcorp.dev",
                        ["yes", reg_session.session.PROMPT],
                        timeout=CMD_TO)
        if DEBUG:
            log.debug ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        if rval == 1:  # need to add ssh key
            rval = reg_session.docmd("yes",
                        [reg_session.session.PROMPT], consumeprompt=False)
            if DEBUG:
                log.debug ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            if rval != 1:  # something else printed
                log.error("Could not log into srwd00dbs008. Exiting")
                exit(2)
        elif rval == 2:  # go right in
            if DEBUG:
                log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        else:  # BAD
            if DEBUG:
                log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            log.error("Something bad happened, exiting")
            exit(2)

        # become the oracle user
        log.info("Becoming oracle user")
        rval = reg_session.docmd("sudo su - oracle", ["oracle>"],
                        consumeprompt=False)
        if DEBUG:
            log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        log.info("Running the auto-provision script")
        use_siebel = ("Y" if args.withsiebel else "")

        auto_provision_cmd = ("/nas/reg/bin/delphix-auto-provision.3.2 %s %s Ecomm %s %s"
            % (envnum, args.release, envbank,  use_siebel))
        log.info("cmd:%s" % auto_provision_cmd)
        rval = reg_session.docmd(auto_provision_cmd,
                        ["ALL DONE!!!", "Error"], timeout=args.timeout)
        if DEBUG:
            log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        if rval != 1:
            log.error("Error occurred: %s%s\n" % (reg_session.before,
                        reg_session.after))
            exit(2)

        else:
            log.info("%s%s\nSuccess.\n" % (reg_session.before,
                        reg_session.after))

            old_db_search_space = re.search(
                                'Found Database[ ]+(?P<odb>D(08|19|16)[DQ]E[0-9]{2})'
                                        , reg_session.before)
            sn_search_space = re.search(
                                'DBNAME\:[ ]+(?P<sn>D(08|19|16)[DQ]E[0-9]{2})',
                                        reg_session.before)

            if sn_search_space:  # make sure we found something
                service_name = sn_search_space.group("sn")
                log.info("\nDBNAME: %s" % service_name)

                log.info("Dropping back to relmgt")
                rval = reg_session.docmd("exit",
                        [reg_session.session.PROMPT])
                if DEBUG:
                    log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                                reg_session.before, reg_session.after))
                log.info("Dropping back to %s" % REGSERVER)
                rval = reg_session.docmd("exit",
                                [reg_session.session.PROMPT])
                if DEBUG:
                    log.debug ("Rval= %d; before: %s\nafter: %s" % (rval,
                                reg_session.before, reg_session.after))

                '''
                1) Search the global_tnsnames.ora file for service_name, if not found then ERROR
                2) Save the single line Service Name definition.
                3) Open /nas/home/oracle/OraHome/network/admin/tnsnames.ora
                4) Search for service name, if found then exit, if not, append to file.
                5) No need to delete the old service name, it might come in handy if the db is moved at a future date
                6) Extract the HOST name from the definition, will need it to map to delphix_prefix and delphix_host variables for tokentable rewrite. 
                '''
                for line in open(GLOBAL_TNSNAMES, 'r'):
                    dbtnsdef = None
                    tns_ss = re.search('^%s.+HOST=(?P<hn>.+)\.stubcorp\.dev' % service_name, line)
                    if tns_ss:
                        dbtnsdef = line
                        dbhost = tns_ss.group("hn")
                        break
                if not dbtnsdef:
                    log.error( "error: could not find service name in the global tnsnames file!")
                    log.error("Exiting with errors")
                    exit(2)

                tnsorafile = open(QA_TNSNAMES, "r")
                for line in tnsorafile:
                    if service_name.upper() in line.upper():
                        log.info("%s is already in %s, nothing to do" % (service_name, QA_TNSNAMES))
                        tnsorafile.close()
                        break
                else:
                    log.info("Adding : %s to %s" % (dbtnsdef, QA_TNSNAMES))
                    tnsupdate_cmd = ("echo '%s' | sudo tee -a %s" %
                        (dbtnsdef, QA_TNSNAMES))
                    rval = reg_session.docmd(tnsupdate_cmd,
                                    [reg_session.session.PROMPT], timeout=30)
                    if DEBUG:
                        log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))

                # extract the environment stanza from the env_based token table file.
                tt_env_based = open(TT_ENV_BASED_RO, "r").read()
                stanza_start = "<%s>" % envid.lower()
                stanza_end = "</%s>" % envid.lower()
                sstart_index = tt_env_based.index(stanza_start) + len(stanza_start)
                send_index = tt_env_based.index(stanza_end, sstart_index)
                tt_stanza = tt_env_based[sstart_index:send_index]
                # get the existing db values set for this stanza
                old_db_sspace = re.search('db_service_name[ ]+=[ ]+(?P<s1>\$<.+>)(?P<e1>[0-9]{2})',tt_stanza)
                old_tt_prefix = old_db_sspace.group('s1')
                old_tt_envnum = old_db_sspace.group('e1')
                old_tt_host = re.search('db_server_01[ ]+=[ ]+(?P<s2>\$<.+>)', tt_stanza).group('s2')

                # create a bunch of update commands to update the token table
                # but first guard them from null values
                if old_tt_prefix and old_tt_host and dbhost and old_tt_envnum:
                    
                    old_tt_db_string = old_tt_prefix + old_tt_envnum    
                    old_tt_host_string = old_tt_host

                    # We need to use a different tt variable for the srwq environments
                    if envbank == "Q":
                        sn_prefix = env_dq_prefix_dict[dbhost]
                    else:
                        sn_prefix = env_de_prefix_dict[dbhost]
        
                    new_tt_db_string = sn_prefix + envnum
                    new_tt_host_string = delphix_host_dict[dbhost]
                        
                    tt_update_cmds = [
                                      "eom-update-token-table -e %s --release-id %s -s '%s' -r '%s' -v" % (envid.lower(), args.release, old_tt_db_string, new_tt_db_string),
                                      "eom-update-token-table -e %s --release-id %s -s '%s' -r '%s' -v" % (envid.lower(), args.release, old_tt_host_string, new_tt_host_string),
                                      ]
                    log.info("Updating the token tables with new values")
                    for cmd in tt_update_cmds:
                        log.info("Applying Command: %s" % cmd)
                        rval = reg_session.docmd(cmd,
                                        [reg_session.session.PROMPT], timeout=300)
                        if DEBUG:
                            log.debug("Rval= %d; before: %s\nafter: %s" % (rval,
                                        reg_session.before, reg_session.after))
                else:
                    log.warn( "Tokenization operation failed. Old Prefix: %s ,Old Host: %s, dbhost: %s" %
                           (old_tt_prefix, old_tt_host, dbhost))
                    
                if args.postpatch:
                    # apply autopatchs if present
                    dbpatch_cmd = "%s %s" % (args.postpatch, service_name)
                    log.info("Running DB post patching scripts")
                    rval = reg_session.docmd(dbpatch_cmd,
                                    [reg_session.session.PROMPT], timeout=600)
                    log.info("%s%s\n" % (reg_session.before, reg_session.after))
                    if DEBUG:
                        log.debug ("Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))
                    log.debug("Patching complete")

            print("Exiting.")
            exit(0)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0

    except Exception, e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2


if __name__ == "__main__":
    main()

