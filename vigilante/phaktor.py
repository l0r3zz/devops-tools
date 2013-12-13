#!/usr/bin/python
import os
import re
import time

__all__ = []
__version__ = 0.1
__date__ = '2012-12-11'
__updated__ = '2013-12-11'

iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
q = open("facts.ftr")
facts = {}
for symbol in q.readlines():
    facts[ symbol.rstrip()] = 1
p = os.popen("facter","r")
print("{"),
print('"iso_time :  "%s"' % iso_time),
for line in p.readlines():
    fsp = re.search("(?P<key>.+)=>(?P<value>.+)",line.rstrip())
    if (line.split())[0] in facts:
        print('"%s" : "%s",' % (fsp.group("key").rstrip(),fsp.group("value").rstrip())),
print("}")
