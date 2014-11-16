import platform

class UnimplementedDistributionError(Exception):
    pass
et = UnimplementedDistributionError

if platform.system() == "Linux":
    from dotfiles.os_specific.linux import *
elif platform.system() == "Darwin":
    from dotfiles.os_specific.mac import *
else:
    raise et
