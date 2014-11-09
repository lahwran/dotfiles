import platform

class UnimplementedDistributionError(Exception):
    pass
et = UnimplementedDistributionError

if platform.system() == "Linux":
    from dotfiles.os_specific.linux import *
else:
    raise et
