#!/bin/bash
# Portal on http://localhost:5600 signed in through the local Sangam (start-sangam.sh first). PUB = publish folder.
export PATH=/opt/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1; S=$(cat /tmp/sangam-secret)
kill $(cat /tmp/portal-5600.pid 2>/dev/null) 2>/dev/null; sleep 1; rm -rf /dev/shm/chvd-5600; mkdir -p /dev/shm/chvd-5600
cd ${PUB:-/tmp/pub}; env ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://localhost:5600 Portal__Mode=Gateway Portal__DataRoot=/dev/shm/chvd-5600 \
  Sangam__Authority=http://localhost:5100/ Sangam__ClientId=chuvadi-portal Sangam__ClientSecret=$S setsid nohup dotnet ChuvadiReader.Web.dll > /tmp/portal-5600.log 2>&1 &
echo $! > /tmp/portal-5600.pid; sleep 5; curl -s -o /dev/null -w "portal 5600: %{http_code}\n" http://localhost:5600/healthz
