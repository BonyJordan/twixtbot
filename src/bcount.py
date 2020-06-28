#! /usr/bin/env python
from collections import defaultdict
import re
import os
import subprocess
import sys

if len(sys.argv) <= 1:
    print >>sys.stderr, "usage:",sys.argv[0],"directory [...]"
    sys.exit(1)

pattern = re.compile(": *(\d+.[05]) \(.*\) ([^ ]+)")
scores = defaultdict(float)

def do_dir(dname):
    for name in os.listdir(dname):
	fullpath = os.path.join(dname, name)
	if not os.path.isfile(fullpath):
	    continue

	with open(fullpath, "r") as f:
	    matches = []
	    for line in f:
		mo = pattern.match(line.strip())
		if mo:
		    matches.append(mo)

	    if len(matches) >= 2:
		for i in [-2, -1]:
		    mo = matches[i]
		    score = float(mo.group(1))
		    name = mo.group(2)
		    scores[name] += score

for d in sys.argv[1:]:
    do_dir(d)

for k, v in scores.items():
    print k, v
