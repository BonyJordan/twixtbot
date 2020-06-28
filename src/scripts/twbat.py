#! /usr/bin/env python
import argparse
import os
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description="play net vs. old")
parser.add_argument('series')
parser.add_argument('loc')
parser.add_argument('trials')
args = parser.parse_args()

if not args.loc in ('0','1','2','3'):
    print >>sys.stderr, "bad location:", args.loc
    sys.exit(1)

if args.series == '3':
    tname = "/data/twixt/training/nn3_vs_tw4.tr"
    oname = "twbat3.out"
elif args.series == '4':
    tname = "/data/twixt/training/nn4_vs_tw3.tr"
    oname = "twbat4.out"
else:
    print >>sys.stderr, "bad series:", args.series
    sys.exit(1)

def mkcmd():
    cmd = ["./battle.py", "-n", "2",
	"-r", "nnclient:location=/tmp/loc%s,name=net" % (args.loc,),
	"-w", "nnmplayer:resource=net,trials=2500",
	"-b", "twplayer:time=%s" % (args.trials,),
	"-M", "-F", "-T", tname,
	">", oname, "2>&1", "&"]
    return cmd

print " ".join(mkcmd())
