#! /usr/bin/env python
import argparse
import collections
import multiprocessing
import os
import socket
import subprocess

def main():
    parser = argparse.ArgumentParser("Generic Bot Server")
    parser.add_argument("--location", "-l", type=str, required=True)
    parser.add_argument("battle_args", type=str, nargs="+")
    args = parser.parse_args()

    if os.path.exists(args.location):
        os.remove(args.location)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(args.location)
    sock.listen(5)
    os.chmod(args.location, 0777)

    procs = []

    while True:
        for p in list(procs):
            if not p.is_alive():
                procs.remove(p)
                p.join()

        conn, addr = sock.accept()
        p = multiprocessing.Process(target=go, args=(conn, args.battle_args))
        p.start()
        conn.close()
        procs.append(p)

def go(conn, bargs):
    request = conn.recv(4096).strip()
    print request
    subprocess.call(["./one.py", "-m", request] + bargs,
        stdout=conn)
    conn.close()


if __name__ == "__main__":
    main()
