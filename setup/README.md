# Setup script for Ubiquiti mFi mPower devices

## Notes

The setup script and the modifications in the `mods` folder should allow to customize Ubiquiti mFi mPower devices easily towards a standalone mode, that means **WITHOUT** the mFI Controller. The script is sadly missing a proper argument parser and relies on correct input order but should do its job. **Make sure to double check the input, especially the number of ports and correct number of list elements!** If the latest firmware 2.1.11 from [here](https://www.ui.com/download/mfi/mpower) is not installed, the script will complain. **Use at your own risk!**

Another similar toolbox which looks more advanced and better documented can be found [here](https://github.com/magcode/mpower-tools). There are differences though.

The setup script from here allows to change the _port names_, the _initial port states_, the _port lock states_ and the _device name_.

**Be ware that all modifications will per default be installed when `setup.py` is used!** They serve the following purpose:

- **`certificate`**: Replaces the device certificate(s) and restart the web server. The corresponding files `key.pem`, `fullchain.pem`, `ca.pem`, `server.pem` must be available in the folder `mods/certificate`, otherwise the installation will simply do nothing.
- **`cleanup`**: Makes sure to cleanup old device stats after each reboot.
- **`ledoff`**: Disables the device LED after some time.
- **`nocontroller`**: Makes the device stop waiting for the mFi Controller as shown [here](https://github.com/magcode/mpower-tools/tree/master/nocontroller) and [here](https://community.ui.com/questions/mPower-default-outlet-state-on-boot-no-controller/390e5e67-44e8-4f94-a914-77d32380d6d1). This is essential for Wi-Fi only devices like the mPower and mPower mini. Without this, the WLAN connection will be disconnected unexpectedly if WPA2 is used. Only a full power-cycle will help in that case.
- **`vpower`**: Helper to set initial port states. Without this, initial port states from the script are lost after the next boot.

**The installation of individual mods can currently only be skipped by modifying the script.**

The SSH connection to Ubiquiti mFi mPower is quite slow. Adding something like this to your `~/.ssh/config` file will enable SSH multiplexing which will speed things up! The settings will also make sure to get use suitable (weak) SSH settings:

```ssh
# ssh -F ~/.ssh/config ubnt@<MFI_HOST>
# scp -O -F ~/.ssh/config ubnt@<MFI_HOST>

Host <MFI_HOST_SELECTION>
    ControlMaster auto
    ControlPath ~/.ssh/sockets/m-%r@%h:%p
    ControlPersist 60m
    HostkeyAlgorithms +ssh-rsa
    KexAlgorithms +diffie-hellman-group1-sha1
    Ciphers +3des-cbc,aes128-cbc,aes256-cbc
	PubkeyAcceptedKeyTypes +ssh-rsa
	# IdentityFile ~/.ssh/id_rsa
	# IdentitiesOnly yes
    # UserKnownHostsFile ~/.ssh/known_hosts
    # StrictHostKeyChecking no
```

**Replace `<MFI_HOST_SELECTION>` to fit your setup, e.g. `my-mfi-device`, `my-mfi-device-*`, `10.0.0.1`, `192.168.0.100, 192.168.13.101`, ... and DO NOT USE bare `*`. Otherwise all connections will use settings from above!**

## Usage example

```bash
#./setup.sh "$host" "$ports" "$labels" "$locks" "$relays" "$name"
./setup.sh "192.168.0.123" "3" "Device 1|Device 2|Device 3" "0|0|0" "1|1|1" "my-mfi-device"
```

## Reboot

```bash
# SSH (shell freezes for some time)
ssh "ubnt@$host"
reboot
```
