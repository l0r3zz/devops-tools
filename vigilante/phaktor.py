#!/usr/bin/python
# encoding: utf-8
'''
phaktor - write facter facts to a FS database

@author:     Geoff White
@copyright:  2013 StubHub. All rights reserved.
@license:    Apache License 2.0
@contact:    geowhite@stubhub.com
'''
import os
import re
import time
import socket
from optparse import OptionParser

__all__ = []
__version__ = 0.3
__date__ = '2012-12-11'
__updated__ = '2013-12-13'

parser = OptionParser()
parser.add_option("-c", "--config", dest="config_file", default="facts.ftr",
                  help="file containing keys to save", metavar="FILE")
parser.add_option("-r","--root", dest="root_dir", default=None,
                  help="root directory to store events")

(options, args) = parser.parse_args()

q = open(options.config_file)

facts = {}
event = {}

for symbol in q.readlines():
    facts[ symbol.rstrip()] = 1
    
gmtime = time.gmtime()
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", gmtime)
fname_time = time.strftime(".%Y%m%dT%H%M%S", gmtime)
fname = socket.gethostname() + fname_time

p = os.popen("facter","r")

event["iso_time"] = iso_time
for line in p.readlines():
    fsp = re.search("(?P<key>.+)=>(?P<value>.+)",line.rstrip())
    if (line.split())[0] in facts:
        event[fsp.group("key").rstrip()] = fsp.group("value").rstrip()
print("{"),
for key, value in event.iteritems():
    print( '"%s" : "%s",' % (key, value)),
print("}")
