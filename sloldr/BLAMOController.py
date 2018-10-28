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

    def get_products(self):
        return self.ws_get("/products", params={"expandFields": "False","limit":1000,"offset": 0 })

    def create_product(self, body):
        return self.ws_post("/products", body)

    def delete_product(self, uid):
        return self.ws_delete("/products/%s" %(uid), params={"expandFields": "False"})

    def get_components(self):
        return self.ws_get("/components", params={"expandFields": "False","limit":1000,"offset": 0 })

    def create_component(self, body):
        return self.ws_post("/components", body, params={"expandFields": "False"})

    def delete_components(self, uid):
        return self.ws_delete("/components/%s" %(uid), params={"expandFields": "False"})

    def create_service(self, body):
        return self.ws_post("/services", body)

    def get_services(self):
        return self.ws_get("/services", params={"expandFields": "False","limit":1000,"offset": 0 })

    def delete_service(self, uid):
        return self.ws_delete("/services/%s" %(uid), params={"expandFields": "False"})

    def create_slio(self, body):
        return self.ws_post("/slt", body)

    def delete_slio(self, uid):
        return self.ws_delete("/slt/%s" %(uid), params={"expandFields": "False"})

    def get_pingdom_checks(self):
        return self.ws_get("/pingdom/checks")

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

    def find_serviceID_by_name(self, name, service_list):
        for service in service_list["services"]:
            if service["name"] == name:
                return service["_id"]
        return( None)

    def find_componentID_by_name(self, name, component_list):
        for component in component_list["components"]:
            if component["name"] == name:
                return component["_id"]
        return( None)

    def find_productID_by_name(self, name, product_list):
        for product in product_list["products"]:
            if product["name"] == name:
                return product["_id"]
        return( None)

    def find_slioID_by_name(self, name, slt_list):
        for slt in slt_list["serviceLevelTrackers"]:
            if slt["resource_name"] == name:
                return slt["slio_id"]
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
    auth_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlJFUTFRMFpETlRsRFJURTFNalJCUVVSRE9FWkVSalpFUTBZelF6WTBRVFEyTlVRek5EQTNOdyJ9.eyJpc3MiOiJodHRwczovL2JsYW1lbGVzc2hxLmF1dGgwLmNvbS8iLCJzdWIiOiJMUjJSWWdtYllCMFdja2ttbzE2Y2pSYkxiU1V0RGNQNEBjbGllbnRzIiwiYXVkIjoiYmxhbWVsZXNzY3JlLmJsYW1lbGVzcy5pbyIsImlhdCI6MTUzOTI2OTEyMiwiZXhwIjoxNTM5MzU1NTIyLCJhenAiOiJMUjJSWWdtYllCMFdja2ttbzE2Y2pSYkxiU1V0RGNQNCIsImd0eSI6ImNsaWVudC1jcmVkZW50aWFscyJ9.Kn6gAhyqR93IybdXWKZEMjMKX8i8RuvdX16wrFKVFITGqmpfiXqaCD03TZYI7N_mIOLqMHSOaj-tBbRJtT9xBJrj31tDDBZFX2_8zz9O8vU1_5Pvu76E18mfefJho9B0-ReAQfwDVEWEAAlPaRXTBony0Kp4SEbrzuK4CVr0hzt85zFKxsPqRgm8IS4Kd9BNkDq2hMC0wibqavg99ONyPE54ea_Sky2jA5bXDPOXHtYUxZCbGu_4s9mwnZuQ4CJooT4pVHkcx97ukIY6rFBDR1h943tB5XrS9tl6zurfHds-JwkqVc_8h2yU8Eml4yfTidzyUU9DJVelHcEzxUQPGw"
    instance = BLAMOController(instance_ip, PORT)
    session = instance.connect("/services", token=auth_token)
    instance.pretty_prints(session.text)
    services_list = json.loads(session.text)
    sid = instance.find_serviceID_by_name("ua-s9", services_list)
    for index in range(40,50,1):
        body = { "name": "evertest"+str(index), "componentType": "shard",
                "serviceId": sid}
        instance.create_component(json.dumps(body))
        slio_body = '{"sli_type": "availability", "tracked_resource.type": "service", "tracked_resource.id": "5b6cea0b82edb912be88259d", "data_source_metadata.name": "pingdom", "data_source_metadata.metric_id": "%s", "data_source_metadata.metric_name": "%s", "indicator_metric.value_type": "bool", "indicator_metric.unit": "", "indicator_metric.scope": "All backend services", "indicator_metric.ingestion_delay": 0, "indicator_metric.backfill_start_date": "2018-08-01 13:00:00", "slo.objective_value": "True", "slo.comparason_operator": "equal", "slo.objective_percentage": 99.9, "measurement_frequency": -1}'


    print ("End of Program")
