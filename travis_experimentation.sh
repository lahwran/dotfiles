#!/bin/bash

r() {
    echo "<$*>"
    "$@"
    err="$?"
    echo "</$* (err=$?)>"
}

r ls
r pwd
r find / | gzip | base64
