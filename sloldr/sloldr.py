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


    if  av.unload: #only if you are unloading data
        if "components" in metrics:
            session = instance.connect("/components", token=auth_token)
            components_list = json.loads(session.text)
            for component in metrics["components"]:
                cid = instance.find_componentID_by_name(component["name"],
                                                        components_list)
                instance.delete_component(cid)
    else:
        if "products" in metrics:
            pass
            session = instance.connect("/products", token=auth_token)
            products_list = json.loads(session.text)
        if "services" in metrics:
            pass
            session = instance.connect("/services", token=auth_token)
            services_list = json.loads(session.text)
        if "components" in metrics:
            session = instance.connect("/services", token=auth_token)
            services_list = json.loads(session.text)
            for component in metrics["components"]:
                sid = instance.find_serviceID_by_name(component["serviceName"], services_list)
                body = component
                body["serviceId"] = sid
                instance.create_component(json.dumps(body))
        if "slio" in metrics:
            session = instance.connect("/components", token=auth_token)
            components_list = json.loads(session.text)
            if ( "user" in metrics["slio"]
                and "password" in metrics["slio"]
                and "app-key" in metrics["slio"]
                ):
                pingdom = PINGDOMController.PINGDOMController()
                session = pingdom.login("/checks",user = metrics["slio"]["user"],
                                        password = metrics["slio"]["password"],
                                        api_key = metrics["slio"]["app-key"],
                                        account_email = metrics["slio"]["account-email"]
                                        )
#                session = instance.get_pingdom_checks()
                metrics_list = json.loads(session.text)
                if "trackers" in metrics["slio"]:
                    for sig in metrics["slio"]["trackers"]:
                        cid = instance.find_componentID_by_name(sig["component_name"],
                                                                components_list)
                        m_signal = pingdom.get_metric_by_name(sig["metric_name"],
                                                              metrics_list["checks"])
                        if m_signal == None:
                            continue
                        ds_metric_id = str(m_signal["id"])
                        ds_metric_name = m_signal["name"]
                        slio_body = {
                            "dataSourceMetadata": {
                                "metricId": ds_metric_id,
                                "metricName": ds_metric_name,
                                "name": "Pingdom"
                            },
                            "indicatorMetric": {
                                "backfillStartDate": "2018-02-01",
                                "ingestionDelay": 0,
                                "scope": "Evernote Test",
                                "unit": "none",
                                "valueType": "bool"
                            },
                            "measurementFrequency": -1,
                            "sliType": "availability",
                            "slo": {
                                "comparasonOperator": "equal",
                                "objectivePercentage": "99.95",
                                "objectiveValue": "true"
                            },
                            "trackedResource": {
                                "id": cid,
                                "type": "component"
                            }
                        }
                        instance.create_slio(json.dumps(slio_body))
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
    global Debug
    global Log
    global Quiet


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

