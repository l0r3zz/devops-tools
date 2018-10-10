#! /usr/bin/env python
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
import BLAMOController
import PINGDOMController
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
def process_metrics(av,metrics):
    instance = BLAMOController.BLAMOController(av.instance, 443)
    if av.token:
        with open(av.token, 'r') as tokenfile:
            auth_token=tokenfile.read().replace('\n', '')
    elif av.cid and av.secret:
        with open(av.cid, 'r') as cidfile:
            client_id=cidfile.read().replace('\n', '')
        with open(av.secret, 'r') as secretfile:
            secret=secretfile.read().replace('\n', '')
    else:
        Log.error("Need both client_id file and secret or API token")
        sys.exit(1)


    if not av.unload: #only if you are unloading data
        session = instance.connect("/services", token=auth_token)
        services_list = json.loads(session.text)
        for component in metrics["components"]:
            sid = instance.find_serviceID_by_name(component["serviceName"], services_list)
            body = component
            body["serviceId"] = sid
            instance.create_component(json.dumps(body))
    else:
        if "components" in metrics:
            session = instance.connect("/components", token=auth_token)
            components_list = json.loads(session.text)
            for component in metrics["components"]:
                cid = instance.find_componentID_by_name(component["name"],
                                                        components_list)
                instance.delete_component(cid)

        if "services" in metrics:
            pass
        if "products" in metrics:
            pass
        if "slio" in metrics:
            if ( "user" in metrics["slio"]
                and "password" in metrics["slio"]
                and "app-key" in metrics["slio"]
                ):
                pingdom = PINGDOMController(instance_ip, PORT)
                session = pingdom.login("/checks",user = metrics["slio"]["user"],
                                        password = metrics["slio"]["password"],
                                        api_key = metric["slio"]["app-key"]
                                        )
                metrics_list = json.loads(session.text)
                slio_body = '{"sli_type": "availability", "tracked_resource.type": "service", "tracked_resource.id": "5b6cea0b82edb912be88259d", "data_source_metadata.name": "pingdom", "data_source_metadata.metric_id": "%s", "data_source_metadata.metric_name": "%s", "indicator_metric.value_type": "bool", "indicator_metric.unit": "", "indicator_metric.scope": "All backend services", "indicator_metric.ingestion_delay": 0, "indicator_metric.backfill_start_date": "2018-08-01 13:00:00", "slo.objective_value": "True", "slo.comparason_operator": "equal", "slo.objective_percentage": 99.9, "measurement_frequency": -1}'
                if "trackers" in metrics["slio"]:
                    for sig in metrics["slio"]["trackers"]:
                        pass
    return

def read_spec(av):
    """ Load the spec file """
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
    Log = mylog.logg("installtool", cnsl=True, llevel=loglevel, sh=devnull)

    def get_opts():
        parser = argparse.ArgumentParser(
            description="Load/unload SLO indicatiors")
        parser.add_argument('--file', "-f", default="-",
                            help="yaml file containing specifications")
        parser.add_argument('--token', default="",
                            help="file containing API token")
        parser.add_argument('--cid', default="",
                            help="file containing client ID")
        parser.add_argument('--secret', "-s", default="",
                            help="file containing secret")
        parser.add_argument('--instance',"-i", default="",
                            help="FQDN or IP of instance")
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
    process_metrics(argv, slometrics)
    if Debug and not Quiet:
        pretty_print(slometrics)
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)

