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
import sys
import time
import socket
from optparse import OptionParser

__all__ = []
__version__ = 0.6
__date__ = '2012-12-11'
__updated__ = '2013-12-16'
program_name = os.path.basename(sys.argv[0])
program_version = "v%s" % __version__
program_build_date = str(__updated__)
program_version_message = '%s %s (%s)' % (program_name, program_version,
                                                 program_build_date)
program_shortdesc ="phaktor - write facter facts to a FS database"

parser = OptionParser(version=program_version_message)
parser.add_option("-c", "--config", dest="config_file", default="facts.ftr",
                  help="file containing keys to save", metavar="FILE")
parser.add_option("-r","--root", dest="root_dir", default=None,
                  help="root directory to store events")
parser.add_option("-d","--depth", dest="depth", default=3, type="int",
                  help="number of events to keep in history")


(options, args) = parser.parse_args()

q = open(options.config_file)

facts = {}
event = {}

for symbol in q.readlines():
    facts[ symbol.rstrip()] = 1
    
gmtime = time.gmtime()
iso_time = time.strftime("%Y-%m-%dT%H:%M:%S", gmtime)
fname_time = time.strftime(".%Y%m%dT%H%M%S", gmtime)
hostname = (socket.gethostname()).split(".")[0]

fname = hostname + fname_time
envidsp = re.search("(?P<envid>srw[dqe][0-9]{2})",fname)
if not envidsp:
    print("This is not running on a DEV system")
    sys.exit()
envid = envidsp.group("envid")

p = os.popen("facter","r")

event["iso_time"] = iso_time
for line in p.readlines():
    fsp = re.search("(?P<key>.+)=>(?P<value>.+)",line.rstrip())
    if (line.split())[0] in facts:
        event[fsp.group("key").rstrip()] = fsp.group("value").rstrip()
        
if options.root_dir:
    env_dir = os.path.abspath( options.root_dir + "/" + envid ) + "/"
    if not os.path.exists(env_dir):
        os.makedirs(env_dir)
    recfd = open((env_dir + fname),"w")
    try:
        os.unlink(env_dir + hostname )
    except OSError:
        pass
    os.symlink((env_dir + fname), env_dir + hostname)
    dirlist = sorted(os.listdir(env_dir),reverse=True)[:-1]
    if len(dirlist) > options.depth :
        for remove_file in dirlist[options.depth: ]:
            os.remove(env_dir + remove_file)

    sys.stdout = recfd
    
print("{"),
for key, value in event.iteritems():
    print( '"%s" : "%s",' % (key, value)),
print("}")

sys.stdout = sys.__stdout__
sys.exit()