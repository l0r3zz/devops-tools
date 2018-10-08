#Copyright (c) 2018 Geoffrey White
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
###
##
#   sloldr: A quick and easy  program designed to load, unload SLO components,
#   service and product definitions into the Blameless Product

import argparse
import sys
import yaml
import json
import os
import inspect
import concurrent.futures
import mylog


#############################   Globals  ######################################
Debug = False
Log = None
Quiet = False
###############################################################################
################# These are debugging helper functions ########################


def pretty_print(obj, ofd=sys.stdout):
    """ Dump a Python datastructure to a file (stdout is the default)
    in a human friendly way"""
    json.dump(obj, ofd, sort_keys=True, indent=4)
    ofd.flush()


def pretty_prints(str, ofd=sys.stdout):
    """ Dump a json string to a file (stdout is the default)
    in a human friendly way"""
    ofd.write("'")
    json.dump(json.loads(str), ofd, sort_keys=True, indent=4)
    ofd.write("'")
    ofd.flush()


def std_prints(str, ofd=sys.stdout):
    """ Dump a json string to a file (stdout is the default)"""

    ofd.write("'")
    json.dump(json.loads(str), ofd)
    ofd.write("'")
    ofd.flush()


###############################################################################
#############################   main function Definitions  ####################
def process_metrics(metrics):
    pass
    return

def read_spec(av):
    """ Load the spec file (runbook)"""
    spec_path = av.file
    if os.path.exists(spec_path):
        try:
            specs = yaml.load(open(spec_path))
        except yaml.scanner.ScannerError as err:
            Log.error("Error:%s" % err)
            sys.exit(1)
    else:
        Log.error("No specifications file found at %s" % spec_path)
        sys.exit(1)
    return specs

###############################################################################
def main():
    """
    Program main loop
    """

    def get_opts():
        parser = argparse.ArgumentParser(
            description="Load/unload SLO indicatiors")
        parser.add_argument('--file', "-f", default="-",
                            help="yaml file containing specifications")
        parser.add_argument('--debug', "-d", action="store_true",
                     help="Enable various debugging output")
        parser.add_argument('--quiet', "-q", action="store_true",
                     help="silence all output")
        parser.add_argument('--verify', "-v", action="store_true",
                     help="Perform only the verification actions on the yaml")
        parser.add_argument('--loglevel', "-l", default="WARN",
                     help="Log Level, default is WARN")
        parser.add_argument('--unload', "-u", action="store_true",
                     help="Unload the contents of the Yaml file")
        args = parser.parse_args()
        return args

    argv = get_opts()
    global Debug
    global Log
    global Quiet
    Debug = argv.debug
    if Debug:
        loglevel = "DEBUG"
    else:
        loglevel = argv.loglevel
    if argv.quiet:
        Quiet = True
        devnull = open("/dev/null","w")
        Log = mylog.logg("sloldr", cnsl=True, llevel=loglevel, sh=devnull)
    else:
        Log = mylog.logg("sloldr", cnsl=True, llevel=loglevel)
    slometrics = read_spec(argv)
    process_metrics(slometrics)
    if Debug and not Quiet:
        pretty_print(slometrics)
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)

