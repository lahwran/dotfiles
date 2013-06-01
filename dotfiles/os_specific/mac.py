import os
import logging
logger = logging.getLogger("mac")

mac_mapping = {}

def package(func):
    mac_mapping[func.__name__] = func
    return func


@package
def git():
    assert which("git"), "please install git"

@package
def vim():
    assert which("vim"), "please install vim"

@package
def pip():
    assert which("pip"), "please install pip"

@package
def fail2ban():
    logger.warn("not installing fail2ban")

@package
def python_dev():
    logger.warn("not installing python-dev")

@package
def ntp_daemon():
    logger.info("mac comes with ntp configured")

@package
def build_essential():
    assert which("gcc"), "please install xcode"

@package
def tmux():
    assert which("tmux"), "please install tmux"

def install_packages(packages):
    for package in packages:
        func = mac_mapping[package.replace("-", "_")]
        func()


# this function from twisted.python.procutils, licensed MIT:
def which(name, flags=os.X_OK):
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

