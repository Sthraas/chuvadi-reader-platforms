#!/bin/bash
# WT-11: a published portal holds only what runs on the Linux server. Usage: check-package.sh <publish folder>
set -u
dir="${1:?publish folder}"
fail=0
for f in web.config appsettings.Development.json; do
    if [ -e "$dir/$f" ]; then echo "FAIL: $f is in the package"; fail=1; fi
done
extra=$(find "$dir" -maxdepth 1 \( -name '*.pdb' -o -name '*.xml' \) -printf '%f\n')
if [ -n "$extra" ]; then echo "FAIL: symbols or API docs in the package:"; echo "$extra"; fail=1; fi
for f in ChuvadiReader.Web.dll appsettings.json ChuvadiReader.Web.staticwebassets.endpoints.json wwwroot; do
    if [ ! -e "$dir/$f" ]; then echo "FAIL: $f is missing"; fail=1; fi
done
[ $fail -eq 0 ] && echo "PASS: package holds only what runs"
exit $fail
