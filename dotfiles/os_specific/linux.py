from dotfiles import wrap_process

debian_mapping = {
    "pip": "python-pip",
    "ntp-daemon": "ntp"
}


def install_packages(packages):
    deps = [debian_mapping.get(package, package) for package in packages]
    wrap_process.call("apt-get", ["apt-get", "install", "-y"] + deps)
