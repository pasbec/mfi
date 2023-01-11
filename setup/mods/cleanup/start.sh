#!/bin/sh
install='/etc/persistent/rc.poststart.d/cleanup'
rm '/etc/persistent/data/'* 2> /dev/null
