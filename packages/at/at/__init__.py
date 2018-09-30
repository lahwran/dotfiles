#!/usr/bin/env python
# python 2 only, adjust path (or port, I'd love you) as needed
# run @ --help for (a little) more information
# MIT licensed.
"""\
primarily a python eval command. auto-formats the result of your expression:
(> indicates the line contains user input)

  > $ @ '1'
    1
  > $ @ '1 + 1'
    2
  > $ @ '"hello world"'
    hello world

has auto-import; looks through your string for module names.
if it finds them, it imports them. shouldn't cause any issues if you don't
mean to use the module:

  > $ @ 'time.time()'
    1397224233.76

if you pass -p, prints x for x in <your expression> on lines:

  > $ @ '[1, 2, 3, 4]'
    [1, 2, 3, 4]
  > $ @ -p '[1, 2, 3, 4]'
    1
    2
    3
    4

if you pass -l, appends ' for line in lines' to your expression:

  > $ @ -pl 'line[::-1]'
  > hello world
    dlrow olleh
  > wheee!
    !eeehw
  > this is fun!
    !nuf si siht

examples from my bash history (try them, they don't bite):

    @ '"|".join(lines)'
    @ -p 'range(10)'
    @ -pl 'line[::-1]
    @ '"%s %s" % (datetime.datetime.now(), line)' -plu
    @ 'math.sqrt(49012)'
    @ 'math.sqrt(150)'
    ... | @ 'line.decode("utf-8").encode("unicode_escape")' -pl | ...
    @ 'x % 5 for x in range(15)'
    @ 'dir()' -p
    @ 'random.SystemRandom().choice("abcdef0123456789") for x in range(30)' -j
    @ 'pprint.pprint(json.loads(inp()))'
    @ 'urllib2.urlopen("google.com").read()'

another great one:

    @ 'variables'
"""


from __future__ import print_function

import sys
import codecs
import ast
import token
import tokenize
import contextlib
import six

_debug = "-d" in sys.argv

class _Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
        self._unbuffered = True

    def write(self, data):
        if isinstance(data, six.text_type) and not getattr(self.stream, "buffer", None):
            data = data.encode("utf-8")
        self.stream.write(data)
        if self._unbuffered:
            self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def _debuffer():
    if _debug:
        print("_debuffer()")
    sys.stdout = _Unbuffered(sys.stdout)
    sys.stdout._unbuffered = sys.stdout.isatty()

    sys.stderr = _Unbuffered(sys.stderr)
    sys.stderr._unbuffered = sys.stderr.isatty()
    if _debug:
        print("done in _debuffer()")

def succeed():
    "Function that exits with a success return code (0)."
    sys.exit(0)

def fail():
    "Function that exits with a failure return code (1)."
    sys.exit(1)

class lines(object):
    def __init__(self):
        self.__doc__ = "Iterable of lines coming in from standard in."

    def __iter__(self):
        return self

    def __repr__(self):
        return "<lines - iterable of lines coming from standard in>"

    def __str__(self):
        return "iterable"

    def next(self):
        line = sys.stdin.readline().decode("utf-8")
        if not line:
            raise StopIteration
        if line.endswith("\n"):
            line = line[:-1]
        return line

def inp():
    "Returns entire standard in as one string."
    res = sys.stdin.read()
    if type(res) == bytes:
        return res.decode("utf-8")
    return res

def _hash(hasher, text):
    instance = hasher()
    instance.update(text)
    return instance

def md5(text):
    "md5(text) - compute hex md5 of input string."
    import hashlib
    return _hash(hashlib.md5, text).hexdigest()

def sha256(text):
    "sha256(text) - compute hex sha256 of input string."
    import hashlib
    return _hash(hashlib.sha256, text).hexdigest()


def pairs(iterable):
    "pairs(iterable) -> (s0, s1), (s1,s2), (s2, s3), etc"
    from itertools import tee, izip
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def write(contents, value):
    sys.stdout.write(contents)
    sys.stdout.flush()
    return value


_chunks_guard = object()
def chunks(generator, size, pad=_chunks_guard):
    """
    chunks(generator, size, pad=<no pad>) - Yield size chunks from generator.
    fills the last one with pad if provided.
    """
    import itertools
    q = itertools.izip_longest(*[iter(generator)]*size, fillvalue=pad)
    return ([a for a in b if a is not _chunks_guard] for b in q)


def delays(delta, iterable=None):
    "delays(secs, i=itertools.repeat(None)) - Wraps iterator with delays."
    if iterable is None:
        import itertools
        iterable = itertools.repeat(None)
    if not callable(delta):
        if getattr(delta, "total_seconds", None) is not None:
            delta = delta.total_seconds()
        deltafunc = lambda: delta
    else:
        deltafunc = delta
    for x in iterable:
        import time
        time.sleep(float(deltafunc()))
        yield x

def noexc(lamb, *a, **kw):
    default = kw.get("default", None)
    try:
        return lamb(*a)
    except Exception as e:
        res = default
        if type(default) in [str, unicode]:
            return default.format(e=e)


lines = lines()

class bytes(object):
    def __init__(self):
        self.__doc__ = "Standard in, byte by byte, as an iterator"
        self.iterator = self._go()
        assert six.next(self.iterator) is None

    def __iter__(self):
        return self.iterator

    def next(self):
        return self.iterator.next()

    def __repr__(self):
        return "<bytes - standard in, byte by byte, as an iterator>"

    def __str__(self):
        return "iterable"

    def _go(self):
        yield None
        if sys.stdout.isatty() and sys.stdout._unbuffered:
            bufsize = 1
        else:
            bufsize = 512

        while True:
            s = sys.stdin.read(bufsize)
            if not s:
                break
            for char in s:
                yield char
bytes = bytes()


def _split_statements(string):

    if string is None:
        return [], ""

    operations = [[]]
    i = iter(string.split("\n"))
    nextop = lambda: six.next(i)
    for type, tokenstring, start, end, line in tokenize.generate_tokens(nextop):
        if tokenstring.strip() == ";":
            operations.append([])
            continue
        operations[-1].append((type, tokenstring))
    strings = [tokenize.untokenize(o) for o in operations]
    return strings[:-1], strings[-1]


def readall(file_like, max=None):
    import select
    read = b""
    while select.select([file_like], [], [], 0)[0] != [] and (max is None or len(read) < max):
        read += file_like.read(select.PIPE_BUF)
    return read


def paste():
    import subprocess
    return subprocess.check_output(["pbpaste"])



def readfor(file_like, duration, use_select=True):
    import select
    import time
    read = b""
    start = time.time()
    end = start + duration
    if use_select:
        while select.select([file_like], [], [], max(0, end - time.time()))[0] != []:
            read += file_like.read(select.PIPE_BUF)
    else:
        while time.time() < end:
            read += file_like.read(select.PIPE_BUF)
    return read
read_for = readfor
read_until = readfor


def shell(name="detect"):
    if _debug:
        print("    => shell(name={!r})".format(name))
    if name == "detect":
        try:
            import bpython
            name = "bpython"
        except ImportError:
            pass
    if name == "detect":
        try:
            import IPython
            name = "ipython"
        except ImportError:
            pass
    if name == "detect":
        try:
            import ptpython
            name = "ptpython"
        except ImportError:
            print("You should totally install ptpython, it's super awesome.")
            print("Specify `-i builtin` to shut this suggestion up.")
    if name == "detect":
        name = "builtin"
    if _debug:
        print("    => after detect: shell(name={!r})".format(name))

    def passthrough(globs, string):
        _add_modules(globs, [string])
        return string

    if name == "ipython":
        if _debug:
            print("    => loading ipython")
        from IPython import embed
        from IPython.terminal.embed import InteractiveShellEmbed

        def e(globbelses):
            orig = InteractiveShellEmbed.run_cell.im_func
            def run_cell(self, string, *a, **kw):
                return orig(self, passthrough(globbelses, string), *a, **kw)
            InteractiveShellEmbed.run_cell = run_cell

            return embed(user_ns=globbelses)

        # monkeypatch ipython.terminal.embed.[...].run_cell(self, string, ...)
        # write with self.push(dict)
        return e
    elif name == "ptpython":
        if _debug:
            print("    => loading ptpython")
        from ptpython.repl import embed, PythonRepl
        def wrap_embed(globs):
            orig = PythonRepl._execute.im_func
            def _execute(self, cli, string):
                return orig(self, cli, passthrough(globs, string))
            PythonRepl._execute = _execute
            return embed(globs, vi_mode=True)
        # monkeypatch ptpython.repl.PythonRepl._execute(self, cli, string)
        # write to actual external globals dict
        return wrap_embed
    elif name == "bpython":
        if _debug:
            print("    => loading bpython")
        from bpython import embed
        from bpython import repl
        def wrap_embed(globs):
            orig = repl.Interpreter.runsource.im_func
            def runsource(self, source, *a, **kw):
                return orig(self, passthrough(globs, source), *a, **kw)
                
            repl.Interpreter.runsource = runsource
            return embed(globs)
        return wrap_embed
    else:
        if _debug:
            print("    => loading builtin")
        if name != "builtin":
            print("warning: don't have interpreter %s, using builtin" % name)
        import code

        try:
            import readline
        except ImportError:
            pass

        def interact(local):
            code.interact("Welcome to the @ built-in console.",
                    readfunc=(lambda prompt: passthrough(local, raw_input(prompt))),
                    local=local)

        return interact


def _parse_args():
    global _debug
    if _debug:
        print("in _parse_args()")
    import argparse
    class Thingy(argparse.RawDescriptionHelpFormatter,
            argparse.ArgumentDefaultsHelpFormatter):
        # argparse's api is weird here
        pass
    parser = argparse.ArgumentParser(epilog=__doc__,
            description="Convenient python eval!",
            formatter_class=Thingy)
    parser.add_argument("-a", "--all", action="store_true",
            help="wrap expression in all()")
    parser.add_argument("-n", "--any", action="store_true",
            help="wrap expression in any()")
    parser.add_argument("-l", "--lines", action="store_true",
            help="make expression iterable per line")
    parser.add_argument("-c", "--chars", action="store_true",
            help="make expression iterable per character")
    parser.add_argument("-b", "--bool", action="store_true",
            help="wrap expression in bool() - important if result will be a bool!")
    parser.add_argument("-u", "--unbuffered", action="store_true",
            help="shut off output buffering")
    parser.add_argument("-p", "--print-each", action="store_true",
            help="print each result from the iterable - good with -l pipelining")
    parser.add_argument("-j", "--print-joined", action="store_true",
            help="print each result from the iterable, no newlines - good for -c pipelining")
    parser.add_argument("-v", "--variables", nargs="*",
            help='use as -v x="hi" y="$there" to add variables to the expression')
    parser.add_argument("string", nargs="*",
            help="the expression, automatically joined by space if multiple specified")
    parser.add_argument("-d", "--debug", action="store_true",
            help='print debug info for type detection')
    parser.add_argument("-q", "--quiet", action="store_true",
            help='quiet, eg don\'t print on ctrl+c')
            
    parser.add_argument("-i", "--interactive", action="store", default=None,
            const="detect", nargs="?",
            help='launch interactive mode')
    args = parser.parse_args()
    _debug = args.debug
    if _debug:
        print("did initial parse, args:", args)

    if args.unbuffered:
        sys.stdout._unbuffered = True
        sys.stderr._unbuffered = True
        if _debug:
            print("=> mark unbuffered")
    if not args.string and not args.interactive:
        args.interactive = 'detect'
    if args.interactive:
        args.interactive = shell(args.interactive)
    if _debug:
        print("=> args.interactive: ", args.interactive)

    string = " ".join(args.string) if args.string else None
    statements, string = _split_statements(string)
    if _debug:
        print("=> statements: ", args.interactive)
        for statement in statements:
            print("   ", statement)
        print(" <<", string)
    if args.print_joined:
        args.print_each = True

    assert not (args.lines and args.chars), "only -c or -l please"
    actions = len([x for x in [
        args.all,
        args.any,
        args.bool,
        args.print_each
    ] if x])
    assert actions <= 1, (
            "only one of ---all, --any, --bool, or --print_each please")


    if args.lines:
        if not string.strip():
            string = "line"
        string = "(%s) for line in lines" % string
    if args.chars:
        if not string.strip():
            string = "char"
        string = "(%s) for char in characters" % string

    if args.bool:
        string = "bool(%s)" % string
    if _debug:
        print("=> processed final str:")
        print(" << {}".format(string))

    if not args.variables:
        args.variables = []
    for var in args.variables:
        name, equals, value = var.partition("=")
        assert equals, "please put an equals sign in variable defitions"
        if _debug:
            print("=> add var {!r} = {!r}".format(name, value))
        globals()[name] = value


    return (statements, string, args.interactive, args.print_each, args.debug,
            sys.stdout.write if args.print_joined else print, args.quiet)

_available_names = set()
_available = []


class _Importable(object):
    def __init__(self, name, kind):
        self.name = name
        self.kind = kind

    def __repr__(self):
        return "<importable %s: %s>" % (self.kind, self.name)

    def __str__(self):
        return "importable %s" % (self.kind)


_optional_modules = [
    "six",
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "base64",
    "BaseHTTPServer",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "bsddb",
    "bz2",
    "cProfile",
    "cStringIO",
    "calendar",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "ConfigParser",
    "contextlib",
    "Cookie",
    "cookielib",
    "copy",
    "crypt",
    "csv",
    "ctypes",
    "datetime",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "email.charset",
    "email.encoders",
    "email.errors",
    "email.generator",
    "email.header",
    "email.iterators",
    "email.message",
    "email.mime",
    "email.parser",
    "email.utils",
    "encodings",
    "encodings.idna",
    "encodings.utf_8_sig",
    "ensurepip",
    "errno",
    "exceptions",
    "fcntl",
    "fcntl",
    "filecmp",
    "fileinput",
    "findertools",
    "fnmatch",
    "formatter",
    "fpectl",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "httplib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "logging.config",
    "logging.handlers",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "netrc",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "parser",
    "pdb",
    "pickle",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "random",
    "re",
    "readline",
    "resource",
    "robotparser",
    "runpy",
    "sched",
    "select",
    "shlex",
    "shutil",
    "signal",
    "SimpleHTTPServer",
    "SimpleXMLRPCServer",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "SocketServer",
    "sqlite3",
    "stat",
    "string",
    "StringIO",
    "stringprep",
    "struct",
    "subprocess",
    "symbol",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "textwrap",
    "thread",
    "threading",
    "time",
    "timeit",
    "token",
    "tokenize",
    "trace",
    "traceback",
    "tty",
    "types",
    "unicodedata",
    "urllib",
    "urllib2",
    "urlparse",
    "uu",
    "uuid",
    "warnings",
    "wave",
    "weakref",
    "wsgiref",
    "zipfile",
    "zlib",

    "cffi",
    "chardet",
    "colorama",
    "cryptography",
    "curtsies",
    "dateutil",
    "decorator",
    "docopt",
    "docutils",
    "docx",
    "enum",
    "exifread",
    "flask",
    "humanize",
    "husl",
    "idna",
    "jinja2",
    "keras",
    "klein",
    "lxml",
    "markdown",
    "markupsafe",
    "matplotlib",
    "mutagen",
    "numpy",
    "pandas"
    "pathtools",
    "png",
    "progressbar",
    "prompt_toolkit",
    "pudb",
    "py",
    "pygments",
    "pytest",
    "requests",
    "scikits",
    "scipy",
    "setuptools",
    "skimage",
    "theano",
    "treq",
    "twisted",
    "urwid",
    "watchdog",
    "yaml",

]

@contextlib.contextmanager
def _mute_stderr():
    "Context manager that mutes file descriptor 2"
    import os
    if not _debug:
        #print("muting fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "muting fd 2 (this was written to fd 2)\n")
        p = os.dup(fdnum)
        q = os.open("/dev/null", os.O_WRONLY)
        os.dup2(q, fdnum)
        sys.stderr = os.fdopen(p, "w")
        #print("just muted fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "just muted fd 2 (this was written to fd 2)\n")

    yield

    if not _debug:
        #print("about to unmute fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "about to unmute fd 2 (this was written to fd 2)\n")
        os.dup2(p, fdnum)
        os.close(q)
        sys.stderr = os.fdopen(fdnum, "w")
        #print("unmuting fd 2 (this was written to fd sys.stderr)", file=sys.stderr)
        #os.write(2, "unmuting fd 2 (this was written to fd 2)\n")

@contextlib.contextmanager
def _mute_all():
    "Context manager that mutes file descriptor 2"
    import os
    fdnum2 = sys.stderr.fileno()
    fdnum1 = sys.stdout.fileno()
    if not _debug:
        #print("muting fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "muting fd 2 (this was written to fd 2)\n")
        p = os.dup(fdnum2)
        q = os.open("/dev/null", os.O_WRONLY)
        os.dup2(q, fdnum2)
        sys.stderr = os.fdopen(p, "w")
        if fdnum2 != fdnum1:
            w = os.dup(fdnum1)
            v = os.open("/dev/null", os.O_WRONLY)
            os.dup2(v, fdnum1)
        else:
            sys.stdout = sys.stderr
        #print("just muted fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "just muted fd 2 (this was written to fd 2)\n")

    yield

    if not _debug:
        #print("about to unmute fd 2 (this was written to sys.stderr)", file=sys.stderr)
        #os.write(2, "about to unmute fd 2 (this was written to fd 2)\n")
        os.dup2(p, fdnum2)
        os.close(q)
        sys.stderr = os.fdopen(fdnum2, "w")
        if fdnum1 != fdnum2:
            os.dup2(w, fdnum1)
            os.close(v)
            sys.stdout = os.fdopen(fdnum1, "w")
        else:
            sys.stdout = sys.stderr
        #print("unmuting fd 2 (this was written to fd sys.stderr)", file=sys.stderr)
        #os.write(2, "unmuting fd 2 (this was written to fd 2)\n")

def _add_modules(globbles, strings):
    if _debug:
        print("=> in _add_modules()")
    def _import(_mod):
        try:
            globbles[_mod] = __import__(_mod)
        except ImportError as e:
            print(e)
            return None
        _reset_vars()
        return globbles[_mod]
    def _reset_vars():
        if "variables" in globbles:
            globbles["variables"]._cache = None

    def _wanted(_mod, kind=None):
        if kind is not None and _mod not in _available_names:
            _available_names.add(_mod)
            _available.append(_Importable(_mod, kind))
        # to find all mentions of a module name
        # (?:.*(?<!\w)(MODULE_NAME)(?!\w))+(?:.(?!(?<!\w)(MODULE_NAME)(?!\w)))*
        # not sure if I need the hack at the end to make sure there are no
        # repetitions of the module name...

        mod_re = "(?<!\w)(MODULE_NAME)(?!\w)".replace("MODULE_NAME", _mod)
        import re
        return _mod not in globbles and any(re.search(mod_re, _s) for _s in strings)

    if _debug:
        print("=> checking optional_modules")
    for _mod in _optional_modules:
        if _wanted(_mod, "module"):
            if _debug:
                print("importing module found in code:", _mod)
            _import(_mod)


    if _wanted("terminal", "pre-initialized blessings instance") or _wanted("blessings", "blessings module") or _wanted("term", "same as `terminal`"):
        if _debug:
            print("adding terminal/blessings")
        blessings = _import("blessings")
        globbles["blessings"] = blessings
        if blessings and "terminal" not in globbles:
            terminal = blessings.Terminal(force_styling=True)
            globbles["terminal"] = terminal
            globbles["term"] = terminal

    # force non-short-circuit evaluation
    #a = _wanted("session", "pre-initialized tensorflow session")
    #a = _wanted("sess", "pre-initialized tensorflow session") or a
    #a = _wanted("s", "pre-initialized tensorflow session") or a
    #a = _wanted("tf", "tensorflow module short-name") or a
    #a = _wanted("tensorflow", "tensorflow") or a
    #if a:
    #    with _mute_all():
    #        tf = _import("tensorflow")
    #        if tf and "session" not in globbles:
    #            session = tf.InteractiveSession()
    #            globbles["session"] = session
    #            globbles["sess"] = session
    #            globbles["s"] = session
    #            globbles["tensorflow"] = tf
    #            globbles["tf"] = tf
    #            _reset_vars()

    if _wanted("np", "numpy module short-name"):
        if _debug:
            print("adding numpy as np")
        numpy = _import("numpy")
        if numpy:
            globbles["np"] = numpy

    for _itertool_func in _itertools_values:
        if _wanted(_itertool_func):
            if _debug:
                print("adding itertools func", _itertool_func)
            _itertools = __import__("itertools")
            globbles[_itertool_func] = getattr(_itertools, _itertool_func)
            _reset_vars()
        del _itertool_func

_available_itertools = []
_itertools_values = [
    "accumulate",
    "count",
    "cycle",
    "repeat",
    "chain",
    "compress",
    "dropwhile",
    "groupby",
    "ifilter",
    "ifilterfalse",
    "islice",
    "imap",
    "starmap",
    "tee",
    "takewhile",
    "izip",
    "izip_longest",
    "product",
    "permutations",
    "combinations",
    "combinations_with_replacement",
]
for _itertool_func in _itertools_values:
    _available_itertools.append(_Importable(_itertool_func, "itertools function"))
del _itertool_func

_blacklist = [
    "_parse_args",
    "_chunks_guard",
    "_available_names",
    "_mute_stderr",
    "_mute_all",
    "_debug",
    "interactive",
    "_format_var",
    "run_globals",
    "_add_environment_vars",
    "_available",
    "_LazyString",
    "_avail",
    "__doc__",
    "__file__",
    "_available_itertools",
    "_Importable",
    "_itertools_values",
    "_wanted",
    "_mod",
    "_optional_modules",
    "_blacklist",
    "_run",
    "_main",
    "_debuffer",
    "_string",
    "_statements",
    "_shouldprint",
    "_hash",
    "__package__",
    "__name__",
    "_add_modules",
    "_Unbuffered",
    "__builtins__",
    "_statement",
    "_variables",
    "_result",
    "_split_statements",
    "_hasdoc",
    "_old_globals",
]

class _LazyString(object):
    """Class for strings created by a function call.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting.

    This is most of the implementation of the `speaklater` package on pypi,
    copy and pasted. this class is BSD licensed, the rest of this file is MIT.
    """
    __slots__ = ('_func', '_args', "_kwargs", "_cache")

    def __init__(self, func, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._cache = None

    @property
    def value(self):
        if self._cache is not None:
            return self._cache
        self._cache = self._func(*self._args, **self._kwargs)
        return self._cache

    def __contains__(self, key):
        return key in self.value

    def __nonzero__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(unicode)

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __add__(self, other):
        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __mod__(self, other):
        return self.value % other

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __getattr__(self, name):
        if name == '__members__':
            return self.__dir__()
        return getattr(self.value, name)

    def __getstate__(self):
        return self._func, self._args, self._kwargs

    def __setstate__(self, tup):
        self._func, self._args, self._kwargs = tup

    def __getitem__(self, key):
        return self.value[key]

    def __copy__(self):
        return self

    def __repr__(self):
        print(self)
        return ""
        #try:
        #    return "LazyString(%r)" % self._func
        #except Exception:
        #    return '<%s broken>' % self.__class__.__name__

def _hasdoc(value):
    doc = getattr(value, "__doc__", None)
    return doc != getattr(type(value), "__doc__", None) and doc

def _format_var(name, value, f=None):
    def truncate_to_line(v, length=100):
        s = v.split("\n")
        if len(s) > 1 or len(s[0]) >= length:
            v = s[0][:length//2 - 5] + "   ...   " + s[0][-(length//2 - 6):]
        return v

    if f is None:
        f = "- {name}: {value}"
    
    if type(value) == _LazyString:
        simpledesc = "<Lazy String>"
    elif type(value) == type(_format_var):
        simpledesc = "function"
    elif type(value) == type(print):
        simpledesc = "builtin"
    elif type(value) == type:
        simpledesc = "class"
    elif type(value) == type(token):
        simpledesc = "module"
    elif type(value) == type(str.join):
        simpledesc = "method"
    elif type(value) == type("".join) or type(value) == type(object().__str__) or type(value) == type(bytes.__str__):
        simpledesc = "bound method"
    elif isinstance(type(value), six.string_types):
        simpledesc = repr(value)
    else:
        simpledesc = str(value)

    if _hasdoc(value):
        value = ("%s - %s" % (simpledesc, value.__doc__.split("\n")[0])).strip()
        value = truncate_to_line(value)
    else:
        value = truncate_to_line(simpledesc)

    return f.format(name=name, value=value)


def show(x, all=False):
    def f(d, blist):
        return "\n".join(
            _format_var(name, value)
            for name, value in sorted(d.items(), key=lambda x: x[0]))
    print(_format_var(None, x, f="{value}"))

    m = dict((q, getattr(x, q)) for q in dir(x) if all or not q.startswith("__"))
    if _hasdoc(x):
        print()
        print(x.__doc__)
        print()

    if m:
        print("Attributes")
        print("==============\n")
        print(f(m, {}))


def _variables(g, oldglobals, quick=False):
    import os
    def f(d, blist):
        return "\n".join(
            _format_var(name, value)
            for name, value in sorted(d.items(), key=lambda x: x[0])
            if name not in blist)
    blist = set(_blacklist)
    shell_vars = f(os.environ, blist)
    blist |= set(os.environ.keys())

    modules = None
    iterfuncs = None
    if not quick:
        modules = f(dict((x.name, g.get(x.name, x)) for x in _available), blist)
    else:
        modules = f(dict((x.name, g[x.name]) for x in _available if x.name in g), blist)
    blist |= set([x.name for x in _available])

    if not quick:
        iterfuncs = f(dict((x.name, g.get(x.name, x)) for x in _available_itertools), blist)
    else:
        iterfuncs = f(dict((x.name, g[x.name]) for x in _available_itertools if x.name in g), blist)
    blist |= set([x.name for x in _available_itertools])

    remaining = f(oldglobals, blist)
    blist |= set(oldglobals.keys())

    uservars = f(g, blist)

    tail = ""

    result = ""
    if shell_vars:
        result += (
            "Variables from shell environment\n"
            "--------------------------------\n"
            "\n"
            "{shell_vars}\n"
            "\n"
        ).format(shell_vars=shell_vars)
    if modules:
        result += (
            "Imported and auto-importing modules\n"
            "-----------------------------------\n"
            "\n"
            "'importable' modules will automatically import on use.\n"
            "\n"
            "{modules}\n"
            "\n"
        ).format(modules=modules)
    if iterfuncs:
        result += (
            "extra: these functions will be auto-imported from itertools:\n"
            "\n"
            "{iterfuncs}\n"
            "\n"
        ).format(iterfuncs=iterfuncs)
    if remaining:
        result += (
            "Utilities and globals specific to @\n"
            "-----------------------------------\n"
            "\n"
            "{remaining}\n"
        ).format(remaining=remaining)
    if uservars:
        result += ("\n"
            "Your variables\n"
            "==============\n"
            "\n"
            "{}\n"
        ).format(uservars)
    return result


def _add_environment_vars(glob, outer_dir):
    import os
    original_globals = dict(glob)

    overlap = set(original_globals) & set(os.environ)
    overlap2 = set(outer_dir + dir(__builtins__)) & set(os.environ)
    if overlap and _debug:
        print("WARNING: variable overlap: %r" % overlap)
    elif overlap2 and _debug:
        print("WARNING: builtin overlap: %r" % overlap2)


    glob.update(os.environ)
    glob.update(original_globals)


def run(statements, expression, run_globals, _shouldprint, _quiet):
    try:
        for statement in statements:
            six.exec_(statement, globals=run_globals)
        if not expression.strip():
            _result = None
        else:
            _result = eval("(%s)" % expression, run_globals)

        if "tensorflow" in sys.modules:
            import tensorflow
            if isinstance(_result, tensorflow.python.framework.ops.Tensor):
                if "session" not in run_globals:
                    run_globals["session"] = tensorflow.InteractiveSession()
                _result = run_globals["session"].run(_result)
    except KeyboardInterrupt:
        if not _quiet:
            sys.stderr.write("@ killed (ctrl+d to close cleanly)")
        return fail
    except BaseException as e:
        import traceback
        x = traceback.format_exc().split("\n")
        y = "\n".join(x[4:])
        sys.stderr.write(y)
        sys.stderr.flush()
        return fail


    if _result is None:
        _result = True

    if not (isinstance(_result, six.string_types) or isinstance(_result, _LazyString)):
        try:
            iterator = iter(_result)
        except TypeError as e:
            if getattr(_result, "__iter__", None):
                print(repr(_result.__iter__))
                raise
        else:
            if _shouldprint:
                for x in iterator:
                    if _debug:
                        print("printed iterator:", x)
                    else:
                        print(x)
            else:
                result2 = list(iterator)
                try:
                    # lol hax
                    is_repeatable_iterable = (
                        "numpy" in str(type(_result))
                        or (
                            iterator is not _result
                            and result2 == list(iter(_result))
                        )
                    )
                except ValueError:
                    # assume yes, because annoying
                    is_repeatable_iterable = True
                if is_repeatable_iterable: # check for repeatability
                    if _debug:
                        print("repeatable iterable:", _result, result2)
                    else:
                        print(_result)
                elif any(x != None for x in result2):
                    if _debug:
                        print("listed iterable with at least one non-none:", result2)
                    else:
                        print(result2)
                elif _debug:
                    print("nothing to print")
            return succeed

    if not isinstance(_result, bool) or _shouldprint:
        if _debug:
            print("hasdoc:", _hasdoc(_result), "repr and str equal:", repr(_result) == str(_result), "uses object str:", type(_result).__str__ == object.__str__)
        if (_hasdoc(_result) and repr(_result) == str(_result)) or type(_result).__str__ == object.__str__:
            if _debug:
                print("printed docstring:", _result.__doc__)
            else:
                #print(_result.__doc__)
                show(_result)
        else:
            if _debug:
                print("primary print:", _result)
            else:
                print(_result)

    if isinstance(_result, bool):
        if _debug:
            print("bool result, returning exit code:", 0 if _result else 1, _result)

        if _result:
            return succeed
        else:
            return fail
    else:
        if _debug:
            print("non-bool result, returning exit code 0 (true)")
        return succeed


def _run(_statements, _string, interactive, _shouldprint, _debug, print, _quiet):
    import os
    if _debug:
        print("in _run")
    sys.path.append(os.path.abspath("."))
    old_globals = dict(globals())

    old_globals["all_variables"] = _LazyString(lambda: _variables(run_globals, old_globals))
    old_globals["variables"] = _LazyString(lambda: _variables(run_globals, old_globals, quick=True))


    _add_modules(old_globals, _statements + [_string])
    run_globals = dict(old_globals)
    _add_environment_vars(run_globals, list(old_globals.keys()))

    if _string.strip() or _statements:
        try:
            result = run(_statements, _string, run_globals, _shouldprint, _quiet)
        except SystemExit:
            if not interactive:
                raise
        else:
            if not interactive:
                result()

    if interactive:
        interactive(run_globals)

def _main():
    global print
    _debuffer()
    _statements, _string, interactive, _shouldprint, _debug, print, _quiet = _parse_args()
    if _debug:
        print("_parse_args done. _shouldprint={}, _quiet={}".format(_shouldprint, _quiet))
    _run(_statements, _string, interactive, _shouldprint, _debug, print, _quiet)

if _debug:
    print("before _main(); __name__ =", __name__)
if __name__ == "__main__":
    _main()

