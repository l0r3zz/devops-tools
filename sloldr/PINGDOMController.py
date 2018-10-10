#!/usr/bin/env python

import sys          # reads command-line args
import ApiHelper
import json

PORT = 443


class PINGDOMController(ApiHelper.ApiHelper):
    '''Object that represents The Pingdom  API'''

    def __init__(self, host, port=443):
        # inherit from ApiHelper
        ApiHelper.ApiHelper.__init__(self, "api.pingdom.com", port,"/api/2.1", verify=False)

    def login(self, logincmd, user="admin", password="admin",api_key=None, timeout=300):
        self.auth = (user, password)
        self.timeout = timeout
        if api_key :
            self.headers["App-Key"] = api_key
        self.urlprefix = "https://%s:%s%s" % (
            self.host, self.port, self.apiprefix)
    #    resp = self.session.get(url,auth=self.auth, timeout=timeout)
        resp = self.request("get",logincmd)
        self.cookies = resp.cookies
        resp.raise_for_status()
        return resp

    def get_check_list(self):
        return self.ws_get("/checks")

# These are non-API helper functions

    def get_metric_by_name(self,name,list):
        for m in list:
            if m["name"] == name:
                return m
        return None

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

if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("usage: %s <instance-addr>  <user> <password> "\
               % sys.argv[0])
        sys.exit(1)

    instance_ip = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]

    instance = PINGDOMController(instance_ip, PORT)
    session = instance.login("/checks",user = "moiz@blameless.com",
                             password = "puo7AiX6hoh7uY4a",
                             api_key = "3sqzlcv90rfwv5r0apzswca8r8rbx52g")
    instance.pretty_prints(session.text)
    check_list = json.loads(session.text)


    print ("End of Program")
