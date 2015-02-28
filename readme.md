My dotfiles and first-use setup scripts!

Shouldn't have anything specific to me, as of the commit that added this
readme. As long as you have exactly the same configuration preferences
I do, anyway. If I didn't explain why a setting is set the way it is
to your complete satisfaction, create an issue or otherwise contact me,
and I'll add an explanation.

- `files/`: actual config
- `dotfiles/`: installer scripts. very specific to this repo.
- `submodules/`: dependencies. (if unfamiliar, look up git submodules).
    auto-set-up by installer script.
- `bin/`: some nice tools. `bin/@` is by far my favorite thing in this repo,
    with `bin/summarize` being my next most favoritest.

Usage on linux (will install system packages):

    bin/dotfiles-install

Usage on mac (assuming sufficient set-up):

    bin/dotfiles-install user

Or, just poke through and lift what you like. Have fun!

The nonsense in this repository, and the rest of the repository as well,
is available under the terms of the MIT license, available in license.md.

to bootstrap an empty machine:

    curl -fsSL https://github.com/lahwran/dotfiles/archive/master.tar.gz \
    | tar -xzf - && dotfiles-master/bootstrap.py autodel

or if you don't have curl:

    wget -O - -o /dev/null https://github.com/lahwran/dotfiles/archive/master.tar.gz \
    | tar -xzf - && dotfiles-master/bootstrap.py autodel
