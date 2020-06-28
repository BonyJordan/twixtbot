#! /usr/bin/env python
import argparse
from collections import namedtuple
import datetime
import os
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--num_clones", "-n", type=int, required=True)
parser.add_argument("--log_dir", "-l", type=str, required=True)
parser.add_argument("cmdline", nargs='+')
args = parser.parse_args()

os.mkdir(args.log_dir)
master_log = os.path.join(args.log_dir, "master.log")
print "logging to %s" % (master_log)
log_f = open(master_log, 'w')
sys.stdout = log_f
sys.stderr = log_f

def mini_log10(n):
    assert n > 0
    k = 1
    while n >= 10:
	n //= 10
	k += 1
    return k

def when():
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d %H:%M:%S")

def search_replace_cmd(org_cmdline, name):
    return [x.replace("%n%", name) for x in org_cmdline]

num_digits = mini_log10(max(1,args.num_clones - 1))
sys.stdin.close()
os.close(0)

ProcInfo = namedtuple('ProcInfo', ['p', 'id', 'fileobj'])
procmap = dict()

for i in range(args.num_clones):
    print "start instance #%d" % i
    sys.stdout.flush()
    name = "%0*d" % (num_digits, i)
    outfile = os.path.join(args.log_dir, name + ".log")
    f = open(outfile, 'w')
    cmd = search_replace_cmd(args.cmdline, name)
    p = subprocess.Popen(cmd, stdout=f, stderr=f)
    proc = ProcInfo(p, i, f)
    procmap[p.pid] = proc

while procmap:
    if len(procmap) % 5 == 0:
	print "remaining jobs:", " ".join(["%0*d" % (num_digits, proc.id) for proc in sorted(procmap.values(), key=lambda x: x.id)])

    (pid, status) = os.wait()
    proc = procmap[pid]
    signum = status & 0xff
    xcode = (status >> 8) & 0xff
    if signum:
	print when(), "instance %d exited with signal %d" % (proc.id, signum)
    elif xcode:
	print when(), "instance %d exited with status %d" % (proc.id, xcode)
    else:
	print when(), "instance %d finished happily" % (proc.id)
    sys.stdout.flush()

    proc.p.wait()
    proc.fileobj.close()
    del procmap[pid]


print when(), "all instances finished."
log_f.close()
