#!/usr/local/bin/python2.7
# encoding: utf-8
'''
jiralab -- useful classes and methods to work with JIRA tickets
@author:     geowhite 
@copyright:  2012 StubHub. All rights reserved.   
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com

'''
import getpass
import aes
import sys
import os
import pexpect
import pxssh


__all__ = []
__version__ = 0.6
__date__ = '2012-11-04'
__updated__ = '2013-01-30'

AES_BLOCKSIZE = 128

# Specialized Exceptions
class JIRALAB_CLI_TypeError(TypeError): pass
class JIRALAB_CLI_ValueError(ValueError): pass
class JIRALAB_AUTH_ValueError(ValueError): pass


class Auth():
    """
    Gather user name and password information from either a dict (the dict from argparse works fine)
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
            for path in pass_vault_path:
                if os.path.isfile(path)and os.access(path, os.R_OK):
                    for line in open(path, 'r'):
                        self.password = aes.decrypt(line.rstrip('\n'),
                            self._salt,AES_BLOCKSIZE)
                    return  # username and password set
            # We looked everywhere for the password vault and could not find it, so ask for password
            self.password = getpass.getpass()

        for path in pass_vault_path:
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

    def __init__(self, host, port=22, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
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
            raise(e)

        self.session.PROMPT = prompt
        self.PROMPT = self.session.PROMPT
        self.before = self.session.before
        self.after = self.session.after
        self.login = True

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

    def docmd(self, cmd, match, notimeout=False, consumeprompt=True, timeout=30):
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
