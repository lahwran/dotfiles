from dotfiles import wrap_process

debian_mapping = {
    "git": "git",
    "vim": "vim",
    "pip": "python-pip",
    "fail2ban": "fail2ban",
    "build-essential": "build-essential",
    "python-dev": "python-dev",
    "ntp-daemon": "ntp"
}


def install_packages(packages):
    deps = [debian_mapping[package] for package in packages]
    wrap_process.call("apt-get", ["apt-get", "install", "-y"] + deps)
