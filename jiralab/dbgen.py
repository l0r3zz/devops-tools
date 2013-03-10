#!/usr/bin/python
# encoding: utf-8
'''
dbgen -- Create Delphix based Databases
@author:     geowhite
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import re
import jiralab

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.96
__date__ = '2012-11-15'
__updated__ = '2013-03-08'

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
    REGSERVER = "srwd00reg010.stubcorp.dev"
    GLOBAL_TNSNAMES = "/nas/home/oracle/DevOps/global_tnsnames/tnsnames.ora"
    QA_TNSNAMES = "/nas/home/oracle/OraHome/network/admin/tnsnames.tst"
    
    delphix_prefix_dict = {
                           "srwd00dbs008" : "$<delphix_db_prefix>",
                           "srwd00dbs016" : "$<delphix_db_prefix_16",
                           "srwd00dbs019" : "$<delphix_db_prefix_19",
                           }
    delphix_host_dict = {
                            "srwd00dbs008" : "$<delphix_host01>",
                            "srwd00dbs016" : "$<delphix_host02>",
                            "srwd00dbs019" : "$<delphix_host03>",
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
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]

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

        if args.debug:
            DEBUG = True

        envid = args.env.upper()
        envnum = envid[-2:]  # just the number

        auth = jiralab.Auth(args)
        auth.getcred()

        # Login to the reg server
        print("Logging into %s" % REGSERVER)
        reg_session = jiralab.CliHelper(REGSERVER)
        reg_session.login(auth.user, auth.password, prompt="\$[ ]")
        if DEBUG:
            print("before: %s\nafter: %s" % (reg_session.before,
                        reg_session.after))

        print ("Becoming relmgt")
        rval = reg_session.docmd("sudo -i -u relmgt", [reg_session.session.PROMPT])
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        #login to the db server
        print("Logging into DB Server : srwd00dbs008")
        rval = reg_session.docmd("ssh srwd00dbs008.stubcorp.dev",
                        ["yes", reg_session.session.PROMPT],
                        timeout=60)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        if rval == 1:  # need to add ssh key
            rval = reg_session.docmd("yes",
                        [reg_session.session.PROMPT], consumeprompt=False)
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            if rval != 1:  # something else printed
                print("Could not log into srwd00dbs008. Exiting")
                exit(2)
        elif rval == 2:  # go right in
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        else:  # BAD
            if DEBUG:
                print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
            print("Something bad happened, exiting")
            exit(2)

        # become the oracle user
        print("Becoming oracle user")
        rval = reg_session.docmd("sudo su - oracle", ["oracle>"],
                        consumeprompt=False)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))

        print("Running the auto-provision script")
        

        use_siebel = ("Y" if args.withsiebel else "")  
  
        auto_provision_cmd = "/nas/reg/bin/delphix-auto-provision %s %s Ecomm %s"\
            % (envnum, args.release,use_siebel)
        rval = reg_session.docmd(auto_provision_cmd,
                        ["ALL DONE!!!", "Error"], timeout=4000)
        if DEBUG:
            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                        reg_session.before, reg_session.after))
        if rval != 1:
            print ("Error occurred: %s%s\n" % (reg_session.before,
                        reg_session.after))
            exit(2)
        else:
            print("%s%s\nSuccess.\n" % (reg_session.before,
                        reg_session.after))
            sn_search_space = re.search(
                                'DBNAME\:[ ]+(?P<sn>D(08|19|16)DE[0-9]{2})'
                                        , reg_session.before)
            if sn_search_space:  # make sure we found something
                service_name = sn_search_space.group("sn")
                print("\nDBNAME: %s" % service_name)
                if args.postpatch:
                    dbpatch_cmd = "%s %s" % (args.postpatch, service_name)

                    # apply autopatchs if present.
                    print("Dropping back to relmgt")
                    rval = reg_session.docmd("exit",
                            [reg_session.session.PROMPT])
                    if DEBUG:
                        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))
                    print("Dropping back to %s" % REGSERVER)
                    rval = reg_session.docmd("exit",
                                    [reg_session.session.PROMPT])
                    if DEBUG:
                        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))

                    print("Running DB post patching scripts")
                    rval = reg_session.docmd(dbpatch_cmd,
                                    [reg_session.session.PROMPT], timeout=600)
                    print("%s%s\n" % (reg_session.before, reg_session.after))
                    if DEBUG:
                        print ("Rval= %d; before: %s\nafter: %s" % (rval,
                                    reg_session.before, reg_session.after))
                    print("Patching complete")
                    
                '''
                1) Search the global_tnsnames.ora file for service_name, if not found then ERROR
                2) Save the single line Service Name definition.
                3) Open /nas/home/oracle/OraHome/network/admin/tnsnames.ora
                4) Search for service name, if found then exit, if not, append to file.
                5) No need to delete the old service name, it might come in handy if the db is moved at a future date
                6) Extract the HOST name from the definition, will need it to map to delphix_prefix and delphix_host variables for tokentable rewrite. 
                '''
                for line in open(GLOBAL_TNSNAMES,'r'):
                    dbtnsdef = None
                    tns_ss = re.search('^%s.+HOST=(?P<hn>.+)\.stubcorp\.dev' % service_name, line)
                    if tns_ss:
                        dbtnsdef = line
                        dbhost = tns_ss.group("hn")
                        break 
                if not dbtnsdef :
                    print( "error: could not find service name in the global tnsnames file!")
                    print("Exiting with errors")
                    exit(2)
                else:
                    tnsorafile = open(QA_TNSNAMES,"r+")
                    for line in tnsorafile:
                        if service_name.upper() in line.upper():
                            print("%s is already in %s, nothing to do" % (service_name, QA_TNSNAMES))
                            break;
                    else:
                        tnsorafile.write(dbtnsdef)
                        print( "Adding : %s to %s" % (dbtnsdef, QA_TNSNAMES))
                    tnsorafile.close()
                    
                    tt_update_cmds = [
                                      "update-token-table -e %s -s '%s' -r '%s' -t token-table-env-based -v" % (envid.lower(), delphix_prefix_dict[dbhost], delphix_host_dict[dbhost]),
                                      "update-token-table -e %s -s '%s' -r '%s' -t token-table-env-based -v" % (envid.lower(), delphix_prefix_dict[dbhost], delphix_host_dict[dbhost]),
                                      "update-token-table -e %s -s '%s' -r '%s' -t token-table-env-stubhub-properties -v" % (envid.lower(), delphix_prefix_dict[dbhost], delphix_host_dict[dbhost]),
                                      "update-token-table -e %s -s '%s' -r '%s' -t token-table-env-stubhub-properties -v" % (envid.lower(), delphix_prefix_dict[dbhost], delphix_host_dict[dbhost]),
                                      ]
                    print("Updating the token tables with new values")
                    for cmd in tt_update_cmds:
                        rval = reg_session.docmd(cmd,
                                        [reg_session.session.PROMPT], timeout=300)
                        print("%s%s\n" % (reg_session.before, reg_session.after))
                        if DEBUG:
                            print ("Rval= %d; before: %s\nafter: %s" % (rval,
                                        reg_session.before, reg_session.after))                                                        
                
            print("Exiting.")
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
