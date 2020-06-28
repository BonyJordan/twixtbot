#! /usr/bin/env python

import argparse
import importlib
import Queue
import random
import sys
import threading

import naf
import twixt

class BattleSpec:
    def __init__(self, black_spec, white_spec, init_moves, with_training=True):
	self.black_spec = black_spec
	self.white_spec = white_spec
	self.init_moves = init_moves
	self.move_list = list(init_moves)
	self.win_color = None
	self.final_score = None
	if with_training:
	    self.train_list = []
	else:
	    self.train_list = None

    def battle(self):
	black_th = twixt.get_thinker(self.black_spec, resources)
	white_th = twixt.get_thinker(self.white_spec, resources)
	self.win_color, self.final_score = battle_once(black_th, white_th, self.init_moves, self.train_list, self.move_list)

def battle_once(black_th, white_th, moves, train_list, move_list=None):
    game = twixt.Game()
    final_score = -1

    if isinstance(moves, twixt.Point):
	game.play(moves)
	if args.show_moves:
            print 'INIT',moves,'-'
	    sys.stdout.flush()
    elif type(moves) == str:
	for m in moves.split(','):
	    game.play(m)
            if args.show_moves:
                print 'INIT',m,'-'
                sys.stdout.flush()
    elif moves == None:
	pass
    else:
	raise Exception("Bad moves type:", moves)

    if args.display:
	tb.set_game(game)

    while not game.just_won():
	if not game.can_win(0) and not game.can_win(1):
	    final_score = 0
	    return None, final_score

	if len(game.legal_plays()) == 0:
	    final_score = 0
	    return None, final_score

	if game.turn == game.BLACK:
	    th = black_th
	else:
	    th = white_th

	if train_list != None:
	    train_list.append(naf.LearningState(game))
	pmout = th.pick_move(game)
	if type(pmout) == tuple:
	    m, policy_array = pmout
	    assert policy_array is not None
	    if isinstance(move_list, list):
		move_list.append(m)
	else:
	    m = pmout
	    if isinstance(move_list, list):
		move_list.append(m)
	    if m == "resign":
		if train_list != None:
		    train_list.pop()
		if args.report_move_count:
		    print "%d moves." % len(game.history)
		final_score = 1
		return 1-game.turn, final_score

	    if train_list != None:
		policy_array = naf.single_move_policy_array(game, m)

	if train_list != None:
	    assert type(policy_array) != type(None)
	    train_list[-1].N = policy_array

	if args.show_moves:
	    print game.COLOR_NAME[game.turn],th.name,m,th.report
	    sys.stdout.flush()
	assert m != "resign"
	game.play(m)

	if args.display:
	    tb.set_game(game)

    if args.report_move_count:
	print "%d moves." % len(game.history)
    return 1-game.turn, final_score


def get_init_moves(fmdb_lock=None):
    if args.moves:
	return args.moves
    elif args.first_moves:
	if fmdb_lock:
	    fmdb_lock.acquire()
	init_moves = fmdb_.select_move(2)
	if fmdb_lock:
	    fmdb_lock.release()
	print "next first move:", str(init_moves)
	return init_moves
    elif args.random_first_moves:
	x = random.randint(1, twixt.Game.SIZE//2)
	y = random.randint(0, twixt.Game.SIZE//2)
	init_moves = twixt.Point(x, y)
	print "random first move:", str(init_moves)
	return init_moves
    else:
	return None


def unthreaded_run():
    names = [args.black, args.white]
    thinker = [twixt.get_thinker(n, resources) for n in names]
    scores = [0.0, 0.0]

    for n in range(args.num_games):
	parity = n % 2
	if parity == 0:
	    moves = get_init_moves()

	if args.training_file:
	    train_list = []
	else:
	    train_list = None

	win_color, final_score = battle_once(thinker[parity], thinker[1-parity], moves, train_list)
	if win_color == None:
	    scores[0] += 0.5
	    scores[1] += 0.5
	elif win_color == twixt.Game.BLACK:
	    scores[parity] += 1.0
	else:
	    scores[1-parity] += 1.0

	if args.first_moves:
	    fmdb_.update_move(moves, win_color)

	if args.training_file:
	    for t in reversed(train_list):
		final_score = -final_score
		t.z = final_score
		train_file.write(t.to_bytes())
		train_file.flush()


	pct = 100.0*scores[0]/(scores[0]+scores[1])
	print "After %d game%s..." % (n+1, "" if n==0 else "s")
	print ": %5.1f (%5.1f%%) %s" % (scores[0], pct, thinker[0].name)
	print ": %5.1f (%5.1f%%) %s" % (scores[1], 100-pct, thinker[1].name)
	sys.stdout.flush()

    if args.display:
	tb.win.getMouse()

    if args.training_file:
	train_file.close()
    # end unthreaded_run()

class ThreadingManager:
    def __init__(self, args):
	self.args = args
	self.fmdb_lock = threading.Lock()
	self.job_request_queue = Queue.Queue()
	self.new_job_queue = Queue.Queue()
	self.done_job_queue = Queue.Queue()

    def job_maker_thread_run(self):
	n = 0
	while n < args.num_games:
	    req = self.job_request_queue.get()
	    init_moves = get_init_moves(self.fmdb_lock)

	    bs1 = BattleSpec(args.black, args.white, init_moves, args.training_file != None)
	    bs2 = BattleSpec(args.white, args.black, init_moves, args.training_file != None)
	    self.new_job_queue.put(bs1)
	    self.new_job_queue.put(bs2)
	    self.job_request_queue.get()
	    n += 2
	    # we put 2 jobs on the queue, so pull a 2nd and 3rd request before we
	    # do it again.
    # end job_maker_thread_run(self):

    def worker_thread_run(self):
	while True:
	    self.job_request_queue.put("r")
	    job = self.new_job_queue.get()
	    job.battle()
	    self.done_job_queue.put(job)

    def completion_thread_run(self):
	scores = [0, 0]
	for n in range(self.args.num_games):
	    fin = self.done_job_queue.get()
	    parity = 0 if fin.black_spec == args.black else 1
	    if fin.win_color == None:
		scores[0] += 0.5
		scores[1] += 0.5
	    else:
		scores[fin.win_color ^ parity] += 1.0

	    if args.first_moves:
		self.fmdb_lock.acquire()
		fmdb_.update_move(moves, win_color)
		self.fmdb_lock.release()

	    if args.training_file:
		final_score = fin.final_score
		for t in reversed(fin.train_list):
		    final_score = -final_score
		    t.z = final_score
		    train_file.write(t.to_bytes())
		    train_file.flush()

	    pct = 100.0*scores[0]/(scores[0]+scores[1])
	    print "After %d game%s..." % (n+1, "" if n==0 else "s")
	    print ": %5.1f (%5.1f%%) %s" % (scores[0], pct, args.black)
	    print ": %5.1f (%5.1f%%) %s" % (scores[1], 100-pct, args.white)

	print "ALL GAMES DONE"
	# end completion_thread
	sys.stdout.flush()

    def go(self):
	jmt = threading.Thread(target=self.job_maker_thread_run)
	jmt.daemon = True
	jmt.start()

	for i in range(args.threads):
	    wt = threading.Thread(target=self.worker_thread_run)
	    wt.daemon = True
	    wt.start()

	self.completion_thread_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='One twixt battle.')
    parser.add_argument('--moves', '-m', type=str)
    parser.add_argument('--display', '-d', action='store_true')
    parser.add_argument('--first_moves', '-F', action='store_true')
    parser.add_argument('--first_moves_model', type=int, default=1)
    parser.add_argument('--random_first_moves', '-R', action='store_true')
    parser.add_argument('--show_moves', '-M', action='store_true')
    parser.add_argument('--report_move_count', action='store_true')
    parser.add_argument('--white', '-w', type=str, required=True)
    parser.add_argument('--black', '-b', type=str, required=True)
    parser.add_argument('--num_games', '-n', type=int, default=1)
    parser.add_argument('--threads', '-t', type=int, default=0)
    parser.add_argument('--training_file', '-T', type=str)
    parser.add_argument('-r', '--resource', type=str, action='append')
    args = parser.parse_args()

    if args.resource:
	resources = {r.name: r for r in [twixt.get_resource(thing) for thing in args.resource]}
    else:
	resources = dict()

    count = sum([1 for thing in [args.first_moves, args.moves, args.random_first_moves] if thing])
    if count > 1:
	raise Exception("cannot more than one of --moves, --first_moves, --random_first_moves")

    if args.threads:
	if args.display:
	    print >>sys.stderr, "Cannot use both display and threads."
	    sys.exit(1)
	if args.show_moves:
	    print >>sys.stderr, "Cannot use both show_moves with threads."
	    sys.exit(1)

    if args.display:
	import ui
	tb = ui.TwixtBoardWindow()

    if args.first_moves:
	import fmdb
	fmdb_ = fmdb.FirstMoveDB(args.first_moves_model)

    if args.training_file:
	train_file = open(args.training_file, "ab")


    if args.threads:
	mgr = ThreadingManager(args)
	mgr.go()
    else:
	unthreaded_run()
