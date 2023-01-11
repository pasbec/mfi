# mfi-mpower-async-api

## API
https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269

## Usage example with internal session
```python
import asyncio

from mfi_mpower import mFimPowerDevice

async def main():

    host = "mympower"
    username = "admin"
    password = "correcthorsebatterystaple"
    use_ssl = True
    verify_ssl = True

    async with mFimPowerDevice(host, username, password, use_ssl, verify_ssl) as device:

        # Show port data
        print(await device.data)

        # Switch first port off
        await device.set(1, False)
        
        # Sleep 5 seconds
        await asyncio.sleep(5)

        # Toggle first port
        await device.toggle(1)

asyncio.run(main())
```

## Usage example with external session
```python
import aiohttp
import asyncio

from mfi_mpower import mFimPowerDevice

async def main():

    host = "mympower"
    username = "admin"
    password = "correcthorsebatterystaple"
    use_ssl = True
    verify_ssl = True

    async with aiohttp.ClientSession() as session:
        async with mFimPowerDevice(host, username, password, use_ssl, verify_ssl, session) as device:

            # Show port data
            print(await device.data)

            # Switch first port off
            await device.set(1, False)
            
            # Sleep 5 seconds
            await asyncio.sleep(5)

            # Toggle first port
            await device.toggle(1)

asyncio.run(m