#!/usr/bin/python
import os
import re

q = open("facts.ftr")
facts = {}
for symbol in q.readlines():
    facts[ symbol.rstrip()] = 1
p = os.popen("facter","r")
print("{"),
for line in p.readlines():
    fsp = re.search("(?P<key>.+)=>(?P<value>.+)",line.rstrip())
    if (line.split())[0] in facts:
        print('"%s" : "%s",' % (fsp.group("key"),fsp.group("value"))),
print("}")
