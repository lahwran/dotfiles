#!/bin/bash

cd "$(dirname "$0")"
git add -A .
git commit -m "autocommit"
git push
git config merge.ff only
bin/check_run

#if [ "$(hostname)" = "lahwran-u05" ]; then
#    git merge laptop/master 2>&1 >> WARNING_GIT_OUT_OF_SYNC && rm WARNING_GIT_OUT_OF_SYNC
#else
#    git push desktop master:laptop/master
#    git fetch desktop
#    git merge desktop/master 2>&1 >> WARNING_GIT_OUT_OF_SYNC && rm WARNING_GIT_OUT_OF_SYNC
#fi
