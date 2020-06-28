#! /usr/bin/env python
import argparse
import bisect
import collections
import numpy
import os
import random
import re
import sys
import tempfile
import tensorflow as tf
from tensorflow.python import debug as tf_debug

import naf
import nnmcts
import twixt
import wrs

parser = argparse.ArgumentParser()
parser.add_argument('--model', '-m', type=str, required=True)
parser.add_argument('--batch_size', '-b', type=int, default=256)
parser.add_argument('--num_batches', '-n', type=int, default=1000)
parser.add_argument('--learning_rate', '-L', type=float, default=0.01)
parser.add_argument('--decay_rate', '-D', type=float, default=1.0)
parser.add_argument('--temperature', '-t', type=float, default=0.5)
parser.add_argument('--policy_epsilon', '-P', type=float, default=0.01)
parser.add_argument('--save_after', '-S', type=int, default=0)
parser.add_argument('--holdout', '-H', type=str, required=False)
parser.add_argument('--holdout_fraction', '-F', type=float, default=1.0)
parser.add_argument('--debug', action='store_true')
# parser.add_argument('--momentum', '-M', type=float, default=0.9)
parser.add_argument('spfiles', metavar='S', type=str, nargs='+', help='a file with selfplay binary logs')
args = parser.parse_args()

print "get our current neural net"
ix = args.model.rfind('/')
if ix == -1:
    model_dir = "./"
else:
    model_dir = args.model[:ix]
print "model_dir is", model_dir
ix = args.model.find('-')
if ix == -1:
    model_name = args.model
else:
    model_name = args.model[:ix]
print "model_name is", model_name

sess = tf.Session()

saver = tf.train.import_meta_graph(args.model + ".meta")
saver.restore(sess, args.model)

if args.debug:
    sess = tf_debug.LocalCLIDebugWrapperSession(sess, log_usage=False)

graph = tf.get_default_graph()
pegx = graph.get_tensor_by_name("pegx:0")
linkx = graph.get_tensor_by_name("linkx:0")
locx = graph.get_tensor_by_name("locx:0")
loss = graph.get_tensor_by_name("total_loss:0")
l1 = graph.get_tensor_by_name("total_l1:0")
l2 = graph.get_tensor_by_name("total_l2:0")
l3 = graph.get_tensor_by_name("total_l3:0")
movelogits = graph.get_tensor_by_name("movelogits:0")
pwin_ = graph.get_tensor_by_name("pwin_:0")
pmove_ = graph.get_tensor_by_name("pmove_:0")

train_step = graph.get_collection("optimizer")[0]
try:
    learning_rate = graph.get_tensor_by_name("optimizer/learning_rate:0")
except KeyError:
    learning_rate = graph.get_tensor_by_name("learning_rate:0")

# momentum = graph.get_tensor_by_name("optimizer/momentum:0")
global_step = graph.get_tensor_by_name("optimizer/global_step:0")
try:
    is_training = graph.get_tensor_by_name("is_training:0")
except KeyError:
    is_training = None

class FileInfo:
    def __init__(self, filename):
	self.name = filename
	stat = os.stat(filename)
	self.count = stat.st_size // naf.LearningState.NUM_BYTES
	self.f = open(filename, "rb")

weight_re = re.compile("w=([0-9]*\.?[0-9]+)")

def load_selector(selector, name):
    num_files = 0
    num_rows = 0

    mo = weight_re.match(fn)
    if mo:
	selector.set_default_weight(float(mo.group(1)))
	return 0, 0
    if os.path.isdir(name):
	for sub in os.listdir(name):
	    f, r = load_selector(selector, os.path.join(name, sub))
	    num_files += f
	    num_rows += r
    elif os.path.isfile(name):
	fi = FileInfo(name)
	selector.add_basket(fi.count, obj=fi)
	num_files += 1
	num_rows += fi.count

    return num_files, num_rows


if args.num_batches > 0:
    selector = wrs.WeightedRandomSelector()
    num_files = 0
    num_rows = 0
    for fn in args.spfiles:
        f, r = load_selector(selector, fn)
        num_files += f
        num_rows += r

    print "scanned: #files=%d  #rows=%d" % (num_files, num_rows)
else:
    print "no files scanned, #batches = 0"

def collect_one_train_state():
    while True:
	bnum, y, fi = selector.random_item()
	assert y >= 0 and y < fi.count, (y, fi)
	fi.f.seek(y*naf.LearningState.NUM_BYTES)
	b = fi.f.read(naf.LearningState.NUM_BYTES)
	assert len(b) == naf.LearningState.NUM_BYTES
	ts = naf.LearningState.from_bytes(b, "%s:%d" % (fi.name, y))
	if ts.N.any():
	    r = random.randint(0, 3)
	    ts.nips.rotate(r)
	    ts.N = naf.rotate_policy_array(ts.N, r)
	    return ts
    # end collect_one_train_state()


S = twixt.Game.SIZE
peg_batch = numpy.zeros((args.batch_size, S, S, 2))
link_batch = numpy.zeros((args.batch_size, S, S, 8))
loc_batch = numpy.zeros((args.batch_size, S, S, int(locx.shape[3])))
pmove_batch = numpy.zeros((args.batch_size, S*(S-2)))
pwin_batch = numpy.zeros((args.batch_size, 1))

prev_loss = None
current_rate = args.learning_rate

def load_tensor_data(index, ls):
    pegs, links, locs = ls.nips.to_input_arrays(loc_batch.shape[3] == 3)

    peg_batch[index,:,:,:] = pegs
    link_batch[index,:,:,:] = links
    loc_batch[index,:,:,:] = locs

    if args.temperature == 0.5:
        nup = numpy.square(ls.N.astype(numpy.float32))
    elif args.temperature == 0.0:
        nup = numpy.where(ls.N == ls.N.max(), 1.0, 0.0)
    elif args.temperature == 1.0:
        nup = ls.N.astype(numpy.float32)
    else:
        raise ValueError("Bad temperature")

    nsum = nup.sum()
    assert nsum > 0, (nsum, ls.name)
    nup /= nsum
    if args.temperature == 0 and args.policy_epsilon > 0:
        nup += args.policy_epsilon
        nup /= nup.sum()

    pmove_batch[index,:] = nup
    pwin_batch[index,0] = ls.z



def read_from_holdout(name):
    if os.path.isdir(name):
	for sub in os.listdir(name):
	    for x in read_from_holdout(os.path.join(name, sub)):
                yield x
    elif os.path.isfile(name):
        lsnb = naf.LearningState.NUM_BYTES
        with open(name, "rb") as f:
            all_bytes = f.read()
        for i in range(len(all_bytes) // lsnb):
            yield naf.LearningState.from_bytes(all_bytes[i*lsnb:(i+1)*lsnb],
                "%s:%d" % (name, i))


def group_from_holdout(rng, fraction):
    i = 0
    for ls in read_from_holdout(args.holdout):
        if rng.random() < fraction:
            continue
        load_tensor_data(i, ls)
        i += 1
        if i == args.batch_size:
            i = 0
            yield

holdout_seed = int(os.urandom(4).encode('hex'), 16)

def test_vs_holdout(seed, fraction):
    rng = random.Random(seed)
    mean_loss = 0.0
    mean_l1 = 0.0
    mean_l2 = 0.0
    mean_l3 = 0.0
    n = 0

    for _ in group_from_holdout(rng, fraction):
        with sess.as_default():
            fd = dict()
            fd[pegx] = peg_batch
            fd[linkx] = link_batch
            fd[locx] = loc_batch
            fd[pwin_] = pwin_batch
            fd[pmove_] = pmove_batch
            fd[learning_rate] = current_rate
            if is_training is not None:
                fd[is_training] = False
            # fd[momentum] = args.momentum
            loss_value, l1_val, l2_val, l3_val = sess.run([loss, l1, l2, l3], feed_dict=fd)

            n += 1
            mean_loss += (loss_value - mean_loss) / n
            mean_l1 += (l1_val - mean_l1) / n
            mean_l2 += (l2_val - mean_l2) / n
            mean_l3 += (l3_val - mean_l3) / n

    print "holdout %d batch%s" % (n, "es" if n != 1 else "")
    print "loss=%g  (l1=%g l2=%g l3=%g)" % (mean_loss, mean_l1, mean_l2,  mean_l3)
	

# Only at the end?
if args.holdout:
   test_vs_holdout(holdout_seed, args.holdout_fraction)

XX = numpy.zeros((2,2))
XY = numpy.zeros(2)

for b in range(args.num_batches):
    print "batch %d" % b
    batch_items = [collect_one_train_state() for i in range(args.batch_size)]

    for i, ts in enumerate(batch_items):
        load_tensor_data(i, ts)

    with sess.as_default():
	fd = dict()
	fd[pegx] = peg_batch
	fd[linkx] = link_batch
	fd[locx] = loc_batch
	fd[pwin_] = pwin_batch
	fd[pmove_] = pmove_batch
	fd[learning_rate] = current_rate
	if is_training is not None:
	    fd[is_training] = True
	# fd[momentum] = args.momentum
	_, loss_value, l1_val, l2_val, l3_val = sess.run([train_step, loss, l1, l2, l3], feed_dict=fd)
	x = numpy.array([1, b])
	y = loss_value
	XX += numpy.outer(x, x)
	XY += x*y
	if b > 2:
	    betas = numpy.linalg.solve(XX, XY)
	    print "loss_value = %g  slope=%g" % (loss_value, betas[1])
	else:
	    print "loss_value = %g" % (loss_value)
	print "l1=%g l2=%g l3=%g" % (l1_val, l2_val, l3_val)
	if prev_loss and loss_value > prev_loss:
	    current_rate *= args.decay_rate
	    print "reduce learning to %g" % (current_rate)
	prev_loss = loss_value
	if args.save_after and (b+1) % args.save_after == 0:
	    print "save it"
	    saver.save(sess, model_name, global_step=global_step)
	sys.stdout.flush()

if args.num_batches > 0:
    with sess.as_default():
        print "save it"
        saver.save(sess, model_name, global_step=global_step)

    # we already tested vs. holdout once at the start
    if args.holdout:
       test_vs_holdout(holdout_seed, args.holdout_fraction)
