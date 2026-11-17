cd /home/claude/wt-verify/tests/web-e2e; O=${OUT:-/tmp/out}; P=/tmp/corpus/text-13.pdf
fresh(){ kill $(cat /tmp/portal-$1.pid) 2>/dev/null; sleep 2; rm -rf /dev/shm/chvd-$1; PUB=$PUB /tmp/start-portal.sh $1 Gateway >/dev/null; }
cnt(){ n=$1; shift; r=$(timeout 500 "$@" 2>&1 | grep -E "^(PASS|FAIL)"); echo "$n: $(echo "$r" | grep -c ^PASS) pass, $(echo "$r" | grep -c ^FAIL) fail"; echo "$r" | grep ^FAIL | cut -c1-220; }
echo "== WT-27 flows.py firefox, first visit on fresh portals"
for i in 1 2 3 4 5 6; do fresh 6095; cnt "fresh portal $i" python3 flows.py http://127.0.0.1:6095 $P $O /tmp/portal-6095.log --browser firefox; done
echo "== WT-27 early_drop.py, fresh portal each"
for br in chrome firefox webkit chromium; do fresh 6095; cnt "early_drop $br" python3 early_drop.py http://127.0.0.1:6095 $P --browser $br; done
echo "== worker_crash.py, fresh portal each"
for br in chrome firefox webkit; do fresh 6095; cnt "worker_crash $br" python3 worker_crash.py http://127.0.0.1:6095 $P /dev/shm/chvd-6095 /tmp/portal-6095.log --browser $br; grep -c "ended with code" /tmp/portal-6095.log; done
kill $(cat /tmp/portal-6095.pid)
echo DONE-A
