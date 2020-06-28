import os
import random

import twixt

class Player:
    def __init__(self, **kwargs):
	self.seed = int(kwargs.get('seed', int(os.urandom(4).encode('hex'), 16)))
	self.rng = random.Random(self.seed)
	print "seed is %d" % (self.seed)

    def pick_move(self, twixt):
	lp = twixt.legal_plays()
	return lp.pick(self.rng)
