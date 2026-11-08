#!/bin/sh
# Test fixture (never shipped): a document source that never delivers data,
# like a hung SMB/NFS/sshfs mount or an unplugged USB drive. Reproduces B-24 / B-08b.
#   stalled-source.sh make  [dir]   -> creates dir/slow.pdf and dir/slow.xlsx (named pipes)
#   stalled-source.sh clean [dir]   -> unblocks any reader and removes them (never hangs)
set -e
DIR=${2:-/tmp/chvd-stall}
case "$1" in
  make)  mkdir -p "$DIR"; for f in slow.pdf slow.xlsx; do rm -f "$DIR/$f"; mkfifo "$DIR/$f"; done
         echo "Open $DIR/slow.pdf (or slow.xlsx) in Chuvadi; it will wait forever for data." ;;
  clean) for f in slow.pdf slow.xlsx; do
           # open for writing without blocking (fails harmlessly if nobody is reading), then close -> reader sees EOF
           python3 -c "import os,sys
try: os.close(os.open(sys.argv[1], os.O_WRONLY|os.O_NONBLOCK))
except OSError: pass" "$DIR/$f" 2>/dev/null || true
           rm -f "$DIR/$f"; done ;;
  *) echo "usage: $0 make|clean [dir]"; exit 2 ;;
esac
