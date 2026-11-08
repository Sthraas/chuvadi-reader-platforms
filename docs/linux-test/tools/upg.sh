#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null; apt-get install -y -q xvfb dbus-x11 imagemagick >/dev/null 2>&1
apt-get install -y -q /u/chuvadi-reader_0.9.0~preview_amd64.deb >/dev/null 2>&1; echo "old installed: $(dpkg-query -W -f='${Version}' chuvadi-reader)"
useradd -m tester
su - tester -c 'WAIT=12 /opt/run.sh upg-old' | grep -E "ALIVE|NOT"
python3 - <<'P' 2>/dev/null || su - tester -c "sed -i 's/^{/{\"theme\":\"Dark\",/' ~/.config/Chuvadi/settings.json"
P
su - tester -c "sed -i 's/^{/{\"theme\":\"Dark\",/' ~/.config/Chuvadi/settings.json; head -c 120 ~/.config/Chuvadi/settings.json; echo"
apt-get install -y -q /u/chuvadi-reader_1.0.0~preview_amd64.deb > /tmp/up.log 2>&1; echo "upgrade rc=$? now: $(dpkg-query -W -f='${Version}' chuvadi-reader)"; grep -iE "warn|error" /tmp/up.log | head -3
su - tester -c 'WAIT=12 /opt/run.sh upg-new' | grep -E "ALIVE|NOT|rror"
su - tester -c "grep -o '\"theme\":\"[A-Za-z]*\"' ~/.config/Chuvadi/settings.json; grep -c five-pages ~/.config/Chuvadi/settings.json"
su - tester -c "echo '{garbage' > ~/.config/Chuvadi/settings.json"
su - tester -c 'WAIT=12 /opt/run.sh upg-corrupt' | grep -E "ALIVE|NOT|rror|xception"
su - tester -c "head -c 200 ~/.config/Chuvadi/settings.json; echo; ls ~/.config/Chuvadi/"
