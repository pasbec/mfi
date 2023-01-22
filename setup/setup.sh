#!/bin/bash

echo

if [[ -z "$1" ]]; then
  echo "No host given!"
  echo
  exit 1
else
  host="$1"
fi

if [[ -z "$1" ]]; then
  echo "No port count given!"
  echo
  exit 1
else
  case "$2" in
    1|"1"|3|"3"|6|"6")
    ports="$2"
    ;;
    *)
    echo "Port count is not valid (1, 3, 6)!"
    echo
    exit 1
  esac
fi

if [[ ! -z "$3" ]]; then
  vars="$3"
  IFS='|'; i=0; for var in $vars; do ((i++)); unset IFS; done
  if [[ "$i" != "$ports" ]]; then
    echo "Label string with separator '|' does not match port count!"
    echo
    exit 1
  else
    labels="$vars"
  fi
fi

if [[ ! -z "$4" ]]; then
  vars="$4"
  IFS='|'; i=0; for var in $vars; do ((i++)); unset IFS; done
  if [[ "$i" != "$ports" ]]; then
    echo "Locks string with separator '|' does not match port count!"
    echo
    exit 1
  else
    locks="$vars"
  fi
fi

if [[ ! -z "$5" ]]; then
  vars="$5"
  IFS='|'; i=0; for var in $vars; do ((i++)); unset IFS; done
  if [[ "$i" != "$ports" ]]; then
    echo "Relays string with separator '|' does not match port count!"
    echo
    exit 1
  else
    relays="$vars"
  fi
fi

name="$6"

###############################################################################

fw="MF.v2.1.11"
user="ubnt"
hash="" # WARNING: The hash variable MUST be EMPTY or contain a CORRECT/KNOWN PASSWORD-HASH (e.g. extracted from another device)!      
led="100"
tz="" # GMT-1GDT
ntp=""

mods="nocontroller|certificate|ledoff|vpower|cleanup"

###############################################################################

# Config
echo "Config"
echo

echo "host   = $host"
echo "ports  = $ports"
echo "labels = $labels"
echo "locks  = $locks"
echo "relays = $relays"
echo "name   = $name"
echo
echo "fw     = $fw"
echo "user   = $user"
echo "hash   = $hash"
echo "led    = $led"
echo "tz     = $tz"
echo "ntp    = $ntp"
echo "mods   = $mods"
echo

read -sp "Check input and press enter to continue"
echo

###############################################################################

userhost="$user@$host"
ssh="ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 -oHostKeyAlgorithms=+ssh-rsa -oCiphers=+aes128-cbc $user@$host"

pers="/etc/persistent"

modsystem=0
modlabels=0
modvpower=0
modinstall=0

###############################################################################

run() {

  local cmd="$1"

  [[ -z "$cmd" ]] && return 1

  echo -n $($ssh "$cmd")
}

getCfg() {

  local cfg="$1"
  local key="$2"

  [[ -z "$cfg" ]] && return 1
  [[ -z "$key" ]] && return 1

  echo -n "grep '$key' '$cfg' 2> /dev/null | sed 's/$key=//g'"
}

setCfg() {

  local cfg="$1"
  local key="$2"
  local val="$3"

  [[ -z "$cfg" ]] && return 1
  [[ -z "$key" ]] && return 1

  if [[ -z "$val" ]]; then
    echo -n "sed -i '/$key/d' '$cfg' 2> /dev/null"
  else
    echo -n "grep -q '$key' '$cfg' 2> /dev/null && sed -i 's/$key=.*/$key=$val/g' '$cfg' || echo '$key=$val' >> '$cfg'"
  fi
}

checkCfg() {

  local cfg="$1"
  local key="$2"
  local val="$3"
  local desc="$4"
  local enstat="$5"

  [[ -z "$cfg" ]] && return 1
  [[ -z "$key" ]] && return 1

  local cur="$(run "$(getCfg "$cfg" "$key")")"

  echo -n "Detected $desc '$cur' ..."

  if [[ "$cur" == "$val" ]]; then
    echo " OK"
    return 0
  else
    echo " FAIL"
    echo -n "Setting new $desc to '$val' ..."
    run "$(setCfg "$cfg" "$key" "$val")"
    local new="$(run "$(getCfg "$cfg" "$key")")"
    if [[ "$new" == "$val" ]]; then
      if [[ "$enstat" == 'yes' ]]; then
        local sb=$(echo "$key" | awk -F . '{print $1}')
        run "$(setCfg "$cfg" "$sb.status" 'enabled')"
        run "$(setCfg "$cfg" "$sb.1.status" 'enabled')"
      fi
      echo " OK"
      return 1
    else
      echo " ERROR"
      echo "An internal error occured!"
      echo
      exit 1
    fi
  fi
}

readFlash() { echo -n "cfgmtd -r -p '/etc'"; }

writeFlash() { echo -n "cfgmtd -w -p '/etc' '/tmp/system.cfg'"; }

reboot() { echo -n "reboot"; }

###############################################################################

checkSystem() {

  local key="$1"
  local val="$2"
  local desc="$3"
  local enstat="$4"

  [[ -z "$key" ]] && return 1

  checkCfg '/tmp/system.cfg' "$key" "$val" "$desc" "$enstat"
  if [[ "$?" == 1 ]]; then
    modsystem=1
  fi
}

checkLabels() {

  local vals="$1"

  [[ -z "$vals" ]] && return 1

  IFS='|'; i=0; for val in $vals; do ((i++)); unset IFS
    val=$(echo $val | awk '{$1=$1};1')
    checkCfg "$pers/cfg/config_file" "port.$(($i-1)).label" "$val" "label of port $i"
    if [[ "$?" == 1 ]]; then
      modlabels=1
    fi
  done
}

checkVpower() {

  local key="$1"
  local vals="$2"

  [[ ! "$key" =~ ^(lock|relay)$ ]] && return 1
  [[ -z "$vals" ]] && return 1

  IFS='|'; local i=0; for val in $vals; do ((i++)); unset IFS
    val=$(echo $val | awk '{$1=$1};1')
    if [[ "$val" =~ ^[0-1]{1}$ ]]; then
      checkCfg "$pers/cfg/vpower_cfg" "vpower.$i.$key" "$val" "$key state of port $i"
      if [[ "$?" == 1 ]]; then
        run "echo $val > '/proc/power/$key$i'"
        run "cp '$pers/cfg/vpower_cfg' '$pers/cfg/vpower_cfg.bak'"
        modvpower=1
      fi
    else
      echo "Skipping lock state of port $i... INVALID"
    fi
  done
}

checkMod() {

  local desc="$1"

  local scr="rc.poststart.d/$desc/start.sh"
  local scrok=$($ssh "[ -e '$pers/$scr' ] && echo 1 || echo 0")
  local curfw=$($ssh "cat '/etc/version'")

  echo -n "Detecting $desc mod..."

  if [[ "$scrok" == 1 ]]; then
    echo " OK"
  else
    echo " FAIL"
    if [[ "$curfw" == "$fw" ]]; then
      echo "Installing $desc ..."
      $ssh "[ -f '$pers/rc.poststart' ] || echo '#!/bin/sh' > '$pers/rc.poststart'; chmod +x '$pers/rc.poststart'"
      $ssh "[ -d '$pers/rc.poststart.d' ] || mkdir '$pers/rc.poststart.d'"
      scp -pr "mods/$desc" "$userhost:$pers/rc.poststart.d"
      $ssh "grep -q '$pers/$scr' '$pers/rc.poststart' || echo '$pers/$scr' >> '$pers/rc.poststart'; '$pers/$scr'"
    fi
    modinstall=1
  fi
}

###############################################################################

# Start
echo "Start"
echo

# Copy public ssh key
echo "Copy ssh id"
ssh-copy-id "$userhost" 2> '/dev/null'
echo

# Check firmware
curfw=$(run "cat '/etc/version'")
echo -n "Detected firmware version '$curfw' ..."
if [[ "$curfw" == "$fw" ]]; then
  echo " OK"
  echo
else
  echo " ERROR"
  echo "Firmware upgrade necessary!"
  echo "Download latest firmware from here: https://dl.ui.com/mfi/2.1.11/firmware/M2M/firmware.bin"
  echo "Then follow: http://$host/upgrade.cgi"
  echo
  exit 1
fi

## Check system config
[[ ! -z "$name" ]] && checkSystem 'resolv.host.1.name' "$name" 'host name'
[[ ! -z "$hash" ]] && checkSystem 'users.1.password' "$hash" 'password hash' 'yes'
[[ ! -z "$led" ]] && checkSystem 'system.led' "$led" 'led state'
[[ ! -z "$tz" ]] && checkSystem 'system.timezone' "$tz" 'time zone'
[[ ! -z "$ntp" ]] && checkSystem 'ntpclient.1.server' "$ntp" 'time server' 'yes'
echo

# Check port labels
[[ ! -z "$labels" ]] && checkLabels "$labels" && echo

# Check vpower lock config
[[ ! -z "$locks" ]] && checkVpower 'lock' "$locks" && echo

# Check vpower relay config
[[ ! -z "$relays" ]] && checkVpower 'relay' "$relays" && echo

# Remove certificate mod to enforce certificate updates
$ssh "umount '/var/etc/server.pem' 2> /dev/null; umount '/var/etc/lighttpd.conf' 2> /dev/null; rm -rf /etc/persistent/rc.poststart.d/certificate"

# Check poststart mods
IFS='|'; i=0; for mod in $mods; do ((i++)); unset IFS
  checkMod "$mod"
done
echo

# Save changes
if [[ "$modsystem" == 1 || "$modlabels" == 1 || \
      "$modvpower" == 1 || "$modinstall" == 1 ]]; then
  echo 'Writing changes to flash ...'
  run "$(writeFlash)"
  if [[ "$?" == 0 ]]; then
    echo " OK"
    echo
  else
    echo " ERROR"
    echo "An internal error occured!"
    echo
    exit 1
  fi
fi

###############################################################################

echo "Done"
echo
exit 0
