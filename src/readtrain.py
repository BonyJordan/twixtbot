#! /usr/bin/env python
import argparse
import numpy

import naf
import twixt

parser = argparse.ArgumentParser()
parser.add_argument('--display', '-d', action='store_true')
parser.add_argument('positions', metavar='S', type=str, nargs='+', help='a file with selfplay binary logs')
args = parser.parse_args()

for p in args.positions:
    colon = p.find(':')
    if colon == -1:
	raise Exception("Required position format <file>:<index>")
    filename = p[:colon]
    index = int(p[colon+1:])

    f = open(filename, "rb")
    f.seek(index*naf.LearningState.NUM_BYTES)
    b = f.read(naf.LearningState.NUM_BYTES)
    ts = naf.LearningState.from_bytes(b)

    print "evaluation: %d" % (ts.z),
    for i in range(len(ts.N)):
	if i % 8 == 0:
	    print
	print "%3s:%-4d" % (naf.policy_index_point(twixt.Game.WHITE, i), ts.N[i]),
    print

    if args.display:
	import ui
	tb = ui.TwixtBoardWindow(p)
	tb.set_naf(ts.naf)
	tb.win.getMouse()
