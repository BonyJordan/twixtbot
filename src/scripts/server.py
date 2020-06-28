#! /usr/bin/env python
import os
import sys


def usage():
    print >>sys.stderr, "usage:",sys.argv[0],"model location"
    sys.exit(1)

if len(sys.argv) != 3:
    usage()

model = sys.argv[1]
loc = sys.argv[2]
if not loc in "0123":
    print >>sys.stderr, "bad location"
    usage()

logfile = "out" + loc

cmd = ["./nns.py", "-m", model, "-l", "/tmp/loc"+loc]
print " ".join(cmd)

os.putenv("CUDA_VISIBLE_DEVICES", loc)
sys.stdin.close()
sys.stdout = open(logfile, "w")
sys.stderr = open(logfile, "w")
os.execv(cmd[0], cmd)
