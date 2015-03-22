import logging

from dotfiles import wrap_process
from dotfiles.install import path

debian_mapping = {
    "ntp-daemon": ["ntp"],
    "vim": ["vim"],
    "git": ["git"],
    "tig": ["tig"],
    "tmux": ["tmux"],
    "fail2ban": ["fail2ban"],
    "python-dev": ["python-dev"],
}

debian_install = [
    "build-essential",
]

logger = logging.getLogger("-")

def install_packages_user(packages):
    pass

def customize():
    wrap_process.call("fix_ubuntu.sh", [path("bin/fix_ubuntu.sh")])

def customize_root():
    pass

def install_packages_root(packages):
    deps = []
    for package in packages:
        if package not in debian_mapping:
            logger.warn("Skipping non-debian package: %s", package)
            continue
        deps.extend(debian_mapping[package])
    deps.extend(debian_install)
    wrap_process.call("apt-get", ["apt-get", "install", "-y"] + deps)
