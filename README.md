devops-tools
============

This repository contains the sum total of two years of work on what has
become known as the eom framework. The framework is currently configured
to execute python code form a single flat directory that should be placed
in the PATH of the user's .bashrc i.e. all of the eom directory is currently
Installed at /nas/reg/bin/jiralab/
This is also true for the envaudit command.

```
Here is a break-down of what is in the current repository tree:

`-- devops-tools                            # Top level directory
    |-- DevOpsPerls                         # Random Perl code (abandoned)
    |   |-- provisioning
    |   |   `-- provision.pl
    |   `-- update-token-table
    |       `-- update-token-table.pl
    |-- eom                                 # Top level eom directory
    |   |-- README.md                       # README specific to eom command
    |   |-- __init__.py
    |   |-- aes.py                          # AES library for password hash
    |   |-- dbgen.py                        # interface to delphix/siebel scripts
    |   |-- eom.py                          # eom top level command implementation
    |   |-- ez_setup.py                     # python ezinstall script
    |   |-- jassign.py                      # cmd to assign a ticket(not used)
    |   |-- jclose.py                       # cmd to close tickets
    |   |-- jcomment.py                     # cmd to comment a ticket
    |   |-- jcontent.py                     # wrapper around REGs content tool (deprecated)
    |   |-- jenvp.py                        # cmd to determine env status (used for lockout)
    |   |-- jiralab.py                      # jiralab library, (auth, ticket manipulation)
    |   |-- jpass.py                        # cmd to set jiralab vault password (maybe broken)
    |   |-- mylog.py                        # jiralab logging module
    |   |-- pexpect.py                      # remote login (old version) http://pexpect.readthedocs.org/en/latest/
    |   |-- proproj.py                      # cmd to create proproj and DB tickets, (used by eom)
    |   |-- pxssh.py                        # part of pexpect module
    |   `-- setup.py                        # ezinstall
    ├── sshdquery
        `── sshdquery.py                    # process sshd logfiles with concurrency
    |
    `-- vigilante                           # top level directory for auditor project
        |-- clitools                        # CLI client
        |   `-- envaudit.py                 # env-audit command (client)
        |-- puppet                          # puppet modules to support vigilante
        |   `-- modules
        |       `-- stubhub-vigilante       # module to gather facts from envs, write to NAS
        |           |-- Modulefile
        |           |-- README
        |           |-- files
        |           |   |-- bin
        |           |   |   |-- phaktor.py
        |           |   |   `-- yaml
        |           |   |       |-- __init__.py
        |           |   |       |-- composer.py
        |           |   |       |-- constructor.py
        |           |   |       |-- dumper.py
        |           |   |       |-- emitter.py
        |           |   |       |-- error.py
        |           |   |       |-- events.py
        |           |   |       |-- loader.py
        |           |   |       |-- nodes.py
        |           |   |       |-- parser.py
        |           |   |       |-- reader.py
        |           |   |       |-- representer.py
        |           |   |       |-- resolver.py
        |           |   |       |-- scanner.py
        |           |   |       |-- serializer.py
        |           |   |       `-- tokens.py
        |           |   `-- etc
        |           |       |-- facts.ftr
        |           |       `-- generic.yaml
        |           |-- manifests
        |           |   `-- init.pp
        |           |-- spec
        |           |   `-- empty
        |           `-- tests
        |               |-- empty
        |               `-- init.pp
        |-- pypuppetdb                      # a puppetdb API library (not used)
        |   |-- __init__.py
        |   |-- api
        |   |   |-- __init__.py
        |   |   |-- v2.py
        |   |   `-- v3.py
        |   |-- errors.py
        |   |-- package.py
        |   |-- types.py
        |   `-- utils.py
        |-- templates                       # templates for vigilante
        |   |-- facts.yaml
        |   `-- generic.yaml
        |-- vigilapi                        # Djaqngo vigilante API implementation
        |   |-- api
        |   |   |-- __init__.py
        |   |   |-- admin.py
        |   |   |-- models.py
        |   |   |-- tests.py
        |   |   |-- views.py
        |   |-- manage.py
        |   |-- nohup.out
        |   `-- vigilapi
        |       |-- __init__.py
        |       |-- settings.py
        |       |-- urls.py
        |       |-- wsgi.py
        `-- vigillib                        # vigilante API library top level
            |-- api.py                      # vigilante client API
            |-- dbapi.py                    # backend DB API


The repository DOES NOT contain the jira-python library which access the
REST API of JIRA, the version that eom currently uses can be found at:
 
/nas/reg/local/lib/python2.7/site-packages/jira_python-0.13-py2.7.egg/

The library has progressed since I forked it, the most current version 
can be found at https://bitbucket.org/bspeakmon/jira-python

```
