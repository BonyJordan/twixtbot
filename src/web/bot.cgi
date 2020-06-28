#! /usr/bin/python
import cgi
import cgitb
import subprocess
import sys

cgitb.enable(logdir="/tmp/cgitb.err")

form = cgi.FieldStorage()
moves = form.getvalue("moves")
bot = form.getvalue("bot")

print "Content-Type: text/html"
print

proc = subprocess.Popen(["nc", "-U", "/tmp/bs"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = proc.communicate(moves)
if err:
    print err
else:
    print out
