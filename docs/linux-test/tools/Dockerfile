ARG REL=24.04
FROM ubuntu:${REL}
ENV DEBIAN_FRONTEND=noninteractive
COPY chuvadi-reader_1.0.0~preview_amd64.deb five-pages.pdf /opt/t/
RUN apt-get update -qq && apt-get install -y -q /opt/t/chuvadi-reader_1.0.0~preview_amd64.deb xvfb dbus dbus-x11 x11-apps imagemagick locales >/dev/null \
 && sed -i 's/# en_IN UTF-8/en_IN UTF-8/; s/# de_DE.UTF-8/de_DE.UTF-8/' /etc/locale.gen && locale-gen >/dev/null \
 && useradd -m tester
