#! /usr/bin/env python
""" Neural Net Server """
# python
import argparse
import numpy
import sys

# mine
import naf
import nneval
import smmpp
import twixt

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--location", type=str, required=True)
parser.add_argument("-m", "--model", type=str, required=False)
parser.add_argument("-k", "--kill", action='store_true')
parser.add_argument("-c", "--capacity", type=int, default=200)
parser.add_argument("--milestone_step", type=int, default=10000)
args = parser.parse_args()

if args.kill:
    c = smmpp.Client(args.location, smmpp.SUICIDE_CODE)
    sys.exit(0)

if args.model is None:
    with open("/data/twixt/models/best", "r") as f:
        model = f.read().strip()
        print "Model is:", model
else:
    model = args.model

ne = nneval.NNEvaluater(model)

class NNServer(smmpp.Server):
    def run_jobs(self, jobs):
        nips = map(naf.NetInputs, jobs)
        pegs, links, locs = ne.eval_many_prepare(nips)
        pws, mls = ne.eval_many_doit(pegs, links, locs)
        outs = []
        for i in range(len(jobs)):
            b = numpy.array([pws[i]], dtype=numpy.float32).tostring()
            b += mls[i].astype(numpy.float32).tostring()
            outs.append(b)
        return outs


server = NNServer(args.location, args.capacity, naf.NetInputs.EXPANDED_SIZE,
    4*(twixt.Game.SIZE-1)**2, args.milestone_step)
server.run()
