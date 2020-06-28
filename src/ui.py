#! /usr/bin/env  -- python
import math

import graphics as gr
import twixt

def ifelse0(condition, value):
    if condition:
	return value
    else:
	return 0

class TBWHistory:
    def __init__(self, move):
	self.move = move
	self.objects = []

class TwixtBoardWindow:
    CELL = 20
    SIZE = twixt.Game.SIZE
    PEG_RADIUS = 7
    HOLE_RADIUS = 2

    # Return me two diagonal points near board edge
    def twopoints(self, i):
        xbit = (i ^ (i>>1)) & 1
        ybit = (i >> 1) & 1
        x0 = (1 + xbit*self.SIZE)*self.CELL
        y0 = (1 + ybit*self.SIZE)*self.CELL
        x1 = (2 + xbit*(self.SIZE-2))*self.CELL
        y1 = (2 + ybit*(self.SIZE-2))*self.CELL
        return [gr.Point(x0,y0), gr.Point(x1,y1)]

    def center(self, x, y):
	return gr.Point((x+1)*self.CELL+self.CELL/2, (y+1)*self.CELL+self.CELL/2)

    def __init__(self, name="Twixt"):
	self.win = gr.GraphWin(name, self.CELL*(2+self.SIZE), self.CELL*(2+self.SIZE), autoflush=False)
	self.history = []
	self.known_moves = set()

	# Regular background
	self.win.setBackground(gr.color_rgb(244, 255,240))

	# black/white end zones
	for i in range(4):
	    a = self.twopoints(i)
	    b = self.twopoints(i+1)
	    color = [gr.color_rgb(255,255,200), gr.color_rgb(200,200,200)][i&1]
	    poly = gr.Polygon(a[0], a[1], b[1], b[0])
	    poly.setOutline(color)
	    poly.setFill(color)
	    poly.draw(self.win)

	# peg holes
	for x in range(self.SIZE):
	    for y in range(self.SIZE):
		if x in (0, self.SIZE-1) and y in (0, self.SIZE-1):
		    continue

		c = gr.Circle(self.center(x, y), self.HOLE_RADIUS)
		c.setFill("black")
		c.draw(self.win)

	# labels
	for i in range(self.SIZE):
	    ctr = self.center(i, i)
	    row_label = "%d" % (i+1)
	    txt = gr.Text(gr.Point(self.CELL/2, ctr.y), row_label)
	    txt.draw(self.win)
	    txt = txt.clone()
	    txt.move(self.CELL*(self.SIZE+1), 0)
	    txt.draw(self.win)

	    col_label = chr(ord('A')+i)
	    txt = gr.Text(gr.Point(ctr.x, self.CELL/2), col_label)
	    txt.draw(self.win)
	    txt = txt.clone()
	    txt.move(0, self.CELL*(self.SIZE+1))
	    txt.draw(self.win)

	gr.update()

    def set_game(self, game):
	i = 0
	while i < len(game.history) and i < len(self.history):
	    if game.history[i] != self.history[i].move:
		break
	    i += 1

	# Get rid of now unneeded objects
	if i < len(self.history):
	    for h in reversed(self.history[i:]):
		for o in h.objects:
		    o.undraw()
		self.known_moves.remove(h.move)
	    self.history = self.history[:i]

	# Add new objects
	while i < len(game.history):
	    self.create_move_objects(game, i)
	    i += 1

	gr.update()

    def set_naf(self, naf, rotate=False):
	for h in reversed(self.history):
	    for o in h.objects:
		o.undraw()
	self.history = []
	self.known_moves = set()

	if not rotate:
	    xyp = lambda x, y: twixt.Point(x, y)
	    pp = lambda p: p
	    cp = lambda c: 1-c
	else:
	    xyp = lambda x, y: twixt.Point(y, x)
	    cp = lambda c: c
	    pp = lambda p: twixt.Point(p.y, p.x)

	objs = []
	
	for x, y, i in zip(*naf[:,:,8:].nonzero()):
	    objs.append(self._create_drawn_peg(xyp(x, y), cp(i&1)))

	for x, y, j in zip(*naf[:,:,:8].nonzero()):
	    link = twixt.Game.describe_link(j, x, y)
	    objs.append(self._create_drawn_link(pp(link.p1), pp(link.p2), cp(i&1)))

	nho = TBWHistory("nninputs")
	self.history.append(nho)
	nho.objects = objs

    def set_nn_inputs(self, pegs, links, rotate=False):
	for h in reversed(self.history):
	    for o in h.objects:
		o.undraw()
	self.history = []
	self.known_moves = set()

	if not rotate:
	    xyp = lambda x, y: twixt.Point(x, y)
	    pp = lambda p: p
	    cp = lambda c: 1-c
	else:
	    xyp = lambda x, y: twixt.Point(y, x)
	    cp = lambda c: c
	    pp = lambda p: twixt.Point(p.y, p.x)

	objs = []

	for x, y, i in zip(*pegs.nonzero()):
	    objs.append(self._create_drawn_peg(xyp(x, y), cp(i)))

	i_px_py = []
	# color = game.WHITE
	for vertical in [False, True]:
	    for diff_sign in [False, True]:
		for as_me in [False, True]:
		    index = ifelse0(vertical, twixt.Game.LINK_LONGY)
		    index += ifelse0(diff_sign, twixt.Game.LINK_DIFFSIGN)
		    index += 1 if as_me else 0
		    pad_x = ifelse0(vertical or diff_sign, 1)
		    pad_y = ifelse0(not vertical or diff_sign, 1)

		    i_px_py.append((index, pad_x, pad_y))

	for x, y, j in zip(*links.nonzero()):
	    index, pad_x, pad_y = i_px_py[j]
	    lx = x - pad_x
	    ly = y - pad_y
	    desc = twixt.Game.describe_link(index, lx, ly)
	    c1 = 2 - 2*pegs[desc.p1.x, desc.p1.y, 0] - pegs[desc.p1.x, desc.p1.y, 1]
	    c2 = 2 - 2*pegs[desc.p2.x, desc.p2.y, 0] - pegs[desc.p2.x, desc.p2.y, 1]
	    if c1 == 0 and c2 == 0:
		color = 0
	    elif c1 == 1 and c2 == 1:
		color = 1
	    else:
		color = 2
	    objs.append(self._create_drawn_link(pp(desc.p1), pp(desc.p2), color))
	
	nho = TBWHistory("nninputs")
	self.history.append(nho)
	nho.objects = objs
	#end set_nn_inputs




    def _create_drawn_peg(self, point, color):
	peg = gr.Circle(self.center(point.x, point.y), self.PEG_RADIUS)
	if color == twixt.Game.WHITE:
	    peg.setWidth(2)
	    peg.setFill("white")
	else:
	    peg.setFill("black")
	peg.draw(self.win)
	return peg

    def create_move_objects(self, game, index):
	color = (index + 1) & 1
	move = game.history[index]
	nho = TBWHistory(move)
	self.history.append(nho)
	assert isinstance(move, twixt.Point), "Swap not handled yet"

	nho.objects.append(self._create_drawn_peg(move, color))
	self.known_moves.add(move)

	for dlink in game.DLINKS:
	    other = move + dlink
	    if other in self.known_moves and game.safe_get_link(move, other, color):
		nho.objects.append(self._create_drawn_link(move, other, color))

	# end create_move_objects()


    def _create_drawn_link(self, p1, p2, color):
	carray = [gr.color_rgb(0,0,0), gr.color_rgb(150,150,150), gr.color_rgb(255,0,0)]
	c1 = self.center(*p1)
	c2 = self.center(*p2)
	dx = c2.x - c1.x
	dy = c2.y - c1.y
	hypot = math.hypot(dx, dy)
	cos = dx / hypot
	sin = dy / hypot
	lx1 = int(c1.x + cos*self.PEG_RADIUS + 0.5)
	ly1 = int(c1.y + sin*self.PEG_RADIUS + 0.5)
	lx2 = int(c2.x - cos*self.PEG_RADIUS + 0.5)
	ly2 = int(c2.y - sin*self.PEG_RADIUS + 0.5)
	line = gr.Line(gr.Point(lx1,ly1), gr.Point(lx2,ly2))
	line.setWidth(3)
	line.setFill(carray[color])
	line.draw(self.win)
	return line



if __name__ == "__main__":
    test = TwixtBoardWindow()
    game = twixt.Game()
    game.play("b3")
    game.play("j10")
    game.play("c5")

    test.set_game(game)
    test.win.getMouse()
    game.undo()
    test.set_game(game)
    test.win.getMouse()
    test.win.close()
