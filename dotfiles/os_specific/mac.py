import os
import logging
import subprocess
import re
import time
import pwd

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
    from dotfiles.install import install_text
    install_text("/etc/shells", "/usr/local/bin/bash")


def p_output(*args, **kwargs):
    try:
        return subprocess.check_output(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        return e.output

p_call = subprocess.call
p_check = subprocess.check_call


def customize():
    from dotfiles.install import (install_file,
            install_dir, install_text, install_copy)

    n_r = False

    seil = "/Applications/Seil.app/Contents/Library/bin/seil"
    if os.path.exists(seil):
        # enable capslock-as-escape
        wrap_process.call("seil", [seil, "set", "keycode_capslock", "53"])
        wrap_process.call("seil", [seil, "set", "enable_capslock", "1"])

    n_r |= disable_default_escape_action()

    # set shell to homebrew-installed bash
    if pwd.getpwuid(os.getuid()).pw_shell != "/usr/local/bin/bash":
        subprocess.call(["chsh", "-s", "/usr/local/bin/bash"])

    # set function keys as function keys!
    n_r |= set_defaults("-g", "com.apple.keyboard.fnState", "1")

    # bettertouchtool maximize sizes
    btt = "com.hegenberg.BetterTouchTool"
    changed_btt = set_defaults(btt, "windowLeftCornerMaximizePercent", "0.3")
    changed_btt |= set_defaults(btt, "windowLeftMaximizePercent", "0.3")

    changed_btt |= set_defaults(btt, "windowRightCornerMaximizePercent", "0.7")
    changed_btt |= set_defaults(btt, "windowRightMaximizePercent", "0.3")
    changed_btt |= set_defaults(btt, "windowSnappingEnabled", "1")

    # bettertouchtool preset
    if p_call(["defaults", "read", btt, "currentStore"], **dnull) != 0:
        install_dir("~/Library/Application Support/BetterTouchTool")
        install_copy("files/bettertouchtool_preset",
            "~/Library/Application Support/BetterTouchTool/bttdata_dotfiles")
        set_defaults(btt, "presets", """
            (
                {
                    fileName = bttdata_dotfiles;
                    presetName = "Dotfiles-Installed";
                }
            )
        """)
        set_defaults(btt, "currentStore", "Dotfiles-Installed")
        path = find_file("BetterTouchTool.app")
        if path:
            p_call(["open", path])

    changed_btt |= set_defaults(btt, "", "1")

    if n_r:
        logger.warn("Changed internal stuff, won't take effect until reboot!"
                    + " sorry :(")


def find_file(name):
    output = p_output(["mdfind", name]).split("\n")
    endswith = [x for x in output if x.endswith("/" + name)]
    if not endswith:
        return None
    return endswith[0]


def set_defaults(domain, key, value):
    if p_output(["defaults", "read", domain, key], **dnull).strip() != value:
        p_check(["defaults", "write", domain, key, value])
        return True
    return False


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

    # this maps from 0 (escape) to -1 (no action), and disables any other
    # osx-internal modifier key mappings
    data = '''
        (
            {
                HIDKeyboardModifierMappingDst="-1";
                HIDKeyboardModifierMappingSrc=0;
            }
        )
    '''

    # next, for each of those keyboard pairs, set the
    changed_anything = False
    name = "com.apple.keyboard.modifiermapping.%s-%s-0"
    for pair in product_pairs:
        prefname = name % pair
        if p_call(["defaults", "read", "-g", prefname], **dnull) == 0:
            # assume already set up and skip
            continue
        changed_anything = True
        p_check(["defaults", "write", "-g", "prefname", data])

    return changed_anything


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

