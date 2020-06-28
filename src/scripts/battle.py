#! /usr/bin/env python
import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--half', action='store_true')
parser.add_argument('loc_name', nargs=2)
parser.add_argument('outdir')
args = parser.parse_args()

l0, n0 = args.loc_name[0].split(",")
l1, n1 = args.loc_name[1].split(",")
outdir = args.outdir

if os.path.exists(outdir):
    print >>sys.stderr, outdir + ": already exists"
    sys.exit(1)
os.mkdir(outdir)

if not l0 in ('0','1','2','3'):
    print >>sys.stderr, "bad location:", l0
    sys.exit(1)
if not l1 in ('0','1','2','3'):
    print >>sys.stderr, "bad location:", l0
    sys.exit(1)

def mkcmd(instance, w, b):
    def nnclient(loc, name):
	return "nnclient:location=/tmp/loc%s,name=%s" % (loc, name)
    def player(name):
	return "nnmplayer:resource=%s,trials=1500" % (name)
    ngame = "8" if args.half else "4"
    ninst = "25" if args.half else "50"

    return ["./pmany.py", "-n", ninst, "-l", "/data/twixt/log/b"+instance, "--",
	"./battle.py", "-n", ngame, "-r", nnclient(l0,n0), "-r", nnclient(l1,n1),
	w, player(n0), b, player(n1), "-M", "-F", "-T",
	os.path.join(outdir, instance + "_%n%")]

cmd2 = ["rm", "-rf", "/data/twixt/log/b0", "/data/twixt/log/b1"]
print "RUN:", " ".join(cmd2)
subprocess.call(cmd2)

print " ".join(mkcmd("0", "-w", "-b"))
print " ".join(mkcmd("1", "-b", "-w"))
