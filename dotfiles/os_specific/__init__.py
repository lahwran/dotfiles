import platform

class UnimplementedDistributionError(Exception):
    pass
et = UnimplementedDistributionError

if platform.system() == "Linux":
    dist, ver, codename = platform.linux_distribution()
    if dist == "Ubuntu":
        from dotfiles.os_specific.ubuntu import *
    else:
        raise et
else:
    raise et
