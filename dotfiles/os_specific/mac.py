import os
import logging
import subprocess
import re
import time
import pwd
import glob

from dotfiles import wrap_process
from contextlib import contextmanager

logger = logging.getLogger("mac")

brew_mapping = {
    "git": ["git"],
    "vim": ["neovim"],
    "tmux": ["tmux"],
    "tig": ["tig"],
}
brew_tap = [
    "caskroom/fonts",
    "neovim/homebrew-neovim",
]
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
    "mtr",
    "socat",
    "pypy",
    "ceylon",
]
cask_install = [
    "google-chrome",
    "seil",
    "iterm2",
    "little-snitch",
    "audacity",
    "font-dejavu-sans",
    "java",
    "grandperspective",
    "firefox",
    "gimp",
    "insomniax",
    "xquartz",
]
devnull = open("/dev/null", "w")
dnull = {"stdout": devnull, "stderr": devnull}


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

    for tap in brew_tap:
        wrap_process.call("homebrew", ["brew", "tap", tap])

    deps = []
    for package in packages:
        if package not in brew_mapping:
            logger.warn("Skipping non-homebrew package: %s", package)
            continue
        deps.extend(brew_mapping[package])
    deps.extend(brew_install)

    if "neovim" in deps:
        # this is to add --HEAD
        deps.remove("neovim")
        wrap_process.call("homebrew", ["brew", "install", "--HEAD", "neovim"])

    wrap_process.call("homebrew", ["brew", "install"] + deps)

    if os.path.exists("/usr/local/.can-cask"):
        for cask in cask_install:
            wrap_process.call("brew-cask",
                            ["brew", "cask", "install", cask])


def install_packages_root(packages):
    from dotfiles.install import install_text
    install_text("/etc/shells", "/usr/local/bin/bash")


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


def customize():
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

def customize_root():
    # don't go into true sleep from display sleep for at least three hours,
    # even on battery
    p_call(["pmset", "-b", "sleep", "180"]) # minutes
    # don't go into sleep on power automatically ever
    p_call(["pmset", "-c", "sleep", "0"])
    p_call(["pmset", "-u", "sleep", "0"])

    # DISABLED (was causing issues with session loss):
    # go into standby mode fairly soon once in sleep, because
    # standby mode allows tossing the filevault key
    #p_call(["pmset", "-a", "standby", "0"])
    #old: p_call(["pmset", "-a", "standbydelay", "300"]) # seconds
    #p_call(["pmset", "-a", "autopoweroff", "0"])
    #old: p_call(["pmset", "-a", "autopoweroff", "5"])

    # there's a big flashy warning about this option in the manual page
    # for pmset. 25 is a supported value, that empties ram.
    # setting this assumes hibernatefile is set, which it seems to be by
    # default.
    # DISABLED - was causing issues with session loss.
    #p_call(["pmset", "-a", "hibernatemode", "0"]) #"25"])
    # once the computer goes into hibernate mode, unload filevault. to resume
    # from this requires _two_ passwords, filevault and login.
    # DISABLED - was causing issues with session loss.
    #p_call(["pmset", "-a", "destroyfvkeyonstandby", "0"])


def find_file(name):
    output = p_output(["mdfind", name]).split("\n")
    endswith = [x for x in output if x.endswith("/" + name)]
    if not endswith:
        return None
    return endswith[0]


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

"""
def disable_default_escape_action():
    # first, detect available keyboard vendorid/productid pairs
    # note: this is fragile.
    hidinfo = p_output(["ioreg", "-n", "IOHIDKeyboard", "-r"])
    matches = re.finditer(" *[|] *\"(VendorID|ProductID)\" = ([0-9]+)",
            hidinfo)
    hid_info = [(match.group(1), match.group(2))
            for match in matches]
    assert len(hid_info), ("ioreg-based plugged-in-keyboard snooping is "
                           "broken, please fix! :(")

    vendorids = []
    productids = []
    for key, value in hid_info:
        # this assumes that they're alternating. if they are not,
        # it will silently break :<
        # pretty sure they will be, though.
        if key == "VendorID":
            vendorids.append(value)
        else:
            productids.append(value)
    product_pairs = zip(vendorids, productids)
    logger.debug("Keyboard product pairs: %r", product_pairs)

    # this maps from 0 (escape) to -1 (no action), and disables any other
    # osx-internal modifier key mappings
    data = '''
        (
            {
                HIDKeyboardModifierMappingDst = -1;
                HIDKeyboardModifierMappingSrc = 0;
            }
        )
    '''

    # next, for each of those keyboard pairs, set the
    changed_anything = False
    name = "com.apple.keyboard.modifiermapping.%s-%s-0"
    for pair in product_pairs:
        prefname = name % pair
        #if p_call(["defaults", "read", "-g", prefname], **dnull) == 0:
        #    # assume already set up and skip
        #    continue
        changed_anything = True
        set_defaults("-g", prefname, data)

    return changed_anything
    """


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

