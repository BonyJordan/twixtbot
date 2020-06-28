#! /usr/bin/env python
import numpy
import time

class TimeStat:
    def __init__(self, name="timer", ignore=None):
	self.name = name
	self.total_count = 0
	self.total_time = 0
	self.start_time = None
	self.ignore = ignore

    def start(self):
	assert self.start_time == None
	self.start_time = time.time()

    def stop(self):
	assert self.start_time != None
	time_taken = time.time() - self.start_time
	if not self.ignore or time_taken < self.ignore:
	    self.total_time += time.time() - self.start_time
	    self.total_count += 1
	self.start_time = None

    def total_count(self):
	return self.total_count

    def total_time(self):
	return self.total_time

    def __str__(self):
	return "%s: N=%d T=%6g avg=%.6f" % (self.name, self.total_count, self.total_time, self.total_time/self.total_count)

class WorkTimeStat:
    def __init__(self, name="timer"):
	self.name = name
	self.XX = numpy.zeros((2,2))
	self.XY = numpy.zeros(2)
	self.start_time = None

    def start(self, work):
	assert self.start_time == None
	self.start_time = time.time()
	self.work = work

    def stop(self):
	assert self.start_time != None
	y = time.time() - self.start_time
	x = numpy.array([1., self.work])
	self.XX += numpy.outer(x, x)
	self.XY += x*y
	self.start_time = None

    def total_count(self):
	return self.XX[0,0]

    def total_work(self):
	return self.XX[0,1]

    def total_time(self):
	return self.XY[0]

    def __str__(self):
	N = self.total_count()
	T = self.total_time()
	W = self.total_work()
	try:
	    betas = numpy.linalg.solve(self.XX, self.XY)
	except numpy.linalg.linalg.LinAlgError:
	    return "%s: N=%d T=%6g W=%8g  matrix error" % (self.name, N, T, W)
	return "%s: N=%d T=%6g W=%8g avg=%.6f + %.6f*W" % (self.name, N, T, W, betas[0], betas[1])
