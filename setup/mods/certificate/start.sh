#!/bin/sh
install='/etc/persistent/rc.poststart.d/certificate'
if [ -e "$install/key.pem" -a -e "$install/fullchain.pem" ]; then
  cat "$install/key.pem" "$install/fullchain.pem" > "$install/server.pem"
fi
if [ -e "$install/server.pem" ]; then
  umount '/var/etc/server.pem' 2> /dev/null
  mount --bind "$install/server.pem" '/var/etc/server.pem'
fi
if [ -e "$install/ca.pem" -a -e "$install/lighttpd.conf" ]; then
  umount '/var/etc/lighttpd.conf' 2> /dev/null
  mount --bind "$install/lighttpd.conf" '/var/etc/lighttpd.conf'
fi
pkill -9 lighttpd
