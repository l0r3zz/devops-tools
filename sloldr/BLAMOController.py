#!/usr/bin/env python

import sys          # reads command-line args
import ApiHelper
import json

PORT = 443


class BLAMOController(ApiHelper.ApiHelper):
    '''Object that represents The Blameless API'''

    def __init__(self, host, port=443):
        # inherit from ApiHelper
        ApiHelper.ApiHelper.__init__(self, host, port,"/api/v1", verify=False)

    def get_services(self):
        return self.ws_get("/services")

    def create_component(self, body):
        return self.ws_post("/components", body)

    def delete_components(self, uid):
        return self.ws_delete("/components/%s" %(uid))

    def create_slio(self, body):
        return self.ws_post("/slt", body)

    def connect(self, logincmd, token=None, client_id=None, secret=None, authurl=None,timeout=300):
        self.timeout = timeout
        if token :
            self.headers["Authorization"] = "Bearer %s" % (token)
        self.urlprefix = "https://%s:%s%s" % (
            self.host, self.port, self.apiprefix)
        resp = self.request("get",logincmd)
        self.cookies = resp.cookies
        resp.raise_for_status()
        return resp





# These are non-API helper functions

    def find_serviceID_by_name(self, name, services_list):
        for service in services_list["services"]:
            if service["name"] == name:
                return service["_id"]
        return( None)

    def find_componentID_by_name(self, name, component_list):
        for component in component_list["components"]:
            if component["name"] == name:
                return component["_id"]
        return( None)

    def pretty_print(self, obj, ofd=sys.stdout):
        json.dump(obj, ofd, sort_keys=True, indent=4)
        ofd.flush()

    def pretty_prints(self, str, ofd=sys.stdout):
        ofd.write("'")
        json.dump(json.loads(str), ofd, sort_keys=True, indent=4)
        ofd.write("'")
        ofd.flush()

    def std_prints(self, str, ofd=sys.stdout):
        ofd.write("'")
        json.dump(json.loads(str), ofd)
        ofd.write("'")
        ofd.flush()

    def save(self, ofd):
        return

    def restore(self, ifd):
        return

if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("usage: %s <instance-addr>  <client_id> <secret> "\
               % sys.argv[0])
        sys.exit(1)

    instance_ip = sys.argv[1]
    client_id = sys.argv[2]
    secret = sys.argv[3]
    auth_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlJFUTFRMFpETlRsRFJURTFNalJCUVVSRE9FWkVSalpFUTBZelF6WTBRVFEyTlVRek5EQTNOdyJ9.eyJpc3MiOiJodHRwczovL2JsYW1lbGVzc2hxLmF1dGgwLmNvbS8iLCJzdWIiOiJMUjJSWWdtYllCMFdja2ttbzE2Y2pSYkxiU1V0RGNQNEBjbGllbnRzIiwiYXVkIjoiYmxhbWVsZXNzY3JlLmJsYW1lbGVzcy5pbyIsImlhdCI6MTUzODg3ODI5NywiZXhwIjoxNTM4OTY0Njk3LCJhenAiOiJMUjJSWWdtYllCMFdja2ttbzE2Y2pSYkxiU1V0RGNQNCIsImd0eSI6ImNsaWVudC1jcmVkZW50aWFscyJ9.eoc6OfX6OnawBTrpQNSgW415zU8n6CxnYkXYDkd94jAIIdx2XpslAw3nyu-_WyGIdkYeol1ypTeaMGKOKYSG951BDmNwAy2K0Yp41_53-fkzWEbqHyf8OZj7sqRRatdKDGUQDDHO_uhiaSU5ny9Sh8812rtv9iJFld4cSUhHmoG0EIFTSdeJyFwMldWM2fe1jZ7TETdAAW1CZXR1mr90wv_Dzcd7TcKlmJY3bbxWqTZTRR7X2o2SEgXpTRlvoufr5rb1tBzjllPOZ3QVtPrkxX4E6cpaZGXYl5OPGe63y8D36PCJ3I2DjFnzTwOqvLmAtW6hI-hVyCN6RRvILuUoyQ"

    instance = BLAMOController(instance_ip, PORT)
    session = instance.connect("/services", token=auth_token)
    instance.pretty_prints(session.text)
    services_list = json.loads(session.text)
    sid = instance.find_serviceID_by_name("ua-s9", services_list)
    for index in range(10):
        body = { "name": "evertest"+str(index), "componentType": "shard",
                "serviceId": sid}
        instance.create_component(json.dumps(body))
        slio_body = '{"sli_type": "availability", "tracked_resource.type": "service", "tracked_resource.id": "5b6cea0b82edb912be88259d", "data_source_metadata.name": "pingdom", "data_source_metadata.metric_id": "%s", "data_source_metadata.metric_name": "%s", "indicator_metric.value_type": "bool", "indicator_metric.unit": "", "indicator_metric.scope": "All backend services", "indicator_metric.ingestion_delay": 0, "indicator_metric.backfill_start_date": "2018-08-01 13:00:00", "slo.objective_value": "True", "slo.comparason_operator": "equal", "slo.objective_percentage": 99.9, "measurement_frequency": -1}'


    print ("End of Program")
