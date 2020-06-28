#! /usr/bin/env python
import math
import numpy
import matplotlib.pyplot as plt
import matplotlib.lines as lines
import matplotlib.patches as patches

import naf
import twixt

SIZE = twixt.Game.SIZE
CRAD = 0.3

def _link_coords(p1, p2):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    n = math.hypot(dx, dy)
    nx = CRAD * dx / n
    ny = CRAD * dy / n
    return [p1.x+nx, p2.x-nx], [p1.y+ny, p2.y-ny]


def game_to_axes(game, ax):
    ax.set_aspect('equal')

    # Dots for empty peg holes
    Z = numpy.ones((SIZE,SIZE))
    Z[0,0] = Z[0,-1] = Z[-1,0] = Z[-1,-1] = 0
    X, Y = Z.nonzero()
    ax.scatter(X, Y, marker='.', s=6)


    # Links!
    link_colors = ['darkblue', 'grey']
    for i in range(8):
	nz = game.links[i].nonzero()
	for x, y in zip(*nz):
	    ld = game.describe_link(i, x, y)
	    xs, ys = _link_coords(ld.p1, ld.p2)
	    line = lines.Line2D(xs, ys, color=link_colors[ld.owner], linewidth=1.0, axes=ax)
	    ax.add_line(line)

    # White circles for white pegs
    X, Y = game.pegs[game.WHITE].nonzero()
    # ax.scatter(X, Y, marker='.', alpha=1, s=25, c='white', edgecolors='k', fill=True)
    for x, y in zip(X, Y):
	c = patches.Circle((x, y), 0.3, facecolor='w', edgecolor='k', fill=True)
	ax.add_patch(c)

    # Black circles for black pegs
    X, Y = game.pegs[game.BLACK].nonzero()
    ax.scatter(X, Y, marker='o', s=25, c='k')

    # Row and Column Labels
    ax.xaxis.set_ticks(numpy.arange(0,SIZE))
    ax.xaxis.set_ticklabels([chr(ord('A')+i) for i in range(SIZE)])

    ax.yaxis.set_ticks(numpy.arange(0,SIZE))
    ax.yaxis.set_ticklabels([str(i+1) for i in range(SIZE)])

    ax.tick_params(axis='both', bottom=True, top=True, left=True, right=True,
	labelbottom=True, labeltop=True, labelleft=True, labelright=True)

    # Guide lines
    guide_line_len = (SIZE-3) // 2
    for dx in (-1, 1):
	x0 = ((SIZE-1) - dx*(SIZE-3)) / 2
	for dy in (-1, 1):
	    y0 = ((SIZE-1) - dy*(SIZE-3)) / 2
	    for slope in (1, 2):
		x1 = x0 + dx*(3-slope)*guide_line_len
		y1 = y0 + dy*slope*guide_line_len
		line = lines.Line2D([x0, x1], [y0, y1], color='lightgreen', axes=ax, linewidth=0.5)
		ax.add_line(line)

    # Border lines
    for c in [0.5, SIZE-1.5]:
	line = lines.Line2D([c,c], [0.5, SIZE-1.5], linewidth=3, color='black', axes=ax)
	ax.add_line(line)

	line = lines.Line2D([0.5, SIZE-1.5], [c,c], linewidth=3, color='lightgrey', axes=ax)
	ax.add_line(line)


def show_game(game):
    fig, ax = plt.subplots()
    game_to_axes(game, ax)
    plt.show()

def show_game_with_p(game, P):
    fig, ax = plt.subplots()
    D = numpy.zeros((SIZE, SIZE))

    for i, p in enumerate(P):
        point = naf.policy_index_point(game, i)
        print point, p
        D[point.y, point.x] = p

    ax.imshow(D)

    game_to_axes(game, ax)
    plt.show()

if __name__ == "__main__":
    game = twixt.Game()
    game.play('J3')
    game.play('K12')
    game.play('L15')
    game.play('M14')
    game.play('N14')

    show_game(game)
