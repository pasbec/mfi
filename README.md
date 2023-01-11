# Asynchronous Python API for mFi mPower devices

## Some API Description
https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269

## Usage example
```python
import asyncio

import aiohttp

from mfi.mpower import MPowerDevice

async def main():

    data = {
        "host": "name_or_ip",
        "username": "ubnt",
        "password": "ubnt",
        "use_ssl": True,
        "verify_ssl": False,
    }

    async with aiohttp.ClientSession() as session:
        async with MPowerDevice(**data, session=session) as device:

            # Print device info
            print(device)

            # Print all sensors and their data
            sensors = await device.create_sensors()
            for sensor in sensors:
                print(sensor)

            # Print all switches and their state
            switches = await device.create_switches()
            for switch in switches:
                print(switch)

            # Turn port 1 off and toggle it afterwards back on
            switch1 = await device.create_switch(1)
            await switch1.set(False)
            await asyncio.sleep(5)
            await switch1.toggle()

asyncio.run(main())
```