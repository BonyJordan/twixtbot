#! /usr/bin/env python
import os
import subprocess
import sys

if len(sys.argv) != 2:
    print >>sys.stderr, "usage:",sys.argv[0],"directory"
    sys.exit(1)

dirname = sys.argv[1]
if not os.path.isdir(dirname):
    print >>sys.stderr, dirname, "is not a directory."

assert dirname[-1] != '/'
filename = dirname + ".tr"
f = open(filename, "wb")
cmd1 = ["./cattrain.py", dirname]
print " ".join(cmd1),">output-to>", filename
subprocess.check_call(cmd1, stdout=f)
f.close()

cmd2 = ["rm", "-rf", dirname]
print " ".join(cmd2)
subprocess.check_call(cmd2)
