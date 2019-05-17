#!/usr/bin/env python

import platform
import json
import subprocess
import sys
import logging
import datetime
import os
import stat
import time
import shutil
import socket
import math
import random
import hashlib
import re


import os
import logging
import subprocess
import re
import time
import pwd
import glob

from dotfiles import wrap_process
from contextlib import contextmanager

from dotfiles.highlight import highlight
from dotfiles import wrap_process

assert (0644 ==
        stat.S_IRUSR |
        stat.S_IWUSR |
        stat.S_IRGRP |
        stat.S_IROTH), "os is insane"

logger = logging.getLogger("-")

os_dependencies = [
    "neovim",
    "git",
    "tmux",
    "tig",
]
debian_mapping = {
    "ntp-daemon": ["ntp"],
    "vim": ["vim"],
    "git": ["git"],
    "tig": ["tig"],
    "tmux": ["tmux"],
    "fail2ban": ["fail2ban"],
    "python-dev": ["python-dev"],
}
brew_install = [
    "coreutils",
    "bash",
    "ffmpeg",
    "htop-osx",
    "lame",
    "mplayer",
    "nmap",
    "openssl",
    "watch",
    "wget",
    "mtr",
    "socat",
    "findutils",
    "pyenv",
    "neovim",
]
cask_install = [
    "iterm2",
    "little-snitch",
    "font-dejavu-sans",
    "grandperspective",
    "firefox",
    "gimp",
    "karabiner-elements",
    "bettertouchtool",
    "alfred",
    "hyperswitch",
    "switchresx",
    "keycastr",
    "menumeters",
]
debian_install = [
    "build-essential",
    "zsh",
    "fail2ban",
    "python-dev",
    "ntp",
]

pip_dependencies = [
    "pip",
    "virtualenv",
    "pytest",
    "twisted",
    #"blessings",
    "blessed",
    "watchdog",
    "chardet",
    "decorator",
    "flask",
    "husl",
    #"ptpython",
    #"prompt_toolkit",
    "pudb",
    "py",
    "requests",
    "treq",
    "klein",
    "numpy",
    "urwid",
    "bpython",
    "hsluv",
    "jupyter",
    "lxml",
    "incremental",
    "six",
    "pytest-regtest",
    "pynvim",
    "python-pcre",
]
legacy_pip_remove = [
    "neovim",
]
legacy_pip_dependencies = [
    "pynvim",
]

ensure_nonexistant = [
    "~/.bash_logout",
    "~/.vim/bundle/racer/"
]



brew_tap = [
    "homebrew/cask-fonts",
]
devnull = open("/dev/null", "w")
dnull = {"stdout": devnull, "stderr": devnull}






def p_output(*args, **kwargs):
    try:
        return subprocess.check_output(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        return e.output

def p_call(command, *a, **kw):
    logger.info("call: %s", " ".join((x if " " not in x else repr(x)) if len(x) < 35 else repr(x[:33] + "...") for x in command))
    return subprocess.call(command, *a, **kw)

def p_check(command, *a, **kw):
    logger.info("check: %s", " ".join((x if " " not in x else repr(x)) if len(x) < 35 else repr(x[:33] + "...") for x in command))
    return subprocess.check_call(command, *a, **kw)

class linux_specific:
    @classmethod
    def install_packages_user(cls, packages):
        pass

    @classmethod
    def customize(cls):
        wrap_process.call("fix_ubuntu.sh", [path("bin/fix_ubuntu.sh")])

    @classmethod
    def customize_root(cls):
        pass

    @classmethod
    def install_packages_root(cls, packages):
        deps = []
        deps.extend(packages)
        deps.extend(debian_install)
        wrap_process.call("apt-get", ["apt-get", "install", "-y"] + deps)

class mac_specific:
    @classmethod
    def base_compilers(cls):
        try:
            subprocess.check_call(["xcode-select", "-p"],
                stdout=devnull, stderr=devnull)
            return
        except (OSError, subprocess.CalledProcessError):
            pass

        logger.info("Asking for xcode install...")
        subprocess.check_call(["xcode-select", "--install"])

        while True:
            try:
                subprocess.check_call(["xcode-select", "-p"])
                logger.info("Xcode installed, continuing")
                return
            except (OSError, subprocess.CalledProcessError):
                pass
            logger.info("Xcode not installed, waiting for 2 seconds")
            time.sleep(2)


    @classmethod
    def install_packages_user(cls, packages):
        packages = [package.replace("-", "_") for package in packages]

        cls.base_compilers()

        if not which_twisted("brew"):
            wrap_process.call("curl", ["curl", "-fsSLo", "/tmp/homebrew.rb",
                "https://raw.githubusercontent.com/Homebrew/install/master/install"])
            wrap_process.call("homebrew",
                    ["/bin/sh", "-c", "echo | ruby /tmp/homebrew.rb"])
            open("/usr/local/.can-cask", "w").write(
                    "Automatically installed homebrew, should be safe to cask")

        for tap in brew_tap:
            wrap_process.call("homebrew", ["brew", "tap", tap])

        deps = []
        deps.extend(packages)
        deps.extend(brew_install)

        wrap_process.call("homebrew", ["brew", "install"] + deps)
        wrap_process.call("brew-cask",
                        ["brew", "cask", "install"] + cask_install)

    @classmethod
    def install_packages_root(cls, packages):
        install_text("/etc/shells", "/usr/local/bin/bash")


    @classmethod
    def customize(cls):
        from dotfiles.install import (install_file,
                install_dir, install_text, install_copy, path, readfile,
                fullpath)

        n_r = False

        # set shell to homebrew-installed bash
        if pwd.getpwuid(os.getuid()).pw_shell != "/usr/local/bin/bash":
            subprocess.call(["chsh", "-s", "/usr/local/bin/bash"])

        # set function keys as function keys!
        n_r |= set_defaults("-g", "com.apple.keyboard.fnState", True)

        # disable automatic app termination - I've never actually seen this happen, but
        # the setting's existence is scary
        n_r |= set_defaults("-g", "NSDisableAutomaticTermination", True)

        # Disable window animations - they royally screw up window management apps, and are
        # fairly slow on most apps to boot
        n_r |= set_defaults("-g", "NSAutomaticWindowAnimationsEnabled", False, typed=True)

        # take a while to move windows between displays, so edge-of-screen stuff isn't annoying
        n_r |= set_defaults("com.apple.dock", "workspaces-edge-delay", 4.0, typed=True)

        n_r |= set_defaults("com.apple.screencapture", "location",
                fullpath("~/Screenshots"), typed=True)
        n_r |= set_defaults("com.apple.screencapture", "type", "png", typed=True)

        coreutils = glob.glob("/usr/local/Cellar/coreutils/*/libexec/gnubin")
        assert len(coreutils)
        newest_coreutils = max(coreutils)

        openssl = glob.glob("/usr/local/Cellar/openssl/*/bin")
        assert len(openssl)
        newest_openssl = max(openssl)

        install_text("~/.bashrc", "source ~/.bashrc_mac")
        install_text("~/.bashrc", "source ~/.bashrc_misc", before=True)
        install_file("files/bashrc_mac", "~/.bashrc_mac")
        with open(fullpath("~/.bashrc_misc"), "w") as writer:
            writer.write('export PATH="%s:%s:$PATH"\n'
                % (newest_coreutils, newest_openssl))

    @classmethod
    def customize_root(cls):
        pass

if platform.system() == "Linux":
    os_specific = linux_specific
elif platform.system() == "Darwin":
    os_specific = mac_specific


def set_defaults(domain, key, value, is_defaults_data=False, typed=False):
    if is_defaults_data:
        typed = False
        f = lambda x: None
        t = lambda x: x
    elif isinstance(value, basestring):
        v = []
        f = lambda x: x
        t = lambda x: x
    elif type(value) == bool:
        v = ["-bool"]
        f = int
        if typed:
            t = lambda x: "true" if x else "false"
        else:
            t = lambda x: "1" if x else "0"
    elif type(value) in [long, int]:
        v = ["-int"]
        f = int
        t = str
    elif type(value) == float:
        v = ["-float"]
        f = float
        t = str
    else:
        assert False

    if not typed:
        v = []

    output = p_output(["defaults", "read", domain, key],
            stderr=devnull).strip()

    if output != '' and f(output) != value:
        print "output: %r (<- %r) != %r (-> %r)" % (f(output), output, value, t(value))
        p_check(["defaults", "write", domain, key] + v + [t(value)])
        return True
    return False


# this function from twisted.python.procutils, licensed MIT:
def which_twisted(name, flags=os.X_OK):
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result

_find_unsafe = re.compile(r'[^\w@%+=:,./-]').search

def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"

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
        before=False, prev_existence=True):
    filename = fullpath(filename)
    try:
        with open(filename, "r") as reader:
            contents = reader.read()
    except IOError as e:
        if e.errno == 2 and not prev_existence:
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
    master = path(master)
    target = fullpath(target)

    install_dir(os.path.dirname(target), log=False)

    try:
        os.symlink(master, target)
        logger.info("installed %s -> %s", master, target)
    except OSError as e:
        if e.errno == 17:
            assert fullpath(os.readlink(target)) == master, (
                    "%s is installed to %s incorrectly: %s" % (master, target, fullpath(os.readlink(target))))
        else:
            raise


def ensure_link(link_target, to_create):
    to_create = fullpath(to_create)
    link_target = fullpath(link_target)

    install_dir(os.path.dirname(to_create), log=False)
    try:
        os.symlink(link_target, to_create)
        logger.info("linking %s as %s", link_target, to_create)
    except OSError as e:
        if e.errno == 17:
            assert fullpath(os.readlink(to_create)) == link_target, (
                    "%s is installed to %s incorrectly: %s" % (link_target, to_create, fullpath(os.readlink(to_create))))
        else:
            raise


def delete_text(filename, *text):
    filename = fullpath(filename)
    text = "\n%s\n" % ("\n".join(text).strip("\n"))

    with open(filename, "r") as reader:
        contents = reader.read()

    if text in contents:
        logger.info("deleting text from %s", filename)
        contents = contents.replace(text, "\n")

        with open(filename, "w") as writer:
            # rewrite whole thing to prevent race conditions
            writer.write(contents)
    

def readfile(filename):
    with open(path(filename), "r") as reader:
        result = reader.read().strip()
    return result


def host_colors(hostname):
    hash = int(hashlib.sha256(hostname).hexdigest(), 16) + 3

    r = random.Random(hash)
    rc = r.choice

    # interesting colors are:
    # 31: red
    # 32: green
    # 33: yellow
    # 34: blue
    # 35: purple
    # 36: aqua
    # 37: white
    # 38: nothing
    # have to prefer one by 2x, so prefer green rather than white
    colors = [str(x) for x in range(32, 37)]
    colors_with_none = [str(x) for x in range(32, 39)]
    bold = "1;"

    d = {}
    d["user"] = rc("33 34 35 37".split())
    d["host"] = bold + rc("32 33 34 35 37 38".split())
    d["at_host"] = bold + rc(colors)
    d["at_path"] = rc(["38", "38", "38", "37", "37", "36", "34", "33"])
    d["path"] = rc(["32", "33", "34", "36"])
    d["symbol"] = "38"

    return "\n".join("PROMPTCOLOR_%s='%s'" % (key, value) for key, value in sorted(d.items()))



def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def check_py(name, found, sites, check_version=None):
    binary = which(name)
    if not binary:
        return
    if check_version is not None:
        out = json.loads(subprocess.check_output([binary, '-c', 'import sys, json; json.dump(list(sys.version_info), sys.stdout)']))
        if out[:len(check_version)] != check_version:
            return
    out = subprocess.check_output([binary, '-m', 'site', '--user-site']).strip()
    if out in sites:
        found.remove(sites[out])
    sites[out] = binary
    found.append(binary)

def user_install():
    global logger
    sites2 = {}
    python2s = []
    check_py("python", python2s, sites2, check_version=[2, 7])

    sites3 = {}
    python3s = []
    for x in range(5, 10):
        check_py("python3.{}".format(x), python3s, sites3)
    check_py("python3", python3s, sites3)
    check_py("python", python3s, sites3, check_version=[3])
    check_py("pypy3", python3s, sites3)

    if which("wget"):
        wrap_process.call("wget", ["wget", "https://bootstrap.pypa.io/get-pip.py", "-O", path("get-pip.py")])
    else:
        wrap_process.call("curl", ["curl", "https://bootstrap.pypa.io/get-pip.py", "-o", path("get-pip.py")])

    if not os.path.exists("~/.py2_pip"):
        for python2 in python2s:
            # this is dumb, kill py2 when
            install_dir("~/.py2_pip")
            wrap_process.call(python2, [python2, path("get-pip.py"), "--user"])
            logger.info("Installing pip packages (py2: {})...".format(python2.rsplit("/")[-1]))
            wrap_process.call("pip2", [python2, "-m", "pip", "uninstall"] + legacy_pip_remove)
            wrap_process.call("pip2", [python2, "-m", "pip", "install", "--user"] + legacy_pip_dependencies)
    for python3 in python3s:
        bn = python3.strip("/").rpartition("/")[-1]
        wrap_process.call(python3, [python3, path("get-pip.py"), "--user", "--upgrade"])
        # install pip packages
        logger.info("Installing pip packages (py3: {})...".format(python3.rsplit("/")[-1]))
        wrap_process.call(bn, [python3, "-m", "pip", "install", "--user", "--upgrade", "pip", "setuptools"])
        wrap_process.call(bn, [python3, "-m", "pip", "install", "--user", "--upgrade"] + pip_dependencies)
        wrap_process.call(bn, [python3, "-m", "pip", "install", "--user", "--upgrade", "--editable", path("packages/at/")])


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

    install_dir("~/.vim")
    ensure_link("~/.vim", "~/.nvim")
    ensure_link("~/.vim", "~/.config/nvim/")

    install_text("~/.nvimrc", "source ~/.vimrc_global",
            before=True, prev_existence=False)
    install_text("~/.config/nvim/init.vim", "source ~/.vimrc_global",
            before=True, prev_existence=False)
    install_text("~/.vimrc", "source ~/.vimrc_global",
            before=True, prev_existence=False)
    install_text("~/.vimrc", "set nocompatible", 0600,
            before=True)
    install_file("files/vimrc", "~/.vimrc_global")
    install_file("files/vimrc_newsession", "~/.vimrc_newsession")

    install_text("~/.bashrc", "DOTFILES_DIR=%s" % (quote(path(".")),),
            prev_existence=False, before=True)
    hostname = socket.gethostname().partition(".")[0]
    install_text("~/.bashrc", host_colors(hostname), before=True)
    install_text("~/.bashrc", "source ~/.bashrc_global")
    install_text("~/.bashrc", 'PATH="%s:$PATH"\n' % (path("bin/"),))
    install_text("~/.bashrc", "trap '' INT TSTP", before=True)
    install_text("~/.bashrc", "trap - INT TSTP")
    install_text("~/.profile", "trap '' INT TSTP", before=True, prev_existence=False)
    install_text("~/.profile", "trap - INT TSTP")
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
            prev_existence=False)
    install_text("~/.profile", "source ~/.profile_global")
    install_file("files/profile", "~/.profile_global")

    wrap_process.call("git submodule", ["git", "submodule", "init"], wd=projectroot)
    wrap_process.call("git submodule", ["git", "submodule", "update"], wd=projectroot)

    install_file("submodules/pathogen/autoload/pathogen.vim", "~/.vim/autoload/pathogen.vim")
    install_file("submodules/jinja2/", "~/.vim/bundle/jinja2/")
    install_file("submodules/nerdtree/", "~/.vim/bundle/nerdtree/")
    install_file("submodules/ctrlp/", "~/.vim/bundle/ctrlp/")
    install_file("submodules/fugitive/", "~/.vim/bundle/fugitive/")
    install_file("submodules/vim-javascript/", "~/.vim/bundle/vim-javascript/")
    install_file("submodules/vim-indent-guides/", "~/.vim/bundle/vim-indent-guides/")
    install_file("submodules/vim-gitgutter/", "~/.vim/bundle/vim-gitgutter/")
    install_file("submodules/ceylon-vim/", "~/.vim/bundle/ceylon-vim/")
    install_file("submodules/rust.vim/", "~/.vim/bundle/rust.vim/")
    install_file("submodules/syntastic/", "~/.vim/bundle/syntastic/")
    install_file("submodules/YouCompleteMe/", "~/.vim/bundle/YouCompleteMe/")
    install_file("submodules/gundo/", "~/.vim/bundle/gundo/")
    install_file("submodules/vim-multiple-cursors/", "~/.vim/bundle/vim-multiple-cursors/")
    install_file("submodules/vim-jsx/", "~/.vim/bundle/vim-jsx/")
    install_file("submodules/vim-auto-save/", "~/.vim/bundle/vim-auto-save/")
    install_file("submodules/vim-markology/", "~/.vim/bundle/vim-markology/")
    install_file("submodules/vim-terraform/", "~/.vim/bundle/vim-terraform/")
    install_file("submodules/xonsh-vim/", "~/.vim/bundle/xonsh-vim/")

    install_file("files/tmux.conf", "~/.tmux.conf")

    install_file("files/gitignore", "~/.gitignore")
    for filename in os.listdir(path("files/syntax/")):
        install_file("files/syntax/"+filename, "~/.vim/syntax/"+filename)


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

    os_specific.install_packages_root(os_dependencies)

    if os.path.exists("/etc/environment"):
        # install global environment defaults
        logger.info("Installing environment defaults...")
        install_text("/etc/environment", readfile("files/global_environ"))

    os_specific.customize_root()


def init_logging(mode):
    rootlogger = logging.getLogger()
    prefix = "\033[32m"
    rootlogger.setLevel(logging.DEBUG)
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    logfile = open(path(".install_%s.log" % today_str), "a")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(highlight(mode) + ' %(levelname)s ' +
                                highlight('%(name)s') + ': %(message)s'))
    rootlogger.addHandler(handler)

    handler = logging.StreamHandler(logfile)
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)6dms ' + highlight(mode) + ' %(levelname)s] ' +
                                        highlight('%(name)s') + ': %(message)s'))

    rootlogger.addHandler(handler)

    logger.info("Logging initialized")

def main(mode="user", *args):
    init_logging(mode)

    if mode == "superuser":
        root_install(*args)
    elif mode == "init":
        logger.info("running root portion")
        subprocess.check_call(["sudo", sys.executable, sys.argv[0], "superuser"] + list(args))
        logger.info("running user portion")
        os_specific.install_packages_user(os_dependencies)
        user_install(*args)
    elif mode == "bootstrap-root":
        os_specific.install_packages_root(os_dependencies)
    elif mode == "bootstrap-user":
        os_specific.install_packages_user(os_dependencies)
    elif mode == "user":
        os_specific.install_packages_user(os_dependencies)
        user_install(*args)
    elif mode == "fake":
        logger.warn("ON REQUEST, NOT ACTUALLY RUNNING INSTALL. please verify that only config files were changed in git.")
    else:
        logger.error("mode must be one of 'superuser', 'init', 'user': %s", mode)
    if os.path.exists(path(".do_sync")):
        subprocess.call([path(".autocommit.sh")], cwd=projectroot)
        with open(fullpath("~/.last_dotfiles_run"), "w") as writer:
            git = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=projectroot)
            writer.write(git)
        subprocess.call([path("bin/check_run")], cwd=projectroot)

if __name__ == "__main__":
    main(*sys.argv[1:])
