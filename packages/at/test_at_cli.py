
import os
import subprocess
import sys
project = os.path.dirname(os.path.abspath(__file__))
b = os.path.join(project, "bin/@")

def out(*args):
    return subprocess.check_output([sys.executable, b] + list(args), stderr=subprocess.STDOUT)

def test_at():
    assert out("1") == b"1\n"
    assert out(";;;") == b""

