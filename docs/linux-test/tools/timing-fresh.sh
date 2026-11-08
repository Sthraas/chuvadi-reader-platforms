#!/bin/bash
source /home/claude/ttools/session.sh
out=/home/claude/evidence/timing
for i in $(seq 1 $2); do
  export HOME=$(mktemp -d /tmp/fresh.XXXX); sync; echo 3 > /proc/sys/vm/drop_caches; sleep 1
  r=$(CHUVADI_TIMING=1 /home/claude/ttools/framewatch 30000 1500 -- $3 2>/tmp/tm.err)
  echo "$1 $i $r shown=$(grep -m1 ' shown' /tmp/tm.err|awk '{print $2}') pageloaded=$(grep -m1 'page loaded' /tmp/tm.err|awk '{print $2}') firstrender=$(grep -m1 'first render' /tmp/tm.err|awk '{print $2}')" >> $out/$1.txt
done
