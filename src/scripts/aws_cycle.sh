#! /bin/bash -e
cd /home/ec2-user
exec >> ds.log 2>&1
echo "Begin DAS SCRIPT Anew"
date

DATA_DIR=/home/ec2-user
cd deeptwixt
source activate tensorflow_p27
MODEL=`ssh azabu.jyjy.org cat /data/twixt/models/best`
MODEL_BASE=`basename $MODEL`
echo "Current model is $MODEL"

mkdir -p $DATA_DIR/model
rm -rf $DATA_DIR/train
mkdir -p $DATA_DIR/train
rm -rf $DATA_DIR/log

scp "azabu.jyjy.org:$MODEL*" $DATA_DIR/model

echo "attempt to kill."
./nns.py -l /tmp/loc0 -k
sleep 3

./nns.py -l /tmp/loc0 -m $DATA_DIR/model/$MODEL_BASE > out0 2>&1 &

while ! grep Ready out0
do
    date
    echo "not ready yet."
    sleep 3
done
echo "Finally ready!"

./play_and_ship.py -n $((50 + RANDOM%61)) -l $DATA_DIR/log -t $DATA_DIR/train &
