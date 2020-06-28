#! /usr/bin/env python
import argparse
import numpy
import tensorflow as tf

import jtf
import twixt

parser = argparse.ArgumentParser()
parser.add_argument('--output', '-o', type=str, required=True)
parser.add_argument('--Optimizer', '-O', type=str, required=True)
parser.add_argument('--num_conv_filters', type=int, default=40)
parser.add_argument('--num_tower_blocks', type=int, default=12)
parser.add_argument('--num_pwin_hidden', type=int, default=80)
parser.add_argument('--normalization_constant', type=float, default=1e-4)
parser.add_argument('--pwin_constant', type=float, default=1.0)
parser.add_argument('--use_recent_moves', action='store_true')
parser.add_argument('--pwin_conv_padding', type=str, default='VALID')
parser.add_argument('--pwin_reductions', type=int, default=2)
parser.add_argument('--pwin_triple', action='store_true')
parser.add_argument('--init_stdev', type=float, default=0.001)
args = parser.parse_args()

S = twixt.Game.SIZE

def my_relu(x):
    return tf.abs(x)

def num_location_planes():
    if args.use_recent_moves:
        return 3
    else:
        return 2

def primary_layer(pegx, linkx, locx):
    with tf.name_scope("primary_location"):
	W_location = weight_variable([1, 1, num_location_planes(), args.num_conv_filters])
	c_location = conv2d(locx, W_location)

    with tf.name_scope("primary_pegs"):
	W_pegs = weight_variable([5, 5, 2, args.num_conv_filters])
	c_pegs = conv2d(pegx, W_pegs)

    with tf.name_scope("primary_links"):
	W_links = weight_variable([4, 4, 8, args.num_conv_filters])
	c_links = conv2d(linkx, W_links)

    with tf.name_scope("primary"):
	h1 = c_location + c_pegs + c_links
	h2 = batch_norm(h1)
	return my_relu(h2)

def residual_block(h0):
    W1 = weight_variable([5, 5, args.num_conv_filters, args.num_conv_filters])
    h1 = conv2d(h0, W1)
    h2 = batch_norm(h1)
    h3 = my_relu(h2)
    W4 = weight_variable([5, 5, args.num_conv_filters, args.num_conv_filters])
    h4 = conv2d(h3, W4)
    h5 = batch_norm(h4)
    # let's try relu then add??
    h6 = my_relu(h5)
    return h6 + h0
    # h6 = h5 + h0
    # return my_relu(h6)



def weight_variable(shape):
    return tf.Variable(tf.random_normal(shape, stddev=args.init_stdev))

def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1,1,1,1], padding='SAME')

def batch_norm(h):
    # return jtf.jordan_batch_norm(h)

    # old
    return tf.contrib.layers.batch_norm(h, center=True, scale=True,
    	    decay=bn_decay, is_training=is_training)


def policy_head(h):
    with tf.name_scope('movelogits') as scope:
	W1 = weight_variable([1, 1, args.num_conv_filters, 2])
	h1 = conv2d(h, W1)
	h2 = batch_norm(h1)
	h3 = my_relu(h2)
	W2 = weight_variable([1, 1, 2, 1])
	h4 = conv2d(h3, W2)
	h5 = tf.reshape(h4[:,1:-1,:,0], shape=[-1, (twixt.Game.SIZE-1)**2-1], name=scope)
	return h5

def value_head(h):
    with tf.name_scope('pwin') as scope:
        hin = h
        for i in range(args.pwin_reductions):
            W = weight_variable([5, 5, args.num_conv_filters, args.num_conv_filters])
            h1 = tf.nn.conv2d(hin, W, strides=[1,2,2,1], padding=args.pwin_conv_padding)
            h2 = batch_norm(h1)
            hin = my_relu(h2)

        h6 = hin
	h7 = tf.contrib.layers.flatten(h6)
	W3 = weight_variable([h7.shape[1].value, args.num_pwin_hidden])
	h8 = tf.matmul(h7, W3)
	h9 = batch_norm(h8)
	h10 = my_relu(h9)
        if args.pwin_triple:
            W4 = weight_variable([args.num_pwin_hidden, 3])
            return tf.matmul(h10, W4, name=scope)
        else:
            W4 = weight_variable([args.num_pwin_hidden, 1])
            h11 = tf.matmul(h10, W4)
            return tf.tanh(h11, name=scope)


c_norm = args.normalization_constant
pegx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, 2], name='pegx')
linkx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, 8], name='linkx')
locx = tf.placeholder(tf.float32, [None, twixt.Game.SIZE, twixt.Game.SIZE, num_location_planes()], name='locx')
if args.pwin_triple:
    pwin3_ = tf.placeholder(tf.float32, [None, 3], name='pwin3_')
else:
    pwin_ = tf.placeholder(tf.float32, [None, 1], name='pwin_')
pmove_ = tf.placeholder(tf.float32, [None, (twixt.Game.SIZE * (twixt.Game.SIZE - 2))], name='pmove_')
learning_rate = tf.placeholder(tf.float32, shape=[], name="learning_rate")
is_training = tf.placeholder(tf.bool, shape=[], name="is_training")
bn_decay = 1.0 - learning_rate

h = primary_layer(pegx, linkx, locx)
for i in range(args.num_tower_blocks):
    with tf.name_scope('block' + str(i)):
	h = residual_block(h)

pwin = value_head(h)
movelogits = policy_head(h)
print "pwin=",pwin
print "movelogits=",movelogits


with tf.name_scope('loss'):
    norm = 0
    for v in tf.trainable_variables():
	norm = norm + tf.nn.l2_loss(v)
    l1 = tf.nn.softmax_cross_entropy_with_logits_v2(labels=pmove_, logits=movelogits, name="l1")
    if args.pwin_triple:
        l2 = tf.nn.softmax_cross_entropy_with_logits_v2(labels=pwin3_, logits=pwin, name = "l2")
    else:
        l2 = args.pwin_constant * tf.squared_difference(pwin_, pwin, name="l2")
    l3 = tf.multiply(c_norm, norm, name="l3")
    loss = l1 + l2 + l3
loss = tf.reduce_mean(loss, name="total_loss")
tf.reduce_mean(l1, name="total_l1")
tf.reduce_mean(l2, name="total_l2")
tf.reduce_mean(l3, name="total_l3")

update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)

with tf.name_scope('optimizer'):
    lr = learning_rate
    gs = tf.Variable(0, name='global_step', trainable=False)
    with tf.control_dependencies(update_ops):
	if args.Optimizer == "ADAM":
	    train_step = tf.train.AdamOptimizer(lr).minimize(loss, global_step=gs)
	elif args.Optimizer == "SGD":
	    train_step = tf.train.GradientDescentOptimizer(lr).minimize(loss, global_step=gs)
	else:
	    raise ValueError("Unexpected Optimizer", args.Optimizer)
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
