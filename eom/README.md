EOM (env-o-matic)
=================
**EOM (env-o-matic)** Is a set of CLI initiated programs which quantify, document and subsequently automate the process of building and delivering virtualized and hybrid (physical/virtual) Environments for use by Development and QA Teams.
Originally the process was a manual one, **eom** automates what was learned by performing the manual process over a few months. **EOM** is a direct application of the 4 phases outlined in the seminal work *The Visible Ops Handbook* by Kevin Behr, Gene Kim and George Spafford.
**Env-o-matic**, a pun on the *veg-o-matic* early food processor of the 60s.  *("It slices!  It dices!")*

Installation
-----------------
This code requires Python 2.7 or greater but is *not* compatible with Python3+ interpreters. It will fetch:

* PyYAML         - Python YAML support to read the *.eom_init* file
* jira-python    - Python Library to manipulate JIRA ticketing system

You should be able to unpack this directory and perform 

	python setup.py install

To install into your python site-packages directory, it will create links in /usr/local/bin for:

* eom             - the main orchestrator
* env-o-matic     - the typist unfriendly name of eom
* dbgen           - script that calls a perl script delphix-auto-provision (not included)
* jclose          - close JIRA tickets
* jcomment        - write comments to JIRA tickets
* jcontent        - wrapper around an interactive portable content tools

### Disclaimer
This is not a general purpose solution! It is specifically crafted to provide a
solution to the DEV/QA needs of StubHub and thus particulars of that environment
are coded into the logic of the programs.  In particular, the dev environments
are named as: 
* srwdXX           - a fully virtual Environment
* srwqXX           - more virtual environments
* srweXX           - performance environments, which have physical blades along with VMs

Certain CONSTANTS point to specific targets in the StubHub DEV/QA environment

* REGSERVER = "srwd00reg015.stubcorp.dev" # Use this server to run commands
* DEFAULT_LOG_PATH = "/nas/reg/log/jiralab/env-o-matic.log" # default place to write the log file to

Usage
---------

geowhite@srwd00reg010 github]$ eom
usage: eom [-h] [-u USER] [-p PASSWORD] [-e ENV] [-q ENVREQ] [-r RELEASE]
           [-b BUILD_LABEL] [-R RESTART_ISSUE] [-l LOGFILE] [-c EOM_INI_FILE]
           [-P EOM_PROFILE] [-d DEPLOY] [--syslog SYSLOG] [--confirm]
           [--ignoreini] [--ignorewarnings] [--content_refresh [no]]
           [--content_tool [no]] [--validate_bigip [no]]
           [--validate_forsmoke [no]] [--close_tickets [no]]
           [--skipreimage [no]] [--skipdbgen [no]] [--noprepatch [no]]
           [--nopostpatch [no]] [--withsiebel [no]] [--withbpm WITHBPM]
           [--init_tokentable [no]] [--override [no]] [--deploy_to DEPLOY_TO]
           [--cmd_to CMD_TO] [--reimage_to REIMAGE_TO]
           [--content_to CONTENT_TO] [--dbgen_to DBGEN_TO]
           [--verify_to VERIFY_TO] [-D] [-v]

eom (env-o-matic)--Basic Automation to build out DEV/QA environments

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  user to access JIRA
  -p PASSWORD, --password PASSWORD
                        password to access JIRA
  -e ENV, --env ENV     environment name to provision (example: srwd03
  -q ENVREQ, --envreq ENVREQ
                        environment request issue ID (example: ENV_707
  -r RELEASE, --release RELEASE
                        release ID (example: rb1218
  -b BUILD_LABEL, --build_label BUILD_LABEL
                        build label to deploy, ex.
                        --build_label=rb_ecomm_13_5-186593.209
  -R RESTART_ISSUE, --restart RESTART_ISSUE
                        ENV or PROPROJ issue to restart from,
  -l LOGFILE, --logfile LOGFILE
                        file to log to (if none, log to console)
  -c EOM_INI_FILE, --config EOM_INI_FILE
                        load a specific .eom.ini file
  -P EOM_PROFILE, --profile EOM_PROFILE
                        specify a label present in the .eom.ini file to load
                        options from
  -d DEPLOY, --deploy DEPLOY
                        Deploy full|properties|java|restart|no can be used
                        more than once ex. -d java -d properties
  --syslog SYSLOG       Specify a syslog server, '/dev/log' or 'host:514'
  --confirm             print out actions before executing the job
  --ignoreini           ignore any .eom.ini file present
  --ignorewarnings      continue with deploy, even with env-validate warnings.
                        note: sudo/ssh warnings will not be ignored

Switches:
  Example: --skipreimage=no will TURN ON re-imaging if skipreimage was set to true in the eom.ini file

  --content_refresh [no]
                        assert to run content refresh during deploy
  --content_tool [no]   assert to run the portable content tool after deploy
  --validate_bigip [no]
                        assert to validate BigIP after deploy
  --validate_forsmoke [no]
                        assert to validate readiness for smoke test
  --close_tickets [no]  assert to close DB & PROPROJ tickets
  --skipreimage [no]    assert to skip the re-image operation
  --skipdbgen [no]      assert to skip the db creation operation
  --noprepatch [no]     assert to DISABLE pre deploy patch script
  --nopostpatch [no]    assert to DISABLE DB creation patching
  --withsiebel [no]     assert to build a Siebel database along with Delphix
  --withbpm WITHBPM     connect to a bpm instance
  --init_tokentable [no]
                        initialize token table with release version
  --override [no]       override env delivered lock-out mechanism

Time out adjustments:
  --deploy_to DEPLOY_TO
                        set the timeout for deploy step in sec.
  --cmd_to CMD_TO       set the timeout for command execution return
  --reimage_to REIMAGE_TO
                        set the timeout for reimage operation in sec.
  --content_to CONTENT_TO
                        set the timeout for content refresh in sec.
  --dbgen_to DBGEN_TO   set the timeout for database creation in sec.
  --verify_to VERIFY_TO
                        set the timeout for verification ops in sec.

Informational:
  -D, --debug           turn on DEBUG additional Ds increase verbosity
  -v, --version         show program's version number and exit

Notes:
Most of these options can be placed in the YAML .eom.ini file.
Command line options will always override anything set in the .eom.ini.
For more information, see the env-o-matic man page

	
