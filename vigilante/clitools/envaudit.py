#!/usr/bin/env python
# encoding: utf-8
'''
env-audit -- cli tool to perform auditing operations on Dev/QA collection data

@author:     geowhite
@copyright:  2014 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''

import sys
import os
import urllib2
import json


from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import REMAINDER

__all__ = []
__version__ = 0.6
__date__ = '2014-06-09'
__updated__ = '2014-07-05'


def http_get(request):
    return urllib2.urlopen(request).read()


def api_request(query_type, query_dict):
    BASE_URL = 'http://srwd00dvo002.stubcorp.dev:7000/vigilante/api/v0.1'
    request_url = ''
    if (query_type == "collector"):
        if "fqdn" in query_dict:
            request_url = "collector/role/current/%s" % query_dict["fqdn"]
        elif "domain" in query_dict:
            request_url = "collector/env/current/%s" % query_dict["domain"]
    elif (query_type == "query"):
        if "fqdn" in query_dict and "template" in query_dict:
            request_url = "query/template/%s/collector/role/current/%s" % (
                query_dict["template"], query_dict["fqdn"])
        if "domain" in query_dict and "template" in query_dict:
            request_url = "query/template/%s/collector/env/current/%s" % (
                query_dict["template"], query_dict["domain"])
    elif (query_type == "templates"):
        request_url = "templates/get/%s" % query_dict["template"]
        pass
    else:
        pass

    if request_url == '':
        return ''

    return http_get("%s/%s" % (BASE_URL, request_url))


def pretty_print_audit(template_struct, result_struct, args):
    summary_msg_role = '\nRole "%s" is %s compliant with template "%s" '
    summary_msg_env = '\nEnvironment "%s" is %s compliant with template "%s" '
    header_msg = '''
    Host                                   Key                 Template Value        Actual Value
    ____________________________________________________________________________________________________
    '''
    column_msg = '''
    %s            %s                %s              %s
    '''
    if result_struct['meta']['type'] == "role-diff":
        compliantP = "NOT" if result_struct['body'] else ""
        print (summary_msg_role %
              (args.role, compliantP, template_struct['meta']['name']))
        if compliantP:
            print (header_msg),
            for key in result_struct['body']:
                print(column_msg %
                     (args.role, key, template_struct['body'][key],
                         result_struct['body'][key])),
    elif result_struct['meta']['type'] == "env-diff":
        compliantP = ""
        for role_key in result_struct['body']:
            if result_struct['body'][role_key]:
                if result_struct['body'][role_key][0]['body']:
                    compliantP = "NOT"
        print (summary_msg_env %
              (args.envid, compliantP, template_struct['meta']['name']))
        print(header_msg),
        for role_key in result_struct['body']:
            if result_struct['body'][role_key]:
                if result_struct['body'][role_key][0]['body']:
                    for key in result_struct['body'][role_key][0]['body']:
                        print(column_msg %
                            (role_key, key,
                                result_struct['template'][role_key]['body'][key],
                                result_struct['body'][role_key][0]['body'][key])),


def main(argv=None):  # IGNORE:C0111
    '''Command line options.'''
    DEBUG = 0
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version,
            program_build_date)
    program_shortdesc = (
        "env-audit - get audit information for Dev/QA environments")

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_shortdesc,
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-e", "--env", dest="envid",
            default=None, help="target environment")
        parser.add_argument("-t", "--template", dest="template",
            default=None, help="template to use for auditing")
        parser.add_argument("-r", "--role", dest="role",
            default=None, help="fqdn of the role  to be used ")
        parser.add_argument('-l', '--list', action='store_true',
		help="list the template or collection data ", dest="list")
        parser.add_argument("-m", "--mgrmode", dest="mm",
            action='store_true',
		help="print the information in a more human readable form")
        parser.add_argument('-v', '--version', action='version',
		help="print the version ", version=program_version_message)
        parser.add_argument('-D', '--debug', dest="debug",
            action='store_true', help="turn on DEBUG switch")

        # Process arguments
        if len(sys.argv) == 1:
            parser.print_help()
            exit(1)

        args = parser.parse_args()

        if args.debug:
            DEBUG = True

        if args.list:
            if args.role:
                rs = json.loads(api_request("collector",
                                {"fqdn": args.role}))
                if args.mm:
                    pass
                else:
                    print(json.dumps(rs, indent=4, sort_keys=True))
            elif args.envid:
                rs = json.loads(
                    api_request("collector", {"domain": args.envid}))
                if args.mm:
                    pass
                else:
                    print(json.dumps(rs, indent=4, sort_keys=True))
            elif args.template:
                rs = json.loads(
                    api_request("templates",
                                {"template": args.template}))
                if args.mm:
                    pass
                else:
                    print(json.dumps(rs, indent=4, sort_keys=True))

        elif args.template:
            tplstruct = json.loads(
                api_request("templates", {"template": args.template}))
            if args.role:
                rs = json.loads(
                    api_request("query",
                                {"fqdn": args.role,
                                 "template": args.template}))
                if args.mm:
                    pretty_print_audit(tplstruct, rs, args)
                else:
                    print(json.dumps(rs, indent=4, sort_keys=True))
            elif args.envid:
                rs = json.loads(
                    api_request("query",
                                {"domain": args.envid,
                                 "template": args.template}))
                if args.mm:
                    pretty_print_audit(tplstruct, rs, args)
                else:
                    print(json.dumps(rs, indent=4, sort_keys=True))

        sys.exit()

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + str(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2

if __name__ == "__main__":
    main()
