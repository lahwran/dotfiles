#!/usr/bin/env python

import subprocess
import sys
import logging
import datetime
import os
import stat
import time
import shutil


from dotfiles.highlight import highlight
from dotfiles import wrap_process

assert (0644 ==
        stat.S_IRUSR |
        stat.S_IWUSR |
        stat.S_IRGRP |
        stat.S_IROTH), "os is insane"

logger = logging.getLogger("-")

os_dependencies = [
    "vim",
    "git",
    "fail2ban",
    "python-dev",
    "ntp-daemon",
    "tmux",
    "tig",
]

pip_dependencies = [
    "virtualenv",
    "pytest",
    "twisted",
    "blessings",
    "watchdog",
]

ensure_nonexistant = [
    "~/.bash_logout",
]

def gitconfig(*args):
    return subprocess.check_output(["git", "config", "--global"] + list(args))

def fullpath(*args):
    _p = os.path
    return _p.abspath(_p.normpath(_p.expanduser(_p.join(*args))))
    del _p

projectroot = fullpath(os.path.dirname(__file__), "..")

def path(*args):
    return fullpath(projectroot, *args)

def install_text(filename, text, permissions=None,
        before=False, prev_existance=True):
    filename = fullpath(filename)
    try:
        with open(filename, "r") as reader:
            contents = reader.read()
    except IOError as e:
        if e.errno == 2 and not prev_existance:
            contents = ""
        else:
            raise

    if text not in contents:
        if before:
            contents = text + "\n" + contents
        else:
            contents += "\n" + text
        with open(filename, "w") as writer:
            # rewrite whole thing to prevent race conditions

            # todo: why did I think this was a better or worse idea than
            # appending?
            writer.write(contents)

    if permissions is not None:
        os.chmod(filename, permissions)


def install_copy(master, target):
    shutil.copy(path(master), fullpath(target))


def install_dir(target, log=True):
    target = fullpath(target)
    try:
        os.makedirs(target)
        return True
    except OSError as e:
        if e.errno == 17:
            return False
        else:
            raise


def install_file(master, target):
    # link master to target
    logger.info("installing %s -> %s", master, target)
    master = path(master)
    target = fullpath(target)

    install_dir(os.path.dirname(target), log=False)

    try:
        os.symlink(master, target)
    except OSError as e:
        if e.errno == 17:
            assert fullpath(os.readlink(target)) == master, (
                    "%s is installed to %s incorrectly: %s" % (master, target, fullpath(os.readlink(target))))
        else:
            raise

def delete_text(filename, *text):
    logger.info("deleting text from %s", filename)
    filename = fullpath(filename)
    text = "\n%s\n" % ("\n".join(text).strip("\n"))

    with open(filename, "r") as reader:
        contents = reader.read()

    if text in contents:
        contents = contents.replace(text, "\n")

        with open(filename, "w") as writer:
            # rewrite whole thing to prevent race conditions
            writer.write(contents)
    

def readfile(filename):
    with open(path(filename), "r") as reader:
        result = reader.read().strip()
    return result


def user_install():
    global logger

    os_specific.install_packages_user(os_dependencies)

    # install pip packages
    logger.info("Installing pip packages...")
    for dep in pip_dependencies:
        wrap_process.call("pip", ["pip", "install", "--user", dep])

    logger = logging.getLogger("u")
    logger.info("Doing user install...")

    for filename in ensure_nonexistant:
        filename = fullpath(filename)
        basename = os.path.basename(filename)
        dirname = os.path.dirname(filename)
        target = os.path.join(dirname, ".__dotfiles_deleted_%s_%s_" % (basename, int(time.time())))
        logger.info("moving %s to %s", filename, target)
        try:
            os.rename(filename, target)
        except OSError as e:
            if e.errno == 2:
                pass
            else:
                raise

    install_text("~/.vimrc", "source ~/.vimrc_global",
            before=True, prev_existance=False)
    install_text("~/.vimrc", "set nocompatible", 0600,
            before=True)
    install_file("files/vimrc", "~/.vimrc_global")
    install_file("files/vimrc_newsession", "~/.vimrc_newsession")

    install_text("~/.bashrc", "source ~/.bashrc_global", prev_existance=False)
    install_file("files/bashrc", "~/.bashrc_global")
    delete_text("~/.bashrc",
        "# enable programmable completion features (you don't need to enable",
        "# this, if it's already enabled in /etc/bash.bashrc and /etc/profile",
        "# sources /etc/bash.bashrc).",
        "if [ -f /etc/bash_completion ] && ! shopt -oq posix; then",
        "    . /etc/bash_completion",
        "fi"
    )

    install_text("~/.profile", readfile("files/profile_include"),
            prev_existance=False)
    install_text("~/.profile", "source ~/.profile_global")
    install_file("files/profile", "~/.profile_global")

    wrap_process.call("git submodule", ["git", "submodule", "init"], wd=projectroot)
    wrap_process.call("git submodule", ["git", "submodule", "update"], wd=projectroot)

    install_file("submodules/pathogen/autoload/pathogen.vim", "~/.vim/autoload/pathogen.vim")
    install_file("submodules/nerdtree/", "~/.vim/bundle/nerdtree/")
    install_file("submodules/ctrlp/", "~/.vim/bundle/ctrlp/")
    install_file("submodules/fugitive/", "~/.vim/bundle/fugitive/")
    install_file("submodules/vim-javascript/", "~/.vim/bundle/vim-javascript/")
    install_file("submodules/vim-indent-guides/", "~/.vim/bundle/vim-indent-guides/")
    install_file("submodules/vim-gitgutter/", "~/.vim/bundle/vim-gitgutter/")
    install_file("submodules/ceylon-vim/", "~/.vim/bundle/ceylon-vim/")
    install_file("submodules/rust.vim/", "~/.vim/bundle/rust.vim/")

    install_file("files/tmux.conf", "~/.tmux.conf")

    install_file("files/gitignore", "~/.gitignore")


    # git configuration
    realname = None
    email = None
    try:
        realname = gitconfig("user.name")
    except subprocess.CalledProcessError:
        pass
    try:
        email = gitconfig("user.email")
    except subprocess.CalledProcessError:
        pass
    if not realname:
        realname = raw_input("Need a realname for git: ")
        gitconfig("user.name", realname)
    if not email:
        email = raw_input("Need an email for git: ")
        gitconfig("user.email", email)

    gitconfig("alias.shortlog", "log --graph --pretty=format:'%Cred%h%Creset %cn -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' --abbrev-commit --date=relative")
    gitconfig("alias.find", r"""!sh -c 'git ls-files --full-name "\\*$1\\*"' -""")
    gitconfig("alias.ignored", "ls-files -o -i --exclude-standard")

    gitconfig("merge.defaultToUpstream", "true")

    gitconfig("color.branch", "auto")
    gitconfig("color.diff", "auto")
    gitconfig("color.interactive", "auto")
    gitconfig("color.status", "auto")
    gitconfig("color.grep", "auto")

    gitconfig("core.editor", "vim")
    gitconfig("core.excludesfile", os.path.expanduser("~/.gitignore"))

    gitconfig("push.default", "current")

    os_specific.customize()


def root_install():
    global logger
    logger = logging.getLogger("s")
    
    # install os packages
    logger.info("Installing OS packages...")

    try:
        # hack
        subprocess.check_call(["whereis", "xinit"])
    except (OSError, subprocess.CalledProcessError):
        pass
    else:
        os_dependencies.append("x11vnc")

    os_specific.install_packages_root(os_dependencies)

    logger.info("Installing pip...")
    wrap_process.call("get-pip", [sys.executable, path("get-pip.py")])
    wrap_process.call("pip", ["pip", "install", "--upgrade", "pip"])

    if os.path.exists("/etc/environment"):
        # install global environment defaults
        logger.info("Installing environment defaults...")
        install_text("/etc/environment", readfile("files/global_environ"))

    os_specific.customize_root()


def init_logging(mode):
    rootlogger = logging.getLogger()
    prefix = "\033[32m"
    formatter = logging.Formatter('[%(relativeCreated)6dms ' + highlight(mode) + ' %(levelname)s] ' +
                                        highlight('%(name)s') + ': %(message)s')
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
        subprocess.check_call(["sudo", sys.executable, sys.argv[0], "superuser"] + list(args))
        logger.info("running user portion")
        user_install(*args)
    elif mode == "bootstrap-root":
        os_specific.install_packages_root(os_dependencies)
    elif mode == "bootstrap-user":
        os_specific.install_packages_user(os_dependencies)
    elif mode == "user":
        user_install(*args)
    else:
        logger.error("mode must be one of 'superuser', 'init', 'user': %s", mode)

from dotfiles import os_specific

if __name__ == "__main__":
    main(*sys.argv[1:])
