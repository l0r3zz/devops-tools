#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
setup(
    name = "eom",
    version = "1.1.0",
    packages = find_packages(),
    py_modules = ['ez_setup','proproj','jcomment','eom','dbgen','jclose',
                  'aes','jiralab','eom_init','mylog','pexpect','pxssh',
                  'jcontent'],
    install_requires = ['jira_python>=0.13', 'PyYAML'],

    # metadata for upload to PyPI
    author = "Geoff White",
    author_email = "gwhite@ebay.com",
    description = "EOM: Continuous Delivery Tools that talk to Jira",
    license = "Restricted",
    keywords = "jira eom devops env-o-matic ",
    entry_points = {
        'console_scripts': [
            'proproj = proproj:main',
            'jcomment = jcomment:main',
            'jclose = jclose:main',
            'jcontent = jcontent:main',
            'env-o-matic = eom:main',
            'eom = eom:main',
            'dbgen = dbgen:mail',
            ]
    }
)