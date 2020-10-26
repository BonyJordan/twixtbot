#! /usr/bin/env python
import bisect
import random

class WeightedRandomSelector:
    def __init__(self):
	self.total_weight = 0.0
	self.default_weight = 1.0
	self.cum_weights = [0.0]
	self.item_count = []
	self.item_objects = []

    def set_default_weight(self, dw):
	assert dw >= 0
	self.default_weight = dw

    def add_basket(self, count, obj=None, weight=None):
	if weight == None:
	    weight = self.default_weight

	self.total_weight += weight * count
	self.cum_weights.append(self.total_weight)
	self.item_count.append(count)
	self.item_objects.append(obj)

    def random_item(self):
	""" Picks a random item from the implicit lists added with add_basket().
	    Returns basket_number, index_within_basket, object """
	x = random.random() * self.total_weight
	i = bisect.bisect_right(self.cum_weights, x) - 1
	assert 0 <= i and i < len(self.item_count)
	y = (x - self.cum_weights[i]) / (self.cum_weights[i+1] - self.cum_weights[i])
	assert 0 <= y and y < 1
	inum = int(self.item_count[i] * y)
	return i, inum, self.item_objects[i]

if __name__ == "__main__":
    # debug it!
    wrs_ = WeightedRandomSelector()
    wrs_.add_basket(5, "a")
    wrs_.set_default_weight(0.7)
    wrs_.add_basket(4, "b")

    xp = dict()
    for i in range(5):
	xp["a" + str(i)] = 1.0 / 7.8
    for i in range(4):
	xp["b" + str(i)] = 0.7 / 7.8

    from collections import Counter
    ctr = Counter()
    N = 100000
    for k in range(N):
	i, j, obj = wrs_.random_item()
	ctr[obj + str(j)] += 1

    print "%5s  %8s  %8s" % ("label",  "expected", "actual")
    for label in sorted(xp.keys()):
	print "%5s  %8d  %8d" % (label, int(xp[label]*N+0.5), ctr[label])


