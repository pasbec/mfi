# Asynchronous Python API for mFi mPower devices

## Notes

This package provides a _direct_ asynchronous API for Ubiquiti mFi mPower devices based on [AIOHTTP](https://docs.aiohttp.org/en/stable/) and [AsyncSSH](https://asyncssh.readthedocs.io/en/latest/). The mFi product line which are is sadly EOL since 2015 and the latest available mFi firmware is version 2.1.11, which can be found [here](https://www.ui.com/download/mfi/mpower).

**Please note that even with the latest available mFi firmware, Ubiquiti mFi mPower Devices are quite unhurried and use OpenSSL 1.0.0g (18 Jan 2012) as well as Dropbear SSH 0.51 (27 Mar 2008).**

SLL connections are thus limited to TLSv1.0. The mFi mPower package pins the cipher use explicitly to `AES128-SHA` in order to get the fastest 2048 bit strength and avoid DES and RC4. This results in the highest possible rating according to the [nmap enum-cipher-script](https://nmap.org/nsedoc/scripts/ssl-enum-ciphers.html). The default device certificate is self-signed and too weak (512 bit) for todays standards. SSL certificate verification is therefore disabled by default. The certificate can however be replaced with your own.

As mFi mPower devices are usually communicating only in a local network and not via the internet, some old SSL still seems to be much better than no encryption at all.

**Be aware that SSL is only supported until TLSv1.0 is eventually removed from Python - at least unless someone finds a way to replace the OpenSSL binary with a more recent version until then.**

A brief description of the old "REST" API can be found in the [UI Community](https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269) but some additional "reverse engineering" was necessary to extract device info. There still seems no way to extract board or model information without SSH. Any hints are very much appreciated!

To extract board information via SSH, only the `ssh-rsa` host key algorithm in combination with the `diffie-hellman-group1-sha1` key exchange is supported. The latter is available as [legacy option](http://www.openssh.com/legacy.html). There is also a [known bug](https://github.com/ronf/asyncssh/issues/263) in older Dropbear versions which truncates the list of offered key algorithms. The mFi mPower package therefore limits the offered key algorithms to `ssh-rsa` and the encryption algorithm to `aes128-cbc`. Known host checks will be [disabled](https://github.com/ronf/asyncssh/issues/132) as this would require user interaction.

## Basic example

```python
import asyncio
import aiohttp

from mfi_mpower.device import MPowerDevice

async def main():

    data = {
        "host": "name_or_ip",
        "username": "ubnt",
        "password": "ubnt",
        "use_ssl": True,
        "verify_ssl": False,
        "board_info": None,
    }

    async with aiohttp.ClientSession() as session:
        async with MPowerDevice(**data, session=session) as device:

            # Turn port 1 off and toggle it afterwards back on
            switch1 = await device.create_switch(1)
            await switch1.set(False)
            await asyncio.sleep(5)
            await switch1.toggle()

asyncio.run(main())
```

## Better example

```python
import asyncio
import aiohttp

from mfi_mpower.device import MPowerDevice

async def query(host: str) -> None:
    """Async query"""

    data = {
        "username": "ubnt",
        "password": "ubnt",
        "use_ssl": True,
        "verify_ssl": False,
        "board_info": None,
    }

    data["host"] = host

    async with aiohttp.ClientSession() as session:
        async with MPowerDevice(**data, session=session) as device:

            # Print device info
            print(device)

            # Print device board data
            print(device.board)

            # Print all switches and their state
            switches = await device.create_switches()
            for switch in switches:
                print(switch)

            # Print all sensors and their data
            sensors = await device.create_sensors()
            for sensor in sensors:
                print(sensor)


async def main() -> None:
    """Async main"""

    hosts = [
        "host1", "host2", "host3",
        "host4", "host5", "host6",
    ]

    await asyncio.gather(*[query(host) for host in hosts])

asyncio.run(main())
```
