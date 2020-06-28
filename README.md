# twixtbot
Code for AI to play the board game Twixt

# Requirements 
The code is written with tensorflow 1.12 and python2 and runs on linux.
I know all the cool kids use tensorflow 2.2 and python3 nowadays.  Sorry!

# How to Play!
Um... so the bad news is there is nothing plug-n-play here.  Maybe some
enterprising soul can turn this into an app that someone who doesn't
want to fight with code can just turn on and play.  What I can give
you is the brief outline.

I first run a `nns.py` (Neural Net Server) with
```
./nns.py -m ../models/six-917000 -l /tmp/loc1 > out1 2>&1 &
```

Here `-m` gives us a pointer to the TensorFlow model, I have given you
my best one.  As we have seen from results on Little Golem, it can
probably be improved with more training and/or a bigger net.  `-l` is
the "location" which is a combination unix socket and shared memory.

Now, if you want to get a smart move, you use the magic `one.py` program,
example:
```
./one.py -m v19,r19,t18,p13,n13,m9,i9,k17 -t asn_player:trials=50000,location=/tmp/loc1 -T
```

Here `-m` gives a list of comma separated moves (`swap` is a legal move too),
`-t` tells us what thinker we want to use.  `asn_player` is the Asynchronous
Net Player (I use `nnmplayer` for training runs), and `trials` is the amount
of time to spend; on my computer it takes approximately 1 minute per 10000
trials.  Even a very low number like 200 gives quite a strong opponent and
is much faster.  `location` you will recall from the `nns.py` command.

# Other files
I don't remember what all of these do.  The biggies are:
- `battle.py` which you use if you want to test two nets or configurations
    against each other
- `bcount.py` which is nice if you use `battle.py` in conjunction with `pmany.py`
- `mkbig.py` creates a raw, untrained net
- `naf.py` is a bunch of code to convert twixt positions to numpy arrays and back
- `nnclient.py`, `nns.py`, `smmppy.py` - these three files work together
    to create a "neural net server".  This is especially useful during
    the part of training where you are self-playing, because it is
    important both to batch up your queries and also python sucks at
    threading.
- `nnmcts.py`, `nnmplayer.py` - these two files work together to make the
    synchronous player.  Note you can use `nnmplayer` with `one` or `battle`
    with the `model:` option if you don't want to set up a `nns` server.
- `one.py` - as explained above, this is great if you want a bot player
    to give you a single move.
- `pmany.py` - a super handy python script to let you run a zillion copies
    of the same program.  For example, during self-play what I do is set
    up a single `nns.py` and then around 80 `battle.py` with `nnmplayer`
    bots set to add 25% random noise (as per the Alpha Go stuff) all
    connecting to the same server.
- `swapmodel.py` - instead of writing code to MCTS the swap rule, I just
    played the bot against itself a few hundred times with each starting
    move, figured out whether white or black wins, fit a (almost) linear
    model to it, and there you go.
- `train.py` - runs a round or two of training on the neural net.
- `twixt.py` - `twixt.Game` is a super handy class for representing the
    state of a game of twixt.
- `scripts` - ugh, I barely remember what any of these do.  You can see
    some stuff relating to AWS; what I'd do is rent several of the cheapest
    possible box with a GPU on it, run self-play games, and then download
    the output of those games to my home computer with manly GPUs to run
    actual training.
- `web` - believe it or not, this is an almost working web page where you
    can just come in and play a game of twixt against the bot.
