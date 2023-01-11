#!/bin/sh
install='/etc/persistent/rc.poststart.d/nocontroller'
umount '/usr/etc/syswrapper.sh' 2> '/dev/null'
sed 's/pkill -9 mcad/exit 0\n        pkill -9 mcad/;s/pkill -9 wpa_supplicant/exit 0\n        pkill -9 wpa_supplicant/' '/usr/etc/syswrapper.sh' > "$install/syswrapper.sh"
chmod +x "$install/syswrapper.sh"
mount --bind "$install/syswrapper.sh" '/usr/etc/syswrapper.sh'
sed -i 's/mcad$/mcad -d/g' '/etc/inittab'
kill -HUP 1
pkill -9 mcad
