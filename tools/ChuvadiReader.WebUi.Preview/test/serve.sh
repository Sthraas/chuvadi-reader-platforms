#!/bin/bash
# usage: serve.sh  -> (re)builds the preview; portal desktop :5101, Windows :5102, portal tablet :5103, portal phone :5104
export PATH=${DOTNET_ROOT:-$HOME/.dotnet}:$PATH DOTNET_NOLOGO=1
S=${WEBUI_TEST_DIR:-/tmp/chuvadi-webui-test}; mkdir -p $S
pkill -f ChuvadiReader.WebUi.Preview.dll; sleep 1
cd "$(dirname "$0")/../../.."
dotnet build tools/ChuvadiReader.WebUi.Preview -c Release --no-restore 2>&1 | grep -E " error |Warn|Error" | sort -u
cd tools/ChuvadiReader.WebUi.Preview
# name:port:platform:formfactor
for pp in web:5101:web:desktop windows:5102:windows:desktop webtablet:5103:web:tablet webphone:5104:web:phone; do
  IFS=: read n port plat ff <<< "$pp"
  PREVIEW_PLATFORM=$plat PREVIEW_FORMFACTOR=$ff ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://127.0.0.1:$port Logging__LogLevel__Default=Warning nohup dotnet bin/Release/net10.0/ChuvadiReader.WebUi.Preview.dll > $S/$n.log 2>&1 &
done
for port in 5101 5102 5103 5104; do for i in $(seq 1 30); do [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$port/)" = 200 ] && break; sleep 1; done; done
echo up
