FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -q cups cups-pdf >/dev/null \
 && sed -i 's/^Listen localhost:631/Listen 0.0.0.0:631/; s/<Location \/>/<Location \/>\n  Allow all/; s/<Location \/admin>/<Location \/admin>\n  Allow all/' /etc/cups/cupsd.conf \
 && echo "ServerAlias *" >> /etc/cups/cupsd.conf && echo "DefaultEncryption Never" >> /etc/cups/cupsd.conf
CMD sh -c "cupsd && sleep 2 && lpadmin -p RemotePDF -E -v cups-pdf:/ -m lsb/usr/cups-pdf/CUPS-PDF_opt.ppd -o printer-is-shared=true && lpadmin -d RemotePDF && cupsctl --share-printers --remote-any && pkill cupsd; while pgrep -x cupsd >/dev/null; do sleep 0.5; done; exec cupsd -f"
