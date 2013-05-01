#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
setup(
    name = "jiralab",
    version = "1.1.0",
    packages = find_packages(),
    py_modules = ['ez_setup','proproj','jcomment','env-o-matic','dbgen','jclose'],
    install_requires = ['jira_python>=0.13', 'PyYAML'],

    # metadata for upload to PyPI
    author = "Geoff White",
    author_email = "gwhite@ebay.com",
    description = "Continuous Delivery Tools that talk to jira",
    license = "Restricted",
    keywords = "jira proproj env-o-matic ",
    entry_points = {
        'console_scripts': [
            'proproj = proproj:main',
            'jcomment = jcomment:main',
            'jclose = jclose:main',
            'jcontent = jcontent:main',
            'env-o-matic = env-o-matic:main',
            'dbgen = dbgen:mail',
            ]
    }
)