"""
mFi mPower

Direct async API for Ubiquiti mFi mPower devices which are sadly EOL since 2015.

Ubiquiti mFi mPower Devices use an ancient and unsecure OpenSSL version (1.0.0g 18 Jan 2012)
even with the latest available mFi firmware 2.1.11 from here:
    https://www.ui.com/download/mfi/mpower

SLL connections are therefore limited to TLSv1.0. The ciphers were constraint to AES256-SHA,
AES128-SHA or SEED-SHA to enforce 2048 bit strength and avoid DES and RC4. This results in the
highest possible rating according to the nmap enum-cipher-script which is documented here:
    https://nmap.org/nsedoc/scripts/ssl-enum-ciphers.html

Be aware that SSL is only supported until TLSv1.0 is eventually removed from Python - at least
unless someone finds a way to replace the OpenSSL binary with a more recent version until then.

A brief description of the old API can be found here:
    https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269

Some additional "reverse engineering" was necessary to realize this API but there still seems no
way to extract board or device model information via HTTP (SSH would be an option though).
"""
from .device import MPowerDevice
from .entities import MPowerSensor, MPowerSwitch
from .exceptions import (
    CannotConnect,
    InvalidAuth,
    InvalidData,
    InvalidResponse,
)

__version__ = "1.0.0"
