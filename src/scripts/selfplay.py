#! /usr/bin/env python
import argparse
import os
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description="self-play robots vs. itself")
parser.add_argument('--half', action='store_true')
parser.add_argument('--most', action='store_true')
parser.add_argument('loc')
parser.add_argument('outdir')
args = parser.parse_args()

loc = args.loc
outdir = args.outdir

if not os.path.exists(outdir):
    os.mkdir(outdir)
subdir_index = 0
while True:
    subdir = os.path.join(outdir, str(subdir_index))
    if not os.path.exists(subdir):
	os.mkdir(subdir)
	break
    subdir_index += 1

if not loc in ('0','1','2','3'):
    print >>sys.stderr, "bad location:", loc
    sys.exit(1)

logdir = os.path.join("/data/twixt/log", loc)
if os.path.exists(logdir):
    shutil.rmtree(logdir)


def mkcmd():
    ps = "nnmplayer:resource=a,trials=1500,add_noise=0.25,temperature=0.5,smart_root=0"
    assert not (args.half and args.most)
    if args.half:
        num = "32"
    elif args.most:
        num = "60"
    else:
        num = "64"

    return ["./pmany.py", "-n", num, "-l", logdir, "--",
	"./battle.py", "-n", "40", "-r",
	"nnclient:location=/tmp/loc%s,name=a" % (loc,),
	"-w", ps, "-b", ps, "-M", "-R", "-T",  subdir + "/%n%"]

print " ".join(mkcmd())
