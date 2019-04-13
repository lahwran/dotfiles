#!/usr/bin/env python
# == DOCKER TOOL ==
import sys
import subprocess
import argparse
import sys
import os

#parser.add_argument('--version', action='version', version='1.0.0')


class argument(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
REMAINDER=argparse.REMAINDER
class apwrap(object):
    REMAINDER=argparse.REMAINDER
    def __init__(self, *args, **kwargs):
        self.parser = argparse.ArgumentParser(*args, **kwargs)
        self.parser.set_defaults(func=self.fail_with_help)
        self.subparsers_ = None
        self.added_help_cmd = False
        self.added_config_arg = False
        self.added_pyramid = False
        self.added_db = False
        self.post_setup = []

    def fail_with_help(self, *a, **kw):
        self.parser.print_help(sys.stderr)
        raise SystemExit

    def add_argument(self, *a, **kw):
        return self.parser.add_argument(*a, **kw)

    def subparsers(self, *a, **kw):
        if self.subparsers_ is None:
            kw["metavar"] = "command"
            kw["help"] = "command to run. one of:"
            self.subparsers_ = self.parser.add_subparsers(*a, **kw)
        return self.subparsers_

    def command(self, *arguments, aliases=(), help=None):
        help_ = help
        if not self.added_help_cmd:
            self.added_help_cmd = True

            @self.command(argument("subcommand", default=None, nargs="?"), help="print this help message")
            def help(*a, **kw):
                self.fail_with_help()

        def inner(func):
            name = func.__name__.replace("_", "-")
            sp = self.subparsers().add_parser(name, aliases=aliases, help=help_)
            for arg in arguments:
                sp.add_argument(*arg.args, **arg.kwargs)
            sp.set_defaults(func=func)
            return func
        if len(arguments) == 1 and type(arguments[0]) != argument:
            func = arguments[0]
            arguments = []
            return inner(func)
        return inner

    def parse_args(self, *a, **kw):
        args = self.parser.parse_args(*a, **kw)
        for func in self.post_setup:
            func(args)
        return args

    def add_config_arg(self):
        if self.added_config_arg:
            return
        self.added_config_arg = True

        proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_configs = [x for x in os.listdir(proj_dir) if x.endswith(".ini") and "pyramid" in x]
        if "pyramid_prod.ini" in default_configs:
            required = False
            default = "pyramid_prod.ini"
        elif "pyramid_dev.ini" in default_configs:
            required = False
            default = "pyramid_dev.ini"
        else:
            required = True
            default = None
        self.add_argument("-c", "--config", required=required, default=default, help="path to server config ini")

import os
import json

apw = apwrap()
dtfile = os.path.expanduser("~/.dockertool.json")
try: 
    with open(dtfile, "r") as reader:
        state = json.loads(reader.read())
except OSError:
    state = {}

def s(*reset, **up):
    global state
    state = dict(((state,) + reset)[-1], **up)
    with open(dtfile, "w") as writer:
        writer.write(json.dumps(state, indent=1, sort_keys=True))

last_image = state.get("last_image", "ubuntu")


@apw.command(
    argument("name"),
    argument("image", help="image to use. defaults to last image: {}".format(last_image), default=last_image, nargs="?"),
    argument("args", nargs=apwrap.REMAINDER),
    help="alias for `docker create --name <name> <image> <args>`; create. doesn't start container.",
    aliases=["c"])
def create(args):
    s(image=args.image)
    return subprocess.call(["docker", "create", "-ti", args.image] + args.args)


@apw.command(
    argument("image", help="image to use. defaults to last image: {}".format(last_image), default=last_image, nargs="?"),
    argument("args", nargs=apwrap.REMAINDER),
    help="alias for `docker run -ti <image> <args>`; create+start. leaves container around.",
    aliases=["cr"])
def crun(args):
    s(image=args.image)
    return subprocess.call(["docker", "run", "-ti", args.image] + args.args)


@apw.command(
    argument("image", help="image to use. defaults to last image: {}".format(last_image), default=last_image, nargs="?"),
    argument("args", nargs=apwrap.REMAINDER),
    help="alias for `docker run --rm -ti <image> <args>",
    aliases=["r"])
def run(args):
    s(image=args.image)
    return subprocess.call(["docker", "run", "--rm", "-ti", args.image] + args.args)


@apw.command(
    argument("dockerfile", default="Dockerfile"),
    argument("args", nargs=apwrap.REMAINDER),
    help="build and run. deletes afterwards.",
    aliases=["br", "build"])
def build_run(args):
    try:
        subprocess.check_call(["docker", "build", "-t", "dt_run", ".", "-f", args.dockerfile])
    except subprocess.CalledProcessError as e:
        return e.returncode
    s(image="dt_run")
    return subprocess.call(["docker", "run", "--rm", "-ti", "dt_run"] + args.args)

@apw.command(
    argument("dockerfile", default="Dockerfile"),
    argument("args", nargs=apwrap.REMAINDER),
    help="build, create, run. prints & sets last container.",
    aliases=["bcr"])
def build_crun(args):
    try:
        subprocess.check_call(["docker", "build", "-t", "dt_run", ".", "-f", args.dockerfile])
    except subprocess.CalledProcessError as e:
        return e.returncode
    s(image="dt_run")
    return subprocess.call(["docker", "run", "--rm", "-ti", "dt_run"] + args.args)
#        subprocess.check_call(["docker", "create", "--name", "dt- "-t", "dt_run", ".", "-f", args.dockerfile])


def main():
    args = apw.parse_args()
    sys.exit(args.func(args))

if __name__ == "__main__":
    main()
#cmd=sys.argv[1]
#if [ "$cmd" = "" ]; then
#    echo 'pass a command. one of:'
#    echo ' - dt (r|run) <image> <args>:   '
#    echo ' - dt (rr|rrun) <image> <args>: '
#fi
#

