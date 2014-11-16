#!/usr/bin/python

import os
import subprocess
import platform
import sys
import shutil

def fullpath(*args):
    _p = os.path
    return _p.abspath(_p.normpath(_p.expanduser(_p.join(*args))))
    del _p

projectroot = fullpath(os.path.dirname(__file__))

def path(*args):
    return fullpath(projectroot, *args)

if platform.system() == "Linux":
    subprocess.check_call(["sudo", "python",
        path("bin/dotfiles-install"), "bootstrap-root"])
elif platform.system() == "Darwin":
    subprocess.check_call(["python",
        path("bin/dotfiles-install"), "bootstrap-user"])

if not os.path.exists(path(".git")):

    os.chdir(fullpath("~"))
    subprocess.check_call(["git", "clone",
        "https://github.com/hamnox/dotfiles.git",
        fullpath("~/dotfiles")])
    os.chdir(fullpath("~/dotfiles"))
    
    if "autodel" in sys.argv:
        shutil.rmtree(projectroot)

subprocess.call(["python", fullpath("./bin/dotfiles-install")])
