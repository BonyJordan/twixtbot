#! /usr/bin/env python
""" Shared Memory Message Passing Protocol """
# python
import argparse
import collections
import mmap
import multiprocessing
import os
import select
import socket
import struct
import sys

debug = False

# mine
import timestat

IntPacker = struct.Struct("<L")
QUERY_AVAILABLE = "QQ"
REPLY_AVAILABLE = "RR"
ANSWER_SENT = "SS"
SUICIDE_CODE = 0xdead3149

def checksum(b):
    return 0xcc
    # return reduce(lambda x,y:x^y, map(ord, b))

class Client:
    def __init__(self, location, slots_needed=1, quiet=False):
        self.quiet = quiet
	self._init_socket(location)
	self._init_shmem(location)
	self._request_slots(slots_needed)

	self.min_timeout = 0.001
	self.max_timeout = 3.0

    def _init_socket(self, location):
	sock_name = location + ".sock"
	self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	self.socket.connect(sock_name)

    def _init_shmem(self, location):
	shmem_name = location + ".shm"
	self.shm_file = open(shmem_name, "r+b")
	self.shmem = mmap.mmap(self.shm_file.fileno(), 0)

    def _request_slots(self, slots_needed):
	outdata = struct.pack("<L", slots_needed)
	if debug:
	    print >>sys.stderr, "Sent request for %d slot(s)" % (slots_needed)
	self.socket.send(outdata)

        if slots_needed == SUICIDE_CODE:
            return
	self.slots = []
	self.cb_by_slot = dict()

	# receive a message telling me the query_size, reply_size, and
	# slot indices I may use
	if debug:
	    print >>sys.stderr, "expecting %d bytes" % (4*(2+slots_needed))
	indata = self.socket.recv(4*(2+slots_needed), socket.MSG_WAITALL)
	if debug:
	    print >>sys.stderr, "received %d bytes" % (len(indata))
	self.query_size = IntPacker.unpack_from(indata, 0)[0]
	self.reply_size = IntPacker.unpack_from(indata, 4)[0]
	for i in range(slots_needed):
	    self.slots.append(IntPacker.unpack_from(indata, 8+i*4)[0])

	self.slot_size = 3 + max(self.query_size, self.reply_size)
	self.unused_slots = list(self.slots)

        if not self.quiet:
            print "query_size=",self.query_size,"reply_size=",self.reply_size,"my_slots=[",",".join(map(str,self.slots)),"]"
            sys.stdout.flush()
	# end _request_slots

    def slot_locations(self, slot):
	return slot*self.slot_size, (slot+1)*self.slot_size

    def is_full(self):
	return len(self.unused_slots) == 0


    def write_query(self, request, reply_callback):
	if not type(request) == str:
	    raise ValueError('queries must be bytes (strings)')
	if len(request) > self.query_size:
	    raise ValueError('query too long')
	if not self.unused_slots:
	    raise Exception('Too many queries!')

	slot = self.unused_slots.pop()
        if debug:
            print "POP",slot
	x, y = self.slot_locations(slot)
	self.shmem[x:x+len(request)] = request
	cs = checksum(request)
	self.shmem[y-3] = chr(cs)
	self.shmem[y-2:y] = QUERY_AVAILABLE
	if debug:
	    print >>sys.stderr, "client sent %d bytes with checksum %d" % (len(request), cs)
	self.cb_by_slot[slot] = reply_callback

    def handle_ready_replies(self):
	ready_slots = []
	for slot in self.cb_by_slot.keys():
	    x, y = self.slot_locations(slot)
	    status = self.shmem[y-2:y]
	    if status == REPLY_AVAILABLE:
		ready_slots.append(slot)

	for slot in ready_slots:
	    self.process_reply(slot)
	return len(ready_slots)


    def process_reply(self, slot):
	assert not slot in self.unused_slots, (slot, self.unused_slots)
	cb = self.cb_by_slot[slot]
	del self.cb_by_slot[slot]
	self.unused_slots.append(slot)
        if debug:
            print "PUSH",slot

	x, y = self.slot_locations(slot)
	replydata = bytes(self.shmem[x:x+self.reply_size])
	cs = checksum(replydata)
	if debug:
	    print >>sys.stderr, "client received %d bytes with checksum %d" % (len(replydata), cs)
	assert cs == ord(self.shmem[y-3])
	cb(replydata)

    def handle_read(self):
	""" Receive a message telling me which slots have finished replies """
	indata = self.socket.recv(4*len(self.slots))
	if debug:
	    print >>sys.stderr, "Client just read %d bytes", (len(indata))
	if len(indata) % 4 != 0:
	    raise Exception("odd number of bytes")
	if len(indata) == 0:
	    raise Exception("Server went away")

	for i in range(0, len(indata), 4):
	    slot = IntPacker.unpack_from(indata, i)[0]
	    self.process_reply(slot)


########################

class ServerSocketProcess(multiprocessing.Process):
    def __init__(self, location, capacity, query_size, reply_size, shmem, notify_pipe):
	multiprocessing.Process.__init__(self)
	# self.daemon = True
	self.location = location
	self.capacity = capacity
	self.query_size = query_size
	self.reply_size = reply_size
	self.slot_size = 3 + max(self.query_size, self.reply_size)
	self.shmem = shmem
	self.notify_pipe = notify_pipe

	self._init_socket()

	self.unused_slots = list(range(self.capacity))
	self.slot_user = dict()
	self.unallocated_sockets = []

    def _init_socket(self):
	self.socket_name = self.location + ".sock"
	if os.path.exists(self.socket_name):
	    os.remove(self.socket_name)

	self.main_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	self.main_socket.bind(self.socket_name)
	self.main_socket.listen(5)

	self.all_sockets = [self.main_socket, self.notify_pipe]
	print "Ready for connections on", self.socket_name
	sys.stdout.flush()

    def slot_locations(self, slot):
	return slot*self.slot_size, (slot+1)*self.slot_size

    def read_main_socket(self):
	new_sock, _ = self.main_socket.accept()
	self.all_sockets.append(new_sock)
	self.unallocated_sockets.append(new_sock)
	print "opened connection. cons=%d free_slots=%d" % (len(self.all_sockets)-1, len(self.unused_slots))
	sys.stdout.flush()


    def allocate_other_socket(self, sock):
	try:
	    # Receive the message requesting how many slots the client wants
	    indata = sock.recv(4, socket.MSG_WAITALL)
	    if len(indata) == 0:
		# counterparty left the house
		self.free_socket(sock)
		return
	    elif len(indata) != 4:
		print "error: want exactly 4 bytes for capacity request"
		sys.stdout.flush()
		self.free_socket(sock)
		return
	    assert sock in self.unallocated_sockets
	    self.unallocated_sockets.remove(sock)
	    desire = IntPacker.unpack(indata)[0]
            if desire == SUICIDE_CODE:
                print "suicide requested"
                sys.stdout.flush()
                self.notify_pipe.send("DIE")
                self.notify_pipe.close()
                self.main_socket.close()
                sys.exit(0)

	    if desire > len(self.unused_slots):
		print "error: more slots requested (%d) than available (%d)" % (desire, len(self.unused_slots))
		sys.stdout.flush()
		self.free_socket(sock)
		return

	    alloc_slots = [self.unused_slots.pop() for _ in range(desire)]
	    msg_ints = [self.query_size, self.reply_size] + alloc_slots
	    assert len(alloc_slots) == desire
	    assert len(msg_ints) == 2+desire
	    outdata = ''.join([IntPacker.pack(n) for n in msg_ints])
	    for slot in alloc_slots:
		self.slot_user[slot] = sock

	    sock.send(outdata)
	    print "%d slot%s allocated, %d unused, outdata len=%d" % (desire, "" if desire == 1 else "s", len(self.unused_slots), len(outdata))
	    sys.stdout.flush()
	except socket.error as serr:
	    print "error in sock.send() in allocate_other_socket():",serr
	    self.free_socket(sock)

	#end allocate_other_socket()


    def read_other_socket(self, sock):
	self.allocate_other_socket(sock)

    def free_socket(self, sock):
	if not sock in self.all_sockets:
	    print "attempt to re-close socket!"
	    return
	self.all_sockets.remove(sock)
	my_slots = [slot for slot, user in self.slot_user.items() if user == sock]
	for slot in my_slots:
	    self.unused_slots.append(slot)
	    del self.slot_user[slot]

	print "closed connection fielno=%d. conns=%d free_slots=%d" % (sock.fileno(), len(self.all_sockets)-1, len(self.unused_slots))
	sock.close()
	sys.stdout.flush()

    def send_out_replies(self):
	self.notify_pipe.recv_bytes()
	outs_by_socket = collections.defaultdict(list)
	for slot, sock in self.slot_user.items():
	    x, y = self.slot_locations(slot)
	    status = self.shmem[y-2:y]
	    if status == REPLY_AVAILABLE:
		outs_by_socket[sock].append(slot)
		self.shmem[y-2:y] = ANSWER_SENT

	for sock, outs in outs_by_socket.items():
	    outdata = ''.join([IntPacker.pack(n) for n in outs])
	    assert len(outdata) == 4*len(outs)
	    try:
		sock.send(outdata)
	    except socket.error as serr:
		print "error sock.send() fileno:",sock.fileno(),"error:",serr
		self.free_socket(sock)
	# send_out_replies

    def run(self):
	while True:
	    rd, _, _ = select.select(self.all_sockets, [], [])
	    for sock in rd:
		if sock == self.main_socket:
		    self.read_main_socket()
		elif sock == self.notify_pipe:
                    self.send_out_replies()
		else:
		    self.read_other_socket(sock)



class Server:
    def __init__(self, location, capacity, query_size, reply_size, milestone_step=0):
	self.location = location
	self.capacity = capacity
	self.query_size = query_size
	self.reply_size = reply_size
	self.slot_size = 3 + max(query_size, reply_size)
	self.next_milestone = milestone_step
	self.milestone_step = milestone_step
	self.min_timeout = 0.001
	# self.max_timeout = 0.064
	self.max_timeout = 1.0

	self._init_shmem()
	self._init_timers()

	print "query_size",query_size,"reply_size",reply_size

    def slot_locations(self, slot):
	return slot*self.slot_size, (slot+1)*self.slot_size

    def _init_shmem(self):
	self.shmem_name = self.location + ".shm"
	self.shmem_file = open(self.shmem_name, "w+b")

	self.shmem_file.seek(self.slot_size*self.capacity - 1, 0)
	self.shmem_file.write(b'\0')
	self.shmem_file.seek(0, 0)

	self.shmem = mmap.mmap(self.shmem_file.fileno(), 0)


    def _init_timers(self):
	self.waiting_timer = timestat.TimeStat("waiting", ignore=15.0)
	self.preproc_timer = timestat.TimeStat("preprocessing")
	self.gpu_timer = timestat.WorkTimeStat("gpu")
	self.pp_shm_timer = timestat.WorkTimeStat("pp_shmem")
	self.pp_sock_timer = timestat.WorkTimeStat("pp_socket")

    def _look_for_jobs(self):
	for slot in range(self.capacity):
	    x, y = self.slot_locations(slot)
	    status = self.shmem[y-2:y]
	    if status == QUERY_AVAILABLE:
		self.job_slots.append(slot)

    def run(self):
	self.sock_conn, self.gpu_conn = multiprocessing.Pipe(True)
	socketeer = ServerSocketProcess(self.location, self.capacity,
	    self.query_size, self.reply_size, self.shmem, self.sock_conn)
	socketeer.start()
	self.run_gpu_side()


    def run_gpu_side(self):
	print >>sys.stderr, "gpu side going!"
	cur_timeout = self.min_timeout
	while True:
	    self.waiting_timer.start()

	    self.job_slots = []
	    self._look_for_jobs()
	    timeout = 0.0 if self.job_slots else cur_timeout
	    if debug:
		print >>sys.stderr, "timeout=", timeout
	    rd, _, _ = select.select([self.gpu_conn], [], [], timeout)
	    for sock in rd:
                x = sock.recv()
                if x == "DIE" or len(x) == 0:
                    print "connecting socket closed; gpu side quit."
                    sys.stdout.flush()
                    sys.exit(0)

	    self.waiting_timer.stop()
	    if self.job_slots:
		self.prepare_run_and_reply()
		cur_timeout = self.min_timeout
	    elif cur_timeout < self.max_timeout:
		cur_timeout *= 2

	    if self.milestone_step and self.gpu_timer.total_work() >= self.next_milestone:
		print "----"
		print str(self.waiting_timer)
		print str(self.preproc_timer)
		print str(self.gpu_timer)
		print str(self.pp_shm_timer)
		print str(self.pp_sock_timer)
		sys.stdout.flush()
		self.next_milestone += self.milestone_step
	# end run()

    def prepare_run_and_reply(self):
	if debug:
	    print >>sys.stderr, "jobs", ",".join(map(str,self.job_slots))
	self.preproc_timer.start()
	work = []
	for slot in self.job_slots:
	    x, y = self.slot_locations(slot)
	    wtd = bytes(self.shmem[x:x+self.query_size])
	    cs = checksum(wtd)
	    if debug:
		print >>sys.stderr,  "server received %d bytes with checksum %d" % (len(wtd), cs)
	    assert cs == ord(self.shmem[y-3]), (cs, ord(self.shmem[y-3]))
	    work.append(wtd)

	self.preproc_timer.stop()
	self.gpu_timer.start(len(self.job_slots))
	if debug:
	    print >>sys.stderr, "about to call self.run_jobs"
	replies = self.run_jobs(work)
	if debug:
	    print >>sys.stderr, "finished with self.run_jobs"
	self.gpu_timer.stop()
	self.pp_shm_timer.start(len(self.job_slots))

	for reply, slot in zip(replies, self.job_slots):
	    assert len(reply) <= self.reply_size
	    x, y = self.slot_locations(slot)
	    self.shmem[x:x+len(reply)] = reply
	    cs = checksum(reply)
	    self.shmem[y-3] = chr(cs)
	    self.shmem[y-2:y] = REPLY_AVAILABLE
	    if debug:
		print >>sys.stderr, "server sent %d bytes with checksum %d" % (len(reply), cs)

	self.pp_shm_timer.stop()
	self.pp_sock_timer.start(len(self.job_slots))
	self.gpu_conn.send_bytes("GO")
	self.pp_sock_timer.stop()
	self.job_slots = []
	#end prepare_run_and_reply


class SillyServer(Server):
    def run_jobs(self, jobs):
	out = [''.join(reversed(job)) for job in jobs]
	return out


if __name__ == "__main__":
    if len(sys.argv) == 2:
	print "running silly server"
	sys.stdout.flush()

	S = SillyServer(sys.argv[1], 10, 100, 100)
	S.run()
    elif len(sys.argv) == 3:
	print "running silly client"
	def cb(x):
	    print "got back",x

	C = Client(sys.argv[1])
	C.write_query(sys.argv[2], cb)
	C.handle_read()
    else:
	print >>sys.stderr, "usage: %s location [send_message]" % (sys.argv[0])
