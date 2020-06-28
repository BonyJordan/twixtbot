#! /usr/bin/env python
import argparse
import numpy
import tensorflow as tf

import twixt

parser = argparse.ArgumentParser()
parser.add_argument('--output', '-o', type=str, required=True)
parser.add_argument('--conv_filters', type=int, default=32)
parser.add_argument('--conv_layers', type=int, default=1)
parser.add_argument('--fc_filters', type=int, default=32)
parser.add_argument('--pwin_filters', type=int, default=32)
parser.add_argument('--normalization_constant', type=float, default=1e-4)
args = parser.parse_args()

def nngraph(pegx, linkx, locx, num_conv_filters, num_fc_filters, num_pwin_filters, num_conv_layers):
    S = twixt.Game.SIZE
    N = S * S * num_conv_filters
    allvars = []

    with tf.name_scope("location"):
	W_location = weight_variable([1, 1, 2, num_conv_filters])
	allvars.append(W_location)
	c_location = conv2d(locx, W_location)

    with tf.name_scope("pegs"):
	W_pegs = weight_variable([5, 5, 2, num_conv_filters])
	allvars.append(W_pegs)
	c_pegs = conv2d(pegx, W_pegs)

    with tf.name_scope("links"):
	W_links = weight_variable([4, 4, 8, num_conv_filters])
	allvars.append(W_links)
	c_links = conv2d(linkx, W_links)
    
    with tf.name_scope("first"):
	b_first = bias_variable([num_conv_filters])
	allvars.append(b_first)
	h_first = tf.nn.relu6(c_location + c_pegs + c_links + b_first)

    h_prev_layer = h_first
    for i in range(num_conv_layers):
	with tf.name_scope("conv_layer_" + str(i)):
	    W_layer = weight_variable([5, 5, num_conv_filters, num_conv_filters])
	    allvars.append(W_layer)
	    c_layer = conv2d(h_prev_layer, W_layer)
	    b_layer = bias_variable([num_conv_filters])
	    allvars.append(b_layer)
	    h_prev_layer = tf.nn.relu6(c_layer + b_layer)

    flat_layer = tf.reshape(h_prev_layer, [-1, N])

    with tf.name_scope("fc"):
	W_fc_first = weight_variable([N, num_fc_filters])
	allvars.append(W_fc_first)
	b_fc = bias_variable([num_fc_filters])
	allvars.append(b_fc)

	h_fc = tf.nn.relu6(tf.matmul(flat_layer, W_fc_first) + b_fc)

    with tf.name_scope("pwin") as scope:
	W_pwin = weight_variable([num_fc_filters, num_pwin_filters])
	allvars.append(W_pwin)
	b_pwin = bias_variable([num_pwin_filters])
	allvars.append(b_pwin)
	h_pwin_pre = tf.nn.relu6(tf.matmul(h_fc, W_pwin) + b_pwin)
	W_pfinal = weight_variable([num_pwin_filters, 1])
	b_pfinal = bias_variable([1])
	h_pwin = tf.tanh(tf.matmul(h_pwin_pre, W_pfinal) + b_pfinal, name=scope)

    with tf.name_scope("movelogits") as scope:
	M = (twixt.Game.SIZE - 2) * twixt.Game.SIZE
	W_movelogits = weight_variable([num_fc_filters, M])
	allvars.append(W_movelogits)
	b_movelogits = bias_variable([M])
	allvars.append(b_movelogits)
	h_movelogits = tf.add(tf.matmul(h_fc, W_movelogits), b_movelogits, name=scope)

    with tf.name_scope("norm"):
	norm = 0
	for wvec in allvars:
	    norm += tf.nn.l2_loss(wvec)
	norm = tf.identity(norm, name="norm")

    return h_pwin, h_movelogits, norm, allvars


def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)

def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1,1,1,1], padding='SAME')


c_norm = args.normalization_constant
pegx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, 2], name='pegx')
linkx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, 8], name='linkx')
locx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, 2], name='locx')
pwin_ = tf.placeholder(tf.float32, [None, 1], name='pwin_')
pmove_ = tf.placeholder(tf.float32, [None, (twixt.Game.SIZE * (twixt.Game.SIZE - 2))], name='pmove_')

pwin, movelogits, norm, allvars = nngraph(pegx, linkx, locx, args.conv_filters,
    args.fc_filters, args.pwin_filters, args.conv_layers)

with tf.name_scope('loss'):
    l1 = tf.nn.softmax_cross_entropy_with_logits_v2(labels=pmove_, logits=movelogits)
    l2 = tf.squared_difference(pwin_, pwin)
    l3 = c_norm * norm
    loss = l1 + l2 + l3
loss = tf.reduce_mean(loss, name="total_loss")

with tf.name_scope('optimizer'):
    lr = tf.placeholder(tf.float32, shape=[], name="learning_rate")
    # mom = tf.placeholder(tf.float32, shape=[], name="momentum")
    gs = tf.Variable(0, name='global_step', trainable=False)
    train_step = tf.train.GradientDescentOptimizer(lr).minimize(loss, global_step=gs)
    tf.add_to_collection("optimizer", train_step)

with tf.name_scope('summary'):
    tf.summary.scalar('l1', tf.reduce_mean(l1))
    tf.summary.scalar('l2', tf.reduce_mean(l2))
    tf.summary.scalar('l3', tf.reduce_mean(l3))
    tf.summary.scalar('loss', tf.reduce_mean(loss))

with tf.Session() as sess:
    saver = tf.train.Saver()
    sess.run(tf.global_variables_initializer())
    saver.save(sess, args.output, global_step=gs)
