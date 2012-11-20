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
import pexpect
import pxssh


__all__ = []
__version__ = 0.2
__date__ = '2012-11-04'
__updated__ = '2012-11-14'

# Specialized Exceptions
class JIRALAB_CLI_TypeError(TypeError): pass
class JIRALAB_CLI_ValueError(ValueError): pass

class Auth():
    """
    Gather user name and password information from either a dict (the dict from argparse workd fine)
    """
    def __init__(self,args):
        AES_BLOCKSIZE = 128
        self._salt = "c0ffee31337bea75"
        vault_file = "./.jiralab_vault-%s"
        
        if (not args.password):
            if args.user :
                self.pass_vault = vault_file % args.user
            else:
                args.user = getpass.getuser()
                self.pass_vault = vault_file % args.user
            try:
                for line in open(self.pass_vault,'r'):
                    args.password = aes.decrypt(line.rstrip('\n'),self._salt,AES_BLOCKSIZE)
            except IOError :
                args.password = None

        if (not args.user):
            user = raw_input("Username [%s]: " % getpass.getuser())
            if not user:
                args.user = getpass.getuser()
            args.user = user
        if (not args.password):
            args.password = getpass.getpass()
            
        self.pass_vault = vault_file % args.user  
        pwf = open(self.pass_vault,'w')
        pwf.write(aes.encrypt(args.password,self._salt,AES_BLOCKSIZE))
        pwf.close()
        self.user = args.user
        self.password = args.password
        return
            
class CliHelper:
    '''Helper class to do  CLI login, command stream execution
    and file transfers '''

    def __init__(self, host, port=22, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.session = pxssh.pxssh()
  

    def login(self, user="admin", password="admin", prompt="$ ",timeout=30):
        self.user = user
        self.password = password
        self.timeout = timeout
        try:
            self.session.login(self.host, self.user, self.password,
                               terminal_type='ansi', original_prompt='[#$]',
                               login_timeout=10, port=self.port,
                               auto_prompt_reset=True)
            
        except pxssh.ExceptionPxssh, e:
            self.login = False
            raise(e)

        self.session.PROMPT = prompt
        self.PROMPT = self.session.PROMPT
        self.before = None
        self.after = None
        self.login = True

    def logout(self):
            self.session.logout()
    
    def _consume_prompt(self):
        # consume the prompt (this is done a lot)
        return self.session.expect([pexpect.TIMEOUT, self.session.PROMPT], self.timeout)

    def set_prompt(self,prompt):
        rval = self.PROMPT
        self.PROMPT = self.session.PROMPT = prompt
        return rval
    
    def docmd(self, cmd, match,notimeout=False,consumeprompt=True,timeout=30):
            search_list = match

            if not len(match):
                self.session.sendline(cmd)
                return self._consume_prompt()
            
            if not notimeout:
                search_list.insert(0,pexpect.TIMEOUT)
                
            self.session.sendline(cmd)
            rval = self.session.expect(search_list, timeout)
            self.before = self.session.before
            self.after = self.session.after
            if consumeprompt:
                self._consume_prompt()
            return rval 
