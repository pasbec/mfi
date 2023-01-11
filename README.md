# mfi-mpower-async-api

## API
https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269

## Usage example with internal session
```python
import asyncio

from mfi_mpower import MPowerDevice

async def main():

    settings = {
        "host": "mympower",
        "username": "admin",
        "password": "correcthorsebatterystaple",
        "use_ssl": True,
        "verify_ssl": True,
    }

    async with MPowerDevice(**settings) as device:

        print(device)

        sensors = await device.create_sensors()
        for sensor in sensors:
            print(sensor)

        switches = await device.create_switches()
        for switch in switches:
            print(switch)

asyncio.run(main())
```

## Usage example with external session
```python
import aiohttp
import asyncio

from mfi_mpower import MPowerDevice

async def main():

    settings = {
        "host": "mympower",
        "username": "admin",
        "password": "correcthorsebatterystaple",
        "use_ssl": True,
        "verify_ssl": True,
    }

    async with aiohttp.ClientSession() as session:
        async with MPowerDevice(**settings, session=session) as device:

            print(await device.create_sensor(1))

            switch1 = await device.create_switch(1)
            await switch1.set(False)
            await asyncio.sleep(5)
            await switch1.toggle()

asyncio.run(main())
```