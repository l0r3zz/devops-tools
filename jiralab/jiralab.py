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


__all__ = []
__version__ = 0.1
__date__ = '2012-11-04'
__updated__ = '2012-11-07'

class auth():
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
            
        
        