#! /usr/bin/env python
import numpy
import socket

import naf
import twixt
import smmpp


class Resource:
    def __init__(self, **kwargs):
	self.location = kwargs.get('location')
	self.slots = int(kwargs.get('slots', 1))
	self.name = kwargs.get('name')
	self.client = smmpp.Client(self.location, self.slots)

    def eval(self, nips):
	if not isinstance(nips, naf.NetInputs):
	    raise TypeError("Refactored to take NetInputs")
	outbytes = nips.to_expanded_bytes()

	def set_reply(reply):
	    self.reply = reply

	self.client.write_query(outbytes, set_reply)
	self.client.handle_read()

	p0 = numpy.frombuffer(self.reply, dtype=numpy.float32)
	assert p0.shape[0] == (twixt.Game.SIZE-1)**2
	pwin = p0[0]
	movelogits = p0[1:]
	return pwin, movelogits
