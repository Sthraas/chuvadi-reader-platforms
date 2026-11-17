#!/bin/bash
# Starts the local test Sangam (published to /tmp/sangam-pub) on http://localhost:5100 with PostgreSQL 16 in /tmp/pgdata,
# and registers the portal client "chuvadi-portal" for http://localhost:5600/. Test environment only. See ../../../docs/web-test/SETUP.md.
export PATH=/opt/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1
PGBIN=/usr/lib/postgresql/16/bin
if [ ! -d /tmp/pgdata ]; then
  mkdir -p /tmp/pgdata && chown postgres /tmp/pgdata && su postgres -c "$PGBIN/initdb -D /tmp/pgdata -A trust" >/dev/null
fi
pgrep -f "postgres -D /tmp/pgdata" >/dev/null || su postgres -c "$PGBIN/pg_ctl -D /tmp/pgdata -o '-p 5432 -k /tmp' -l /tmp/pg.log start" >/dev/null
sleep 2
su postgres -c "psql -h /tmp -p 5432 -Atc \"select 1 from pg_roles where rolname='sangam_identity'\"" | grep -q 1 || \
  su postgres -c "psql -h /tmp -p 5432 -c \"create role sangam_identity login password 'sangam_dev' createdb\" -c \"create database sangam_identity owner sangam_identity\"" >/dev/null
[ -f /tmp/sangam-secret ] || head -c 32 /dev/urandom | base64 | tr -d '/+=' > /tmp/sangam-secret
S=$(cat /tmp/sangam-secret)
pgrep -f Sangam.Identity.Server.dll >/dev/null && { echo "Sangam already running"; exit 0; }
cd /tmp/sangam-pub && ASPNETCORE_ENVIRONMENT=Development ASPNETCORE_URLS=http://localhost:5100 Sangam__Issuer=http://localhost:5100/ \
  Sangam__Clients__chuvadi__ClientId=chuvadi-portal Sangam__Clients__chuvadi__Kind=application \
  Sangam__Clients__chuvadi__BaseUrl=http://localhost:5600/ Sangam__Clients__chuvadi__Secret=$S \
  setsid nohup dotnet Sangam.Identity.Server.dll > /tmp/sangam.log 2>&1 &
for i in $(seq 1 60); do curl -s -o /dev/null http://localhost:5100/.well-known/openid-configuration && { echo "Sangam up"; exit 0; }; sleep 0.5; done; echo "Sangam NOT up"; tail -20 /tmp/sangam.log
