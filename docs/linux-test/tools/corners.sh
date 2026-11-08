#!/bin/bash
# $1 label  $2 wm: mutter|none   $3 state: restored|maximised|fullscreen
D=:8$RANDOM; D=${D:0:4}; export DISPLAY=$D GTK_A11Y=none HOME=/home/claude/thome
Xvfb $D -screen 0 1440x900x24 >/dev/null 2>&1 & XP=$!; sleep 1
export DBUS_SESSION_BUS_ADDRESS=$(dbus-daemon --session --fork --print-address=1 | head -1)
[ "$2" = mutter ] && { mutter --x11 --replace >/dev/null 2>&1 & sleep 2; }
/home/claude/pub/chuvadi-reader >/dev/null 2>&1 & AP=$!; sleep 7
W=$(xdotool search --name Chuvadi | tail -1)
case $3 in maximised) xdotool windowsize $W 100% 100% 2>/dev/null; xdotool key --window $W super+Up; sleep 2;;
 fullscreen) xdotool windowactivate $W 2>/dev/null; xdotool key F11; sleep 2;;
 restored) wmctrl -i -r $W -b remove,maximized_vert,maximized_horz; sleep 1; xdotool windowsize $W 1100 700; xdotool windowmove $W 150 100; sleep 2;; esac
eval $(xdotool getwindowgeometry --shell $W); echo "$1: geom ${WIDTH}x${HEIGHT}+${X}+${Y}"
import -window root /tmp/c-$1.png
P=/home/claude/evidence/corners; mkdir -p $P
# window may be client-side decorated: find the app's frame by scanning for the cream colour from the top-left of the reported geometry
convert /tmp/c-$1.png -crop 24x24+$X+$Y +repage -scale 800% $P/$1-tl.png
convert /tmp/c-$1.png -crop 24x24+$((X+WIDTH-24))+$((Y+HEIGHT-24)) +repage -scale 800% $P/$1-br.png
cp /tmp/c-$1.png $P/$1-full.png
kill $AP; sleep 1; pkill -P $$ mutter; kill $XP
