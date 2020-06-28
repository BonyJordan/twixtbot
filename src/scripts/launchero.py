#! /usr/bin/env python
import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser("Get an AWS Instance Doing Stuff")
parser.add_argument("--remote_host", "-r", required=True, type=str)
args = parser.parse_args()

log = os.path.join("/data/twixt/log/launch", args.remote_host)
log_f = open(log, "w")
os.dup2(log_f.fileno(), 1)
os.dup2(log_f.fileno(), 2)
sys.stdin.close()
os.close(0)

home = os.environ["HOME"]
user_host = "ec2-user@" + args.remote_host
ssh_ident = os.path.join(home, ".ssh/aws-twixy.pem")

def runit(cmd, check=True):
    print " ".join(cmd)
    sys.stdout.flush()
    if check:
	return subprocess.check_call(cmd)
    else:
	return subprocess.call(cmd)


runit(["scp", "-i", ssh_ident,
    "-o", "StrictHostKeyChecking=no",
    "-p", "etc/aws_ssh_config", user_host + ":.ssh/config"])

runit(["ssh", "-i", ssh_ident, user_host, "rm", "-rf", "deeptwixt"])
runit(["ssh", "-i", ssh_ident, user_host, "git", "clone",
    "izu.jyjy.org:/Users/jordan/Gits/deeptwixt"])
runit(["ssh", "-i", ssh_ident, user_host, "sh", "deeptwixt/scripts/aws_cycle.sh"])
