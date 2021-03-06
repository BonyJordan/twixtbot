#! /usr/bin/env python
import numpy
import random
import tensorflow as tf

import naf

class NNEvaluater:
    def __init__(self, model):
	self.model = model

	if self.model[-3:] == ".pb":
	    with tf.gfile.GFile(self.model, "rb") as f:
		graph_def = tf.GraphDef()
		graph_def.ParseFromString(f.read())

	    with tf.Graph().as_default() as graph:
		tf.import_graph_def(graph_def, name="mynn")
	    prefix = "mynn/"
	    self.sess = tf.Session(graph=graph)

	else:
	    self.sess = tf.Session()
	    saver = tf.train.import_meta_graph(self.model + ".meta")
	    saver.restore(self.sess, self.model)
	    graph = tf.get_default_graph()
	    prefix = ""

	self.pegx_t = graph.get_tensor_by_name(prefix + "pegx:0")
	self.linkx_t = graph.get_tensor_by_name(prefix + "linkx:0")
	self.locx_t = graph.get_tensor_by_name(prefix + "locx:0")
	self.pwin_t = graph.get_tensor_by_name(prefix + "pwin:0")
	self.movelogits_t = graph.get_tensor_by_name(prefix + "movelogits:0")
	try:
	    self.is_training_t = graph.get_tensor_by_name(prefix + "is_training:0")
	except KeyError:
	    self.is_training_t = None

	self.use_recents = (int(self.locx_t.shape[3]) == 3)

    def pwin_size(self):
        if self.pwin_t.shape[1] == 1:
            return 1
        elif self.pwin_t.shape[1] == 3:
            return 3
        else:
            return ValueError("Weird pwin shape!")

    def eval_many(self, nips):
	""" Take a list of nips, evaluate them, and return an array of pwins
	    and movelogitses """
	pegs, links, locs = self.eval_many_prepare(nips)
	return self.eval_many_doit(pegs, links, locs)

    def eval_many_prepare(self, nips):
	""" Take a list of nafs, and turn it into three identical sized arrays
	    of pegs, links, rots. """
	pegs = []
	links = []
        locs = []

	for n in nips:
	    p, l, lx = n.to_input_arrays(self.use_recents)
	    pegs.append(p)
	    links.append(l)
            locs.append(lx)

	return pegs, links, locs

    def eval_many_doit(self, pegs, links, locs):
	feed_dict = {self.pegx_t:pegs, self.linkx_t:links, self.locx_t: locs}
	if self.is_training_t is not None:
	    feed_dict[self.is_training_t] = False

	return self.sess.run([self.pwin_t,  self.movelogits_t], feed_dict=feed_dict)


    def eval_one(self, nip):
	pegs, links, locs = nip.to_input_arrays(self.use_recents)

	feed_dict = {self.pegx_t:[pegs], self.linkx_t:[links], self.locx_t: [locs]}
	if self.is_training_t is not None:
	    feed_dict[self.is_training_t] = False
	return self.sess.run([self.pwin_t,  self.movelogits_t], feed_dict=feed_dict)
