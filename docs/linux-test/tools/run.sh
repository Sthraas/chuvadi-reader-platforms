#!/bin/bash
# inside container, as tester. $1 = label
cd ~; export DISPLAY=:9 XDG_RUNTIME_DIR=/tmp/rt-$USER; mkdir -p $XDG_RUNTIME_DIR; chmod 700 $XDG_RUNTIME_DIR
Xvfb :9 -screen 0 1440x900x24 >/dev/null 2>&1 & sleep 1
eval $(dbus-launch --sh-syntax)
[ "$RO" = 1 ] && chmod -R a-w ~
[ -n "$PREP" ] && eval "$PREP"
CHUVADI_TIMING=1 timeout 40 chuvadi-reader ${FILE:-/opt/t/five-pages.pdf} > /tmp/app.log 2>&1 &
sleep ${WAIT:-15}
import -window root /out/$1.png 2>/dev/null
ps -C chuvadi-reader >/dev/null && echo "$1: ALIVE" || echo "$1: NOT RUNNING"
pkill -TERM -x chuvadi-reader; for i in 1 2 3 4 5 6; do ps -C chuvadi-reader >/dev/null || break; sleep 1; done; ps -C chuvadi-reader >/dev/null && echo "$1: STILL RUNNING 6 s after SIGTERM"
echo "$1: rss=$(ps -o rss= -C chuvadi-reader | head -1)KB  locale=$LANG"
grep -E "timing|rror|xception|arning" /tmp/app.log | grep -v a11y | head -6 | sed "s/^/$1:   /"
find ~ -maxdepth 3 \( -path '*/.config/*' -o -path '*/Documents*' \) 2>/dev/null | head -5 | sed "s/^/$1:   file /"
