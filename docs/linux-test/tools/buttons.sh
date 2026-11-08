#!/bin/bash
L="$1"; N=$2; D=:9$N; export DISPLAY=$D GTK_A11Y=none HOME=/tmp/btn-$N; rm -rf $HOME; mkdir -p $HOME/.config/gtk-4.0
printf "[Settings]\ngtk-decoration-layout=%s\n" "$L" > $HOME/.config/gtk-4.0/settings.ini
Xvfb $D -screen 0 1440x900x24 >/dev/null 2>&1 & XP=$!; sleep 1
export DBUS_SESSION_BUS_ADDRESS=$(dbus-daemon --session --fork --print-address=1 | head -1)
mutter --x11 --replace >/dev/null 2>&1 & sleep 2
${APPBIN:-/home/claude/pub/chuvadi-reader} >/dev/null 2>&1 & AP=$!; sleep 8
import -window root /tmp/b.png; P=/home/claude/evidence/buttons; mkdir -p $P
convert /tmp/b.png -crop 260x40+0+0 +repage $P/$N-left.png; convert /tmp/b.png -crop 260x40+1180+0 +repage $P/$N-right.png
convert $P/$N-left.png $P/$N-right.png +append -bordercolor '#f0f' -border 2 $P/$N-ends.png
cp /tmp/b.png $P/$N-full.png
kill $AP; sleep 1; pkill -f "mutter --x11"; kill $XP
