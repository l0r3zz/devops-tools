#!/usr/bin/env python
# encoding: utf-8
'''
jiralab -- useful classes and methods to work with JIRA tickets
@author:     geowhite 
@copyright:  2013 StubHub. All rights reserved.   
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com

'''
import getpass
import aes 
import sys
import os
import pexpect
import pxssh
import logging
import mylog
import time
import threading


__all__ = []
__version__ = 0.86
__date__ = '2012-11-04'
__updated__ = '2013-05-04'

AES_BLOCKSIZE = 128
REGSERVER = "srwd00reg010.stubcorp.dev"

log = logging.getLogger('env-o-matic (%s)' % __name__)

# Specialized Exceptions
class JIRALAB_CLI_TypeError(TypeError): pass
class JIRALAB_CLI_ValueError(ValueError): pass
class JIRALAB_AUTH_ValueError(ValueError): pass

class Reg():
    """
    Class to handle release and build label translations
    """

    def __init__(self, reghandle):
        # FIX ME  just a quick hack, this should be done by a mapping function
        # so that we don't have to continuously track it
        jira_dict = {
                     "rb1306"     : "ecomm_13.6",
                     "ecomm_13.6" : "ecomm_13.6",
                     "rb_ecomm_13_6" : "ecomm_13.6",
                     "ecomm_13.6.1" : "ecomm_13.6.1",
                     "rb_ecomm_13_6_1" : "ecomm_13.6.1",
                     "ecomm_13.7" : "ecomm_13.7",
                     "rb_ecomm_13_7" : "ecomm_13.7",
                      }

        self.reghandle = reghandle
        if reghandle in jira_dict:
            self.jira_release = jira_dict[reghandle]
        else:
            raise JIRALAB_CLI_ValueError("No release named %s" % reghandle)

class Job(threading.Thread):
    '''
    Inherit this class to create parallelizable tasks, just add run() ;)
    '''
    def __init__(self, args, auth, log, **kwargs):
        '''
        Initialize the job, set up required values and log into a REG server
        Required Args:
            args    - args that eom was invoked with.
            auth    - the authentication/authorization context to
                      perform the job in.
            log     - logging object
        Optional Args:
            debug   - set to True to print out debugging
            session - if set, don't perform a login, but use this session
                      context to run the job.
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
        self.use_siebel = kwargs.get('use_siebel', None)
        self.stage_q = kwargs.get('queue', None)


        if not self.ses :
            # Login to the reg server
            log.info ("eom.login:(%s) Logging into %s  @ %s UTC" %
                      (self.name, REGSERVER,
                       time.asctime(time.gmtime(time.time()))))
            # Create a remote shell object
            self.ses = CliHelper(REGSERVER)
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


class Auth():
    """
    Gather user name and password information from either a dict
    (the dict from argparse works fine)
    """
    def __init__(self, args):

        self._salt = "c0ffee31337bea75"
        self.vault_file = ".jiralab_vault-%s"

        self.user = args.user
        self.password = args.password

    def getcred(self):
        # Let's make sure we have the username
        # If no username provided use the user that is running the process
        if (not self.user):
            user = raw_input("Username [%s]: " % getpass.getuser())
            if user == '':
                self.user = getpass.getuser()
            self.user = user

        # set up some paths to search for the vault file
        pass_vault_path = [
                          ("~%s/" % self.user) + (self.vault_file % self.user),
                            "./" + (self.vault_file % self.user),
                          ]

        # Execute this block if a password was not provided as an argument
        if (not self.password):
            # Iterate through a list of the paths, precedence set by position
            for p in pass_vault_path:
                path = os.path.expanduser(p)
                if os.path.isfile(path)and os.access(path, os.R_OK):
                    for line in open(path, 'r'):
                        self.password = aes.decrypt(line.rstrip('\n'),
                            self._salt,AES_BLOCKSIZE)
                    return  # username and password set
            # We looked everywhere for the password vault and could not find it,
            # so ask for password
            self.password = getpass.getpass()

        for p in pass_vault_path:
            path = os.path.expanduser(p)
            try:
                pwf = open(path, 'w')
            except IOError:
                continue
            pwf.write(aes.encrypt(self.password, self._salt, AES_BLOCKSIZE))
            pwf.close()
            return
        raise JIRALAB_AUTH_ValueError("Can't write vault file")


class CliHelper:
    '''Helper class to do  CLI login, command stream execution
    and file transfers '''

    def __init__(self, host, port=22, log, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.log = log
        self.session = pxssh.pxssh()

    def login(self, user="admin", password="admin", prompt="[#$]", timeout=30):
        self.user = user
        self.password = password
        self.timeout = timeout
        try:
            self.session.login(self.host, self.user, self.password,
                               terminal_type='ansi', original_prompt='[#$]',
                               login_timeout=10, port=self.port,
                               auto_prompt_reset=False)
            #self.session.prompt()

        except pxssh.ExceptionPxssh, e:
            self.login = False
            self.log.error(
                    "eom.cliloginfail: Login failure to %s user: %s, %s" % (self.host, self.user, e))
            return False

        self.session.PROMPT = prompt
        self.PROMPT = self.session.PROMPT
        self.before = self.session.before
        self.after = self.session.after
        return True

    def logout(self):
            self.session.logout()

    def _consume_prompt(self):
        # consume the prompt (this is done a lot)
        self.before = self.session.before
        self.after = self.session.after
        self.session.prompt(timeout=1)

    def set_prompt(self, prompt):
        rval = self.PROMPT
        self.PROMPT = self.session.PROMPT = prompt
        return rval

    def docmd(self, 
              cmd, match, notimeout=False, consumeprompt=True, timeout=30):
            search_list = match

            if not len(match):
                self.session.sendline(cmd)
                self._consume_prompt()
                return 1

            if not notimeout:
                search_list.insert(0, pexpect.TIMEOUT)

            self.session.sendline(cmd)
            rval = self.session.expect(search_list, timeout)
            self.before = self.session.before
            self.after = self.session.after
            if consumeprompt:
                self._consume_prompt()
            return rval

