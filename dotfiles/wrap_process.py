
import subprocess
import logging
import pty
import os
import sys

from highlight import highlight

def de_ret(line):
    thelist = []
    index = 0
    for char in line:
        if char == "\r":
            index = 0
            continue
        if index == len(thelist):
            thelist.append(char)
        else:
            thelist[index] = char
        index += 1
    return "".join(thelist)

def call(name, args):
    logger = logging.getLogger(highlight(name))
    logger.info("starting %s...", args)

    master, slave = pty.openpty()

    process = subprocess.Popen(args, bufsize=1, stdin=slave, stdout=slave, stderr=subprocess.STDOUT, close_fds=True)
    os.close(slave)
    process.stdout = os.fdopen(master)
    try:
        while True:
            line = process.stdout.readline()
            if not line: break

            line = line.replace("\n", "")
            if "\r" in line:
                line = de_ret(line)
            logger.info(line)
    except IOError as e:
        if e.errno == 5:
            pass
        else:
            raise
    return process.wait()
