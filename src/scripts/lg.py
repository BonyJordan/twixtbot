#! /usr/bin/env python
import argparse
from bs4 import BeautifulSoup
import collections
import os
import re
import requests
import subprocess
import sys
import time
import urlparse

GameInfo = collections.namedtuple("GameInfo", "game_id popen moves draw_offer")

def find_moves_for_game(session, game_id):
    move_re = re.compile("(b|r)\[([a-x][a-x]|swap|SWAP)(\|draw)?\]")
    size_re = re.compile("SZ\[(\d+)\]")
    url = "http://www.littlegolem.net/servlet/sgf/%s/game%s.tsgf" % (game_id, game_id)
    resp = session.get(url)

    mo = size_re.search(resp.text)
    assert mo,  (resp.text)
    assert mo.group(1) == "24"

    moves = []
    draw_offer = False
    prev_color = 'r'
    for field in resp.text.split(';'):
        mo = move_re.match(field)
        if mo:
            color = mo.group(1)
            assert color in ['r', 'b']
            assert color != prev_color
            prev_color = color

            mstr = mo.group(2)
            if len(mstr) == 2:
                mstr = mstr[0] + str(int(ord(mstr[1]) - ord('a') + 1))
            moves.append(mstr.encode('ascii'))
            draw_offer = (mo.group(3) is not None)
    return moves, draw_offer


def find_games(session, verbose=False):
    gid_re = re.compile("\#(\d+)")

    resp = session.get('http://www.littlegolem.net/jsp/game/index.jsp')
    soup = BeautifulSoup(resp.text, 'html.parser')
    key_text = soup.find(string=re.compile(".*The list of all your active.*"))
    if key_text is None:
        if verbose:
            print "No games"
        return []
    table = key_text.find_next("table")
    tbody = table.tbody
    out = []
    for trow in tbody.find_all("tr"):
        mo = gid_re.search(trow.td.a.text)
        out.append(mo.group(1))
        if verbose:
            print "game id", mo.group(1)
    return out
        

def handle_invites(session):
    try:
        resp = session.get('http://www.littlegolem.net/jsp/invitation/index.jsp')
    except requests.exceptions.ConnectionError as e:
        print e
        return "CE"

    soup = BeautifulSoup(resp.text, 'html.parser')

    a = soup.find(string="Invitations from other players")
    if a is None:
        print "IfOP not found"
        print soup.prettify().encode('utf-8')
        return 0
    table = a.find_next('table')
    first = True
    count = 0
    for trow in table('tr'):
        if first:
            first = False
            continue

        # 0 = when
        # 1 = who
        # 2 = game
        # 3 = first/move
        # 4 = message
        # 5 = your decision

        who = trow('td')[1].text
        game = trow('td')[2].text
        yd = trow('td')[5]
        # 0 = accept; 1 = refuse

        if game == "Twixt PP :: Size 24":
            new_url = yd('a')[0].get('href')
        else:
            new_url = yd('a')[1].get('href')

        url = urlparse.urljoin(resp.url, new_url)
        url = re.sub("&amp;", "&", url)
        print url
        sys.stdout.flush()

        session.get(url)
        count += 1

    return count

def start_thinking_for_game(movelist, loc, time):
    #cmd = ["./one.py", "-m", ",".join(movelist), "-r",
    #    "nnclient:location=%s,name=net" % (loc), "-t",
    #    "nnmplayer:resource=net,trials=5000,use_swap=1", "-T"]
    cmd = ["./one.py", "-m", ",".join(movelist),
        "-t", "asn_player:trials=%d,location=%s" % (time, loc), "-T"]

    print "start for game:", game_id
    print " ".join(cmd)
    sys.stdout.flush()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p

def stop_thinking_for_game(gi):
    #####
    out, err = gi.popen.communicate()
    print "stop for game:", gi.game_id, "draw offer:", gi.draw_offer
    print "--OUT--\n", out
    print "--RETURNCODE--\n", gi.popen.returncode
    sys.stdout.flush()

    lines = out.splitlines()
    assert len(lines) == 3, (lines)
    score_text = lines[2].split(':')[0]
    if score_text == 'fwin':
        score = 1.0
    elif score_text == 'fdraw':
        score = -0.5
    elif score_text == 'flose':
        score = -1.0
    elif score_text == "swapmodel":
        score = 0.0
    else:
        score = float(score_text)

    move = None

    if score < -0.85:
        print "low score (%g): resign" % score
        move = "resign"

    if gi.draw_offer and score_text != "fwin" and float(score_text) < -0.1 and len(gi.moves) > 10:
        move = "draw"

    if gi.draw_offer and move is None:
        ds = subprocess.check_output(["./one.py", "-m", ",".join(gi.moves),
            "-D"])
        if ds[:4] == "draw":
            move = "draw"
        elif ds[:3] == "bcw" and len(gi.moves)%2 == 0:
            move = "draw"
        elif ds[:3] == "wcw" and len(gi.moves)%2 == 1:
            move = "draw"
        print "draw state:", ds

    if move is None:
        move = lines[1]
        if len(move) < 4:
            m0 = move[0]
            m1 = chr(ord('a') - 1 + int(move[1:]))
            move = m0 + m1

    url = "http://www.littlegolem.net/jsp/game/game.jsp?sendgame=%s&sendmove=%s" % (gi.game_id, move)
    print "url:", url
    session.post(url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Little Golem Bot Controller")
    parser.add_argument("-u", "--user_name", type=str, required=True)
    parser.add_argument("-p", "--password", type=str, required=True)
    parser.add_argument("-M", "--max_thinking_games", type=int, default=10)
    parser.add_argument("-l", "--location", type=str, default="/tmp/loc1")
    parser.add_argument("-t", "--time", type=int, default=50000)
    args = parser.parse_args()

    session = requests.Session()
    resp = session.post('http://www.littlegolem.net/jsp/login/index.jsp',
        data={"login":args.user_name, "password": args.password})

    # game_id -> Popen object
    thinking_games = dict()

    while True:
        rids = []
        for game_id, ginfo in thinking_games.items():
            if ginfo.popen.poll() is not None:
                rids.append(game_id)
                stop_thinking_for_game(ginfo)
        for game_id in rids:
            del thinking_games[game_id]

        he = handle_invites(session)
        if he == "CE":
            print "extra sleeping"
            time.sleep(1800)
            continue

        game_list = find_games(session)
        for game_id in game_list:
            if game_id in thinking_games or len(thinking_games) > args.max_thinking_games:
                continue
            move_list, draw_offer = find_moves_for_game(session, game_id)
            popen = start_thinking_for_game(move_list, args.location, args.time)
            thinking_games[game_id] = GameInfo(game_id, popen, move_list, draw_offer)
        else:
            print "no games.  sleep"
            sys.stdout.flush()
            time.sleep(120)
