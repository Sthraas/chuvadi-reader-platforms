#!/bin/bash
# usage: start-portal.sh <port> <mode> [extra env...]
port=$1; mode=$2; shift 2
export PATH=/opt/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1
mkdir -p /dev/shm/chvd-$port
cd ${PUB:-/tmp/pub}
env ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://127.0.0.1:$port Portal__Mode=$mode \
  Portal__DataRoot=/dev/shm/chvd-$port "Logging__LogLevel__Microsoft.AspNetCore=Information" "$@" \
  dotnet ChuvadiReader.Web.dll > /tmp/portal-$port.log 2>&1 &
echo $! > /tmp/portal-$port.pid
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:$port/healthz && { echo up after $i x 0.25s; exit 0; }; sleep 0.25; done; echo NOT UP; tail -20 /tmp/portal-$port.log
