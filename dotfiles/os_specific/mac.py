import os
import logging
import subprocess
import re
import time

from dotfiles import wrap_process
from contextlib import contextmanager

logger = logging.getLogger("mac")

brew_mapping = {
    "git": ["git"],
    "vim": ["vim"],
    "tmux": ["tmux"],
    "tig": ["tig"],
}
brew_install = [
    "caskroom/cask/brew-cask",
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
]
cask_install = [
    "google-chrome",
    "seil",
    "iterm2",
    "spacemonkey",
    "crashplan",
    "little-snitch",
    "menumeters",
    "bettertouchtool",
]
devnull = open("/dev/null", "w")


def base_compilers():
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


def install_packages_user(packages):
    packages = [package.replace("-", "_") for package in packages]

    base_compilers()

    if not which("brew"):
        wrap_process.call("curl", ["curl", "-fsSLo", "/tmp/homebrew.rb",
            "https://raw.githubusercontent.com/Homebrew/install/master/install"])
        wrap_process.call("homebrew",
                ["/bin/sh", "-c", "echo | ruby /tmp/homebrew.rb"])
        open("/usr/local/.can-cask", "w").write(
                "Automatically installed homebrew, should be safe to cask")

    deps = []
    for package in packages:
        if package not in brew_mapping:
            logger.warn("Skipping non-homebrew package: %s", package)
            continue
        deps.extend(brew_mapping[package])
    deps.extend(brew_install)

    wrap_process.call("homebrew", ["brew", "install"] + deps)

    if os.path.exists("/usr/local/.can-cask"):
        for cask in cask_install:
            wrap_process.call("brew-cask", ["brew", "cask", "install", cask])



def install_packages_root(packages):
    pass


def customize():
    from dotfiles.install import install_file

    seil = "/Applications/Seil.app/Contents/Library/bin/seil"
    if os.path.exists(seil):
        wrap_process.call("seil", [seil, "set", "keycode_capslock", "53"])


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

