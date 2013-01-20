#!/usr/bin/env python

import subprocess
import sys
import logging
import datetime

import wrap_process

logger = logging.getLogger("install")

dependencies = [
    "vim",
    "git",
]


def user_install():
    logger.info("Doing user install...")
    pass

def root_install():
    logger.info("Doing root install...")
    wrap_process.call("apt-get", ["apt-get", "install"] + dependencies)



def init_logging(mode):
    rootlogger = logging.getLogger()
    formatter = logging.Formatter('[%(asctime)s ' + mode + ' %(levelname)8s] %(name)s: %(message)s')
    rootlogger.setLevel(logging.DEBUG)
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    logfile = open(".install_%s.log" % today_str, "a")
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(logfile)
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        rootlogger.addHandler(handler)
    logger.info("Logging initialized")

def main(mode="init", *args):
    init_logging(mode)

    if mode == "superuser":
        root_install(*args)
    elif mode == "init":
        logger.info("running root portion")
        subprocess.call(["sudo", sys.executable, sys.argv[0], "superuser"] + list(args))
        logger.info("running user portion")
        user_install(*args)
    elif mode == "user":
        user_install(*args)
    else:
        logger.error("mode must be one of 'superuser', 'init', 'user': %s", mode)

if __name__ == "__main__":
    main(*sys.argv[1:])
