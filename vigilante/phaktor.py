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

__all__ = []
__version__ = 0.2
__date__ = '2012-12-11'
__updated__ = '2013-12-13'

q = open("facts.ftr")
facts = {}
event = {}
for symbol in q.readlines():
    facts[ symbol.rstrip()] = 1
p = os.popen("facter","r")
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
event["iso_time"] = iso_time
for line in p.readlines():
    fsp = re.search("(?P<key>.+)=>(?P<value>.+)",line.rstrip())
    if (line.split())[0] in facts:
        event[fsp.group("key").rstrip()] = fsp.group("value").rstrip()
print("{"),
for key, value in event.iteritems():
    print( '"%s" : "%s",' % (key, value)),
print("}")
