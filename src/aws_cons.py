#! /usr/bin/env python
import argparse
import os
import random
import subprocess
import sys

import naf

# This method is bad because random holdout positions are extremely
# similar to training positions.
allow_holdout = False

parser = argparse.ArgumentParser("Collate AWS tr files")
parser.add_argument("--output", "-o", required=True, type=str)
parser.add_argument("--holdout", "-H", required=False, type=str)
parser.add_argument("--holdout_fraction", "-F", required=False, type=float, default=0.05)
parser.add_argument("sources", nargs='+')
args = parser.parse_args()

fout = open(args.output, 'ab')
if args.holdout:
    hout = open(args.holdout, 'ab')
else:
    hout = None

def process(path):
    num_held = 0
    num_copied = 0
    if os.path.isdir(path):
	for sub in sorted(os.listdir(path)):
            nh, nc = process(os.path.join(path, sub))
            num_held += nh
            num_copied += nc
	return num_held, num_copied
    elif os.path.isfile(path):
        use_holdout = False
        if hout and random.random() < args.holdout_fraction:
            use_holdout = True

	with open(path, "rb") as f:
	    while True:
		b = f.read(naf.LearningState.NUM_BYTES)
		if len(b) == 0:
		    break
		elif len(b) < naf.LearningState.NUM_BYTES:
		    print >>sys.stderr, "%s: odd lot ignored" % (path)
		    break

                if use_holdout:
                    hout.write(b)
                    num_held += 1
                else:
                    fout.write(b)
                    num_copied += 1
	os.unlink(path)
	return num_held, num_copied
    else:
	return 0, 0

for path in args.sources:
    nh, nc = process(path)
    print "from %s, %d row[s] held, %d copied" % (path, nh, nc)

fout.close()
if hout:
    hout.close()
