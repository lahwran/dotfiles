#!/usr/bin/env python

import subprocess

dependencies = [
    "vim",
    "git",
]

subprocess.call(["sudo", "apt-get", "install"] + dependencies)
