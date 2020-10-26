#! /usr/bin/env python
import argparse
import MySQLdb as mysql
import math
import sys

import twixt

class FirstMoveDB:
    def __init__(self, model_id=1): 
	self.conn = None
	self.cur = None
	self.model_id = model_id

    def __enter__(self):
	self.conn = mysql.connect(host="localhost", user="jordan", db="twixt")
	self.cur = self.conn.cursor()
	self.cur.execute("LOCK TABLES first_move_v2 WRITE")

    def __exit__(self, type, value, traceback):
	self.cur.execute("UNLOCK TABLES")
	self.cur.close()
	self.conn.close()
	self.cur = None
	self.conn = None

    def _load_initial(self, override=False):
	self.cur.execute("SELECT COUNT(*) FROM first_move_v2 WHERE model_id=%d" % (self.model_id))
	n = self.cur.fetchone()[0]
	if n:
	    if override:
		self.cur.execute("DELETE FROM first_move_v2 WHERE model_id=%d" % (mself.model_id))
	    else:
		raise Exception("Rows already exist in first_move_v2")

	S = twixt.Game.SIZE
	M = S/2
	for x in range(1,M):
	    for y in range(M):
		p = twixt.Point(x, y)
		sql = "INSERT first_move_v2 (model_id, move, white, black, draws, visits) VALUES (%d, '%s', 0, 0, 0, 0)" % (self.model_id, str(p))
		print "sql:", sql
		self.cur.execute(sql)
	self.conn.commit()

    def _reset_visits(self):
	sql = "UPDATE first_move_v2 SET visits=white+black+draws WHERE model_id=%d" % (self.model_id)
	self.cur.execute(sql)
	self.conn.commit()

    def select_move(self, visit_count=1, verbose=False):
	with self:
            return self._select_move(visit_count, verbose)

    def _select_move(self, visit_count, verbose):
        self.cur.execute("SELECT move, white, black, draws, visits FROM first_move_v2 WHERE model_id=%d" % (self.model_id))
        all_rows = list(self.cur.fetchall())
        N = sum([x[4] for x in all_rows])
        numerator = math.sqrt(2.0 * math.log(N + 1.0))
        if verbose:
            print "N=", N, "numerator=", numerator
            verbose_rows = []

        def row_util(row):
            move, white, black, draws, visits = row
            assert visits >= white + black + draws
            mean = (white + draws*0.5 + 0.5) / (1.0 + white + black + draws)
            if mean > 0.5:
                mean = 1.0 - mean
            util = mean + numerator / math.sqrt(1.0 + visits)
            if verbose:
                verbose_rows.append((move, white, black, draws, visits, visits-black-white-draws, mean, util))
                # print "%s w=%d b=%d d=%d v=%d xv=%d mean=%5.2f%% util=%5.2f%%" % (str(move), white, black, draws, visits, visits-black-white-draws, mean*100, util*100)
            return util

        best_row = max(all_rows, key=row_util)
        move = best_row[0]
        self.cur.execute("UPDATE first_move_v2 SET visits=visits+%d WHERE move=\"%s\" AND model_id=%d" % (visit_count, move, self.model_id))
        self.conn.commit()

        if verbose:
            n = 0
            for row in sorted(verbose_rows, key=lambda x:x[7], reverse=True):
                if n % 20 == 0:
                    print "%3s %5s %5s %5s %5s %3s %6s %6s" % ("mve", "white", "black", "draws", "visit", "xv", "mean", "util")
                n += 1
                print "%3s %5d %5d %5d %5d %3d %6.2f %6.2f" % (str(row[0]), row[1], row[2], row[3], row[4], row[5], row[6]*100.0, row[7]*100.0)
            sys.stdout.flush()

        return twixt.Point(move)

    def update_move(self, move, winner):
	with self:
	    if winner == twixt.Game.BLACK:
		self.cur.execute("UPDATE first_move_v2 SET black=black+1 WHERE move=\"%s\" AND model_id=%d" % (str(move), self.model_id))
	    elif winner == twixt.Game.WHITE:
		self.cur.execute("UPDATE first_move_v2 SET white=white+1 WHERE move=\"%s\" AND model_id=%d" % (str(move), self.model_id))
	    else:
		self.cur.execute("UPDATE first_move_v2 SET draws=draws+1 WHERE move=\"%s\" AND model_id=%d" % (str(move), self.model_id))
	    self.conn.commit()

    def report(self):
	self.cur.execute("SELECT move, white, black, draws, visits FROM first_move_v2 WHERE model_id=%d" % (self.model_id))
	all_rows = self.cur.fetchall()

	def row_util(row):
	    move, white, black, draws, visits = row
	    assert visits >= white + black + draws
	    mean = (white + draws*0.5 + 0.5) / (1.0 + white + black + draws)
	    if mean < 0.5:
		mean = 1.0 - mean
	    return mean

	print("%3s %6s %5s" % ("mve", "count", "w%"))
	for row in sorted(all_rows, key=row_util):
	    move, white, black, draws, visits = row
	    mean = (white + draws*0.5 + 0.5) / (1.0 + white + black + draws)
	    print("%3s %6d %5.2f" % (move, visits, mean*100.0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("fmdb.py")
    parser.add_argument("--model_id", type=int, default=1)
    parser.add_argument("--init", action='store_true')
    parser.add_argument("--force_init", action='store_true')
    parser.add_argument("--reset_visits", action='store_true')
    parser.add_argument("--util", action='store_true')
    args = parser.parse_args()

    fmdb = FirstMoveDB(args.model_id)
    with fmdb:
        if args.init:
	    print "initialize"
	    fmdb._load_initial()
	elif args.force_init:
	    print "force initialize"
	    fmdb._load_initial(True)
	elif args.reset_visits:
	    print "reset visits"
	    fmdb._reset_visits()
	elif args.util:
	    print "util"
	    fmdb._select_move(0, True)
        else:
            fmdb.report()
