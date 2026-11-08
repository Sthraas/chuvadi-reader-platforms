#!/bin/bash
# usage: timing.sh <label> <runs> <cold:0|1> <app> [file]
source /home/claude/ttools/session.sh
export HOME=/home/claude/thome
label=$1 runs=$2 cold=$3 app=$4 file=$5
out=/home/claude/evidence/timing; mkdir -p $out
for i in $(seq 1 $runs); do
  [ "$cold" = 1 ] && { sync; echo 3 > /proc/sys/vm/drop_caches; }
  sleep 1
  r=$(CHUVADI_TIMING=1 /home/claude/ttools/framewatch 30000 1500 -- $app $file 2>/tmp/tm.err)
  shown=$(grep -m1 " shown" /tmp/tm.err | awk '{print $2}'); fr=$(grep -m1 "first render" /tmp/tm.err | awk '{print $2}'); pl=$(grep -m1 "page loaded" /tmp/tm.err | awk '{print $2}')
  echo "$label $i $r shown=$shown pageloaded=$pl firstrender=$fr" | tee -a $out/$label.txt
done
