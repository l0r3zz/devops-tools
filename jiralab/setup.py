#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
setup(
    name = "jiralab",
    version = "0.5.0",
    packages = find_packages(),
    py_modules = ['ez_setup','proproj','jcomment'],
    install_requires = ['jira_python'],

    # metadata for upload to PyPI
    author = "Geoff White",
    author_email = "gwhite@stubhub.com",
    description = "CLI level tools manipulate JIRA tickets",
    license = "Restricted",
    keywords = "jira proproj env ",
    entry_points = {
        'console_scripts': [
            'proproj = proproj:main',
            'jcomment = jcomment:main',
            ]
    }
)