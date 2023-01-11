#!/bin/sh
install='/etc/persistent/rc.poststart.d/vpower'
sleep 10
[ -e '/etc/persistent/cfg/vpower_cfg.bak' ] && cp '/etc/persistent/cfg/vpower_cfg.bak' '/etc/persistent/cfg/vpower_cfg'
