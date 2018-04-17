#!/usr/bin/env python2.7
import os
import argparse
import sys
import re
import csv
import socket
from netaddr import *
import concurrent.futures
from dns import resolver, reversename
import sshpubkeys
from ipwhois import IPWhois
from itertools import tee, islice, izip_longest
import datetime

# Code to enable look-ahead doing file IO:
def get_next(some_iterable, window=1):
    items, nexts = tee(some_iterable, 2)
    nexts = islice(nexts, window, None)
    return izip_longest(items, nexts)

#############################   Globals  #######################################
# This array holds a list of CIDRs for the Virtual Clean Rooms
vcrcidrdb = []
# Ths dict contains the customer ssh key info keyed by fingerprint
CustomerKeys = dict()
# This dict contains the Connection tracking Objects, key'ed by source IP
# address
SrcIPs = dict()
# This array holds a list of tuples, (ip-addr, revdns, arin_data) after
# processing
IPresults = []
# This arraY holds the source ips to be processed
IPvector =[]
# Duration calculations, key = proc_id, value= 3 element array, start, stop,
# duration (att strings)
Durations = {}
################################################################################

#############################   Class Definitions  #############################
class Session:
    def __init__(self,dc,sshdhost, userid, kfingerprint,starttime,sip,pid):
        self.dc = dc
        self.counter = 0
        self.sshdhost = sshdhost
        self.userid = userid
        self.key_fingerprint = kfingerprint
        self.e_mail = ""
        self.options = ""
        self.start_time = starttime
        self.stop_time = ""
        self.duration = ""
        self.source_ip = sip
        self.procid = pid


class SourceIP:
    def __init__(self,revdns,coo, isaVCR,addr):
        self.counter = 0
        self.addr = addr
        self.domain = revdns
        self.whois_data = coo
        self.isVCRP = isaVCR
        self.session_list = []
        IPvector.append(addr)

    def new_session(self,newsession):
        self.session_list.append(newsession)
        self.counter+=1
        newsession.counter = self.counter
################################################################################

def isaVCRaddr(addr):
    """Return True if the Address is a VCR address, false otherwise"""
    if addr == "UNKNOWN":
        print "UNKNOWN IP! suspect Hacking Attempt"
        return False
    ipaddr = IPAddress(addr)
    for entry in vcrcidrdb :
        ipnet = entry
        # let's try for the quick-win match
        if ipaddr == ipnet.ip and (ipnet.netmask ==
                                   IPAddress('255.255.255.255')):
            return True
        # Have to do examine subnet masks
        elif (ipaddr & ipnet.netmask) == ipnet.network :
            return True
        else:
            continue
    return False

def process_VCR_database(av):
    """ Load up the VCR netmask database"""
    with open(av.vcrcidrs) as netblk:
        for line in netblk:
            vcrcidrdb.append(IPNetwork(line))
    return

def process_sshkeys(av):
    """ Process the ssh key directory if present"""
    if av.keydir:
        for keyfile in os.listdir(av.keydir):
                current_file = os.path.join(av.keydir, keyfile)
                with open(current_file, "rb") as file:
                    for sshkey in file:
                        if sshkey.rstrip() == "":
                            continue
                        try:
                            ssh = sshpubkeys.SSHKey(sshkey.rstrip(),
                                                    strict_mode=False)
                            ssh.parse()
                        except sshpubkeys.exceptions.InvalidKeyException as err:
                            print(("Invalid key:%s %s" % (sshkey.rstrip(), err)))
                            continue
                        except UnicodeDecodeError  as err:
                            print(("Invalid key:%s %s" % (sshkey.rstrip(), err)))
                            continue
                        key_fingerprint = ssh.hash_md5()[4:] #delete "MD5:"
                        key_email = ssh.comment
                        key_options = ssh.options
                        if key_fingerprint in CustomerKeys:
                            print(
                              "Warning: key %s already in Database as e-mail: %s"
                              ", this is %s"  %
                                 (key_fingerprint,
                                   CustomerKeys[key_fingerprint]["e_mail"],
                                   key_email) )
                            continue
                        CustomerKeys[key_fingerprint] = {"e_mail" : key_email,
                                                         "options" : key_options}
    return

def process_logfile(av):
    """Open and process an sshd logfile"""
    logentry = re.compile('(?P<ss_timestamp>'
                          '[JFMAMSOND][a-z]{2}\s+\d{1,2}\s\d{2}\:\d{2}\:\d{2})'
                         '\s(?P<ss_hostname>'
                          '(([a-zA-Z0-9]+|[a-zA-Z0-9][a-zA-Z0-9\-]*'
                          '[a-zA-Z0-9])\.)*'
                          '([A-Za-z0-9]+|[A-Za-z0-9][A-Za-z0-9\-]*))'
                          '\s(?P<ss_process>[a-zA-Z0-9\-\[\]]*\:\s)'
                          '(?P<ss_message>.+$)'
                          )
# set up resolver so it doesn't take forever
    dns_resolver = resolver.Resolver()
    dns_resolver.timeout = 1
    dns_resolver.lifetime = 1

    def lookups(addr):
       """worker function to do reverse DNS and ARIN lookups"""
       try:
           reverse_name = reversename.from_address(addr)
           domain = dns_resolver.query(reverse_name,
                                       "PTR")[0].to_text()[:-1]
           arin_obj = IPWhois(addr)
           arin_data = arin_obj.lookup_rdap(depth=1)

       except:
           domain = ""
           arin_data = {}
       return (addr,domain, arin_data)

    def get_duration(starttime,stoptime):
       """Calculate session duration from start and stop times"""
       fmt = "%b %d %H:%M:%S"
       start = datetime.datetime.strptime(starttime,fmt)
       stop = datetime.datetime.strptime(stoptime,fmt)
       duration = stop - start
       if duration.days < 0:
           return "__:__:__"
       else:

           return str(duration)

# Process the log file
    with open(av.file) as logfile:

        # For each line in the log file, start by parsing out the timestamp,
        # hostname, process id info and message body.
        # Then, examine the message body looking for key messages that signal
        # the start of an actual sftp connection via ssh key, When an
        # "Accepted Public Key" message is received, look ahead one line
        # to see if you find an entry that has the pid for the session,
        # this will be used to match up with a message signaling the disconnect
        # or teardown of the session, this is used to derive Duration
        # information

        for line, next_line in get_next(logfile):
            timestamp = logentry.match(line).group("ss_timestamp")
            sshd_hostname = logentry.match(line).group("ss_hostname")
            sshd_process = logentry.match(line).group("ss_process")
            sshd_message = logentry.match(line).group("ss_message")
            if "Connection from" in sshd_message:
                connection_message = sshd_message
                _,_,addr,_,port =  connection_message.split()
                if addr in SrcIPs:
                    srcip = SrcIPs[addr]
                    srcip.counter+1
                else:
                    if addr is not "UNKNOWN":
                        domain = ""
                        arin_data = {}
                    else:
                        domain = "UNKNOWN"
                        arin_data = {}

                    SrcIPs[addr] = SourceIP(
                                    domain,arin_data,isaVCRaddr(addr),addr)
                continue
            elif "Found matching" in sshd_message:
                found_message = sshd_message
                _,_,_,_,keyfinger = found_message.split()
                continue
            elif "Postponed publickey" in sshd_message:
                postponed_message = sshd_message
                _,_,_,userid_post,_,addr_post,_,port,_ = postponed_message.split()
                continue
            elif "Accepted publickey" in sshd_message:
                accepted_message = sshd_message
                _,_,_,userid,_,addr,_,port,_ = sshd_message.split()
                if "User child is on pid" in next_line:
                    session_pid = logentry.match(
                        next_line).group("ss_message").split()[5]
                    Durations[session_pid+addr] = [addr,timestamp,"",""]
                else:
                    session_pid = ""
                if addr in SrcIPs:
                    srcip = SrcIPs[addr]
                    dc = sshd_hostname.split('.')[3]
                    session = Session(dc,sshd_hostname,
                                      userid, keyfinger,
                                      timestamp,addr, session_pid )
                    if keyfinger in CustomerKeys:
                        session.e_mail = CustomerKeys[keyfinger]["e_mail"]
                        session.options = CustomerKeys[keyfinger]["options"]
                    srcip.new_session(session)
                    continue
                else:
                    print "Accepted connection but no connection entry found!"
                    print ("time: %s address: %s user: %s" %
                           ( timestamp, addr,userid))
                    print "Adding and continuing"
                    domain = ""
                    arin_data = {}
                    dc = sshd_hostname.split('.')[3]
                    SrcIPs[addr] = SourceIP(
                                    domain,arin_data,isaVCRaddr(addr),addr)
                    srcip.session_list.append(Session(dc,sshd_hostname,userid,
                                         keyfinger,timestamp,addr, session_pid))
            elif "Received disconnect" in sshd_message:
                addr = sshd_message.split()[3][:-1] #Remove trailing :
                sess_pid_obj = re.search(r"[0-9]+", sshd_process)
                sess_pid = sess_pid_obj.group(0)
                durkey = sess_pid+addr
                if durkey in Durations:
                    Durations[durkey][2] = timestamp
                    Durations[durkey][3] = get_duration(Durations[durkey][1],
                                                        Durations[durkey][2])
                continue
            elif "Closing connection" in sshd_message:
                addr = sshd_message.split()[3]
                sess_pid_obj = re.search(r"[0-9]+", sshd_process)
                sess_pid = sess_pid_obj.group(0)
                durkey = sess_pid+addr
                if durkey in Durations:
                    Durations[durkey][2] = timestamp
                    Durations[durkey][3] = get_duration(Durations[durkey][1],
                                                        Durations[durkey][2])
                continue
            else:
                continue

    # We've processed the entire logfile and built in-memory databases of IP
    # address and session information that will be used to write the csv info.
    # Reverse DNS lookups, and ARIN data API calls take a significant amount of
    # time, so let's parallize their execution using the concurrent.futures
    # package with a pool size of 128 workers.

    with concurrent.futures.ThreadPoolExecutor(max_workers = 128) as pool:
        IPresults = list(pool.map(lookups,IPvector))

    # Update the SrcIP database with the map results (reduce)
    for ip_tuple in IPresults:
        addr = ip_tuple[0]
        revdns = ip_tuple[1]
        arin_data = ip_tuple[2]
        SrcIPs[addr].domain = revdns
        SrcIPs[addr].whois_data = arin_data
    return

def write_csv(av):
    """Write out a csv file containing the results"""
    with open(av.csv,'wb') as f:
        writer = csv.writer(f)
        header = ["Address","Domain","ARIN Network Name", "ASN CC", "VCR?",
                  "Start Time", "Stop Time","Duration","Session #","Data Center",
                  "SFTP Host","Userid",
                  "key_fingerprint","e-mail","e-mail Domain","IP restrictions"]
        writer.writerow(header)
        for ipaddr, ipdata in SrcIPs.iteritems():
            row_prefix = []
            row_prefix.append(ipaddr)
            row_prefix.append(ipdata.domain)
            # Add change ARIN info here (results of IPwhois package)
            if ipdata.whois_data == {}:
                row_prefix.append("NONE") # Empty ARIA network name
                row_prefix.append("NONE") # Empty ARIC country code
            else:
                row_prefix.append(ipdata.whois_data["network"]["name"])
                row_prefix.append(ipdata.whois_data["asn_country_code"])

            row_prefix.append(ipdata.isVCRP)
            for sess in ipdata.session_list:
                durkey = sess.procid+ipaddr
                if durkey in Durations:
                    sess.stop_time = Durations[durkey][2]
                    sess.duration = Durations[durkey][3]
                row = list(row_prefix)
                row.append(sess.start_time)
                row.append(sess.stop_time)
                row.append(sess.duration)
                row.append(sess.counter)
                row.append(sess.dc)
                row.append(sess.sshdhost)
                row.append(sess.userid)
                row.append(sess.key_fingerprint)
                if sess.e_mail :
                    row.append(sess.e_mail)
                    row.append(sess.e_mail.split("@")[-1]) # create domain name
                else:
                    row.append("no-email")
                    row.append("no-email-domain")
                if sess.options :
                    row.append(sess.options["from"])
                else:
                    row.append("NONE")

                writer.writerow(row)
    return


def main():
    """
    usage: vcrquery.py [-h] [--file FILE] [--keydir KEYDIR] [--vcrcidrs VCRCIDRS]
                       [--csv CSV]
           process sftp log data
           optional arguments:
            -h, --help            show this help message and exit
            --file FILE, -f FILE  If present, file to get log from, else stdin
            --keydir KEYDIR, -k KEYDIR
                                  If present, directory to get sshkeys from
            --vcrcidrs VCRCIDRS, -c VCRCIDRS
                                  If present, file that contains the vcr cidr block
            --csv CSV, -o CSV     file to output the csv result to

    """

    def get_opts():
        parser = argparse.ArgumentParser(description='process sftp log data')
        parser.add_argument('--file',"-f", default="-",
                   help="If present, file to get log from, else stdin")
        parser.add_argument('--keydir',"-k", default= None,
                   help="If present, directory to get sshkeys from")
        parser.add_argument('--vcrcidrs',"-c", default="vcr-cidr-blocks.txt",
                   help="If present, file that contains the vcr cidr block")
        parser.add_argument('--csv',"-o", default="some.csv",
                   help="file to output the csv result to")
        args = parser.parse_args()
        return args

    argv= get_opts()
    process_VCR_database(argv)
    process_sshkeys(argv)
    process_logfile(argv)
    write_csv(argv)
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
