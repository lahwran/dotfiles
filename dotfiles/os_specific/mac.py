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
    "vim": ["vim"],
    "tmux": ["tmux"],
    "tig": ["tig"],
}
brew_tap = [
    "caskroom/fonts",
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
    "skype",
    "audacity",
    "quassel-client",
    "font-dejavu-sans"
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

p_call = subprocess.call
p_check = subprocess.check_call


def customize():
    from dotfiles.install import (install_file,
            install_dir, install_text, install_copy, path, readfile,
            fullpath)

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
    n_r |= set_defaults("-g", "com.apple.keyboard.fnState", True)

    # bettertouchtool maximize sizes
    btt = "com.hegenberg.BetterTouchTool"
    changed_btt = set_defaults(btt, "windowLeftCornerMaximizePercent", 0.3)
    changed_btt |= set_defaults(btt, "windowLeftMaximizePercent", 0.3)

    changed_btt |= set_defaults(btt, "windowRightCornerMaximizePercent", 0.7)
    changed_btt |= set_defaults(btt, "windowRightMaximizePercent", 0.7)
    changed_btt |= set_defaults(btt, "windowSnappingEnabled", True)
    changed_btt |= set_defaults(btt, "launchOnStartup", True)
    changed_btt |= set_defaults(btt, "showicon", False)

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
        """, True)
        set_defaults(btt, "currentStore", "Dotfiles-Installed")
        path = find_file("BetterTouchTool.app")
        if path:
            p_call(["open", path])

    n_r |= changed_btt

    if install_dir("~/Library/Application Support/audacity"):
        with open(fullpath("~/Library/Application Support/"
                    + "audacity/audacity.cfg"), "w") as writer:
            writer.write(readfile("files/audacity.cfg")
                        .replace("HOMEDIRECTORY/", fullpath("~/")))

    n_r |= install_defaults("com.ragingmenace.MenuMeters", "files/menumeters")
    n_r |= set_defaults("com.googlecode.iterm2", "PrefsCustomFolder",
                                path("files/iterm2/"))
    n_r |= set_defaults("com.googlecode.iterm2",
                            "LoadPrefsFromCustomFolder", True)

    # time until initial key repeat
    n_r |= set_defaults("-g", "InitialKeyRepeat", 35)

    # time between key repeats
    n_r |= set_defaults("-g", "KeyRepeat", 2)

    # set natural scroll - not apple's "unnatural" scroll
    n_r |= set_defaults("-g", "com.apple.swipescrolldirection", False)
    
    # disable yucky automatic spell stuff
    n_r |= set_defaults("-g", "NSAutomaticSpellingCorrectionEnabled", False)
    n_r |= set_defaults("-g", "WebAutomaticSpellingCorrectionEnabled", False)
    n_r |= set_defaults("-g", "NSAutomaticDashSubstitutionEnabled", False)
    n_r |= set_defaults("-g", "NSAutomaticQuoteSubstitutionEnabled", False)

    if n_r:
        # set some fun replacements - <3 to unicodeheart in particular
        n_r |= set_defaults("-g", "NSUserDictionaryReplacementItems",
                    readfile("files/mac_user_dictionary"), True)
        n_r |= set_defaults("-g", "NSUserReplacementItems",
                    readfile("files/mac_user_replacements"), True)
        n_r |= set_defaults("-g", "NSUserReplacementItemsEnabled", True)

    # disable app nap! app nap is evil
    n_r |= set_defaults("-g", "NSAppSleepDisabled", True)

    coreutils = glob.glob("/usr/local/Cellar/coreutils/*/libexec/gnubin")
    assert len(coreutils)
    newest_coreutils = max(coreutils)

    openssl = glob.glob("/usr/local/Cellar/openssl/*/bin")
    assert len(openssl)
    newest_openssl = max(openssl)

    install_text("~/.bashrc", "source ~/.bashrc_mac")
    install_text("~/.bashrc", "source ~/.bashrc_misc")
    install_file("files/bashrc_mac", "~/.bashrc_mac")
    with open(fullpath("~/.bashrc_misc"), "w") as writer:
        writer.write('export PATH="%s:%s:$PATH"\n'
            % (newest_coreutils, newest_openssl))

    if n_r:
        logger.warn("Changed internal stuff, won't take effect until reboot!"
                    + " sorry :(")


def customize_root():
    # don't go into true sleep from display sleep for at least three hours,
    # even on battery
    p_call(["pmset", "-b", "sleep", "180"]) # minutes
    # don't go into sleep on power automatically ever
    p_call(["pmset", "-c", "sleep", "0"])
    p_call(["pmset", "-u", "sleep", "0"])

    # go into standby mode fairly soon once in sleep, because
    # standby mode allows tossing the filevault key
    p_call(["pmset", "-a", "standby", "1"])
    p_call(["pmset", "-a", "standbydelay", "300"]) # seconds
    # there's a big flashy warning about this option in the manual page
    # for pmset. 25 is a supported value.
    # setting this assumes hibernatefile is set, which it seems to be by
    # default.
    p_call(["pmset", "-a", "hibernatemode", "25"])
    # once the computer goes into hibernate mode, unload filevault. to resume
    # from this requires _two_ passwords, filevault and login.
    p_call(["pmset", "-a", "destroyfvkeyonstandby", "1"])


def find_file(name):
    output = p_output(["mdfind", name]).split("\n")
    endswith = [x for x in output if x.endswith("/" + name)]
    if not endswith:
        return None
    return endswith[0]


def install_defaults(app, filename):
    from dotfiles.install import readfile
    if p_call(["defaults", "read", app], **dnull) != 0:
        p_check(["defaults", "write", app, readfile(filename)])
        return True
    return False


def set_defaults(domain, key, value, is_defaults_data=False):
    if is_defaults_data:
        v = []
        f = lambda x: None
        t = lambda x: x
    elif type(value) == bool:
        v = ["-bool"]
        f = int
        t = lambda x: "true" if x else "false"
    elif type(value) in [long, int]:
        v = ["-integer"]
        f = int
        t = str
    elif type(value) == float:
        v = ["-float"]
        f = float
        t = str
    else:
        v = ["-string"]
        f = lambda x: x
        t = lambda x: x


    if f(p_output(["defaults", "read", domain, key],
            stderr=devnull).strip()) != value:
        p_check(["defaults", "write", domain, key] + v + [t(value)])
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

