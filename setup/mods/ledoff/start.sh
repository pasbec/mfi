#!/bin/sh
install='/etc/persistent/rc.poststart.d/ledoff'
echo 99 > '/proc/led/status'
