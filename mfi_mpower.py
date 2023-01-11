"""
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

Author: Pascal Beckstein, 2023
"""

from __future__ import annotations

import asyncio
from random import randrange
import ssl
import time

import aiohttp
from aiohttp import ClientResponse, ClientSession
from yarl import URL


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidResponse(Exception):
    """Error to indicate we received an invalid http status."""


class InvalidData(Exception):
    """Error to indicate we received invalid device data."""


class MPowerDevice:
    """mFi mPower device representation."""

    _host: str
    _url: URL
    _username: str
    _password: str
    _cache_time: float
    _eu_model: bool

    _cookie: str
    _session: bool
    _ssl: bool | ssl.SSLContext

    _updated: bool
    _authenticated: bool
    _time: float
    _data: dict

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_ssl: bool = True,
        verify_ssl: bool = True,
        cache_time: float = 0.0,
        eu_model: bool = False,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the device."""
        self._host = host
        self._url = URL(f"https://{host}" if use_ssl else f"http://{host}")
        self._username = username
        self._password = password
        self._cache_time = cache_time
        self._eu_model = eu_model

        self._cookie = "".join([str(randrange(9)) for i in range(32)])
        self._cookie = f"AIROS_SESSIONID={self._cookie}"

        if session is None:
            self.session = ClientSession()
            self._session = True
        else:
            self.session = session
            self._session = False

        if use_ssl:
            # NOTE: Ubiquiti mFi mPower Devices only support SSLv3 and TLSv1.0
            self._ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self._ssl.set_ciphers("AES256-SHA:AES128-SHA:SEED-SHA")
            self._ssl.load_default_certs()
            self._ssl.verify_mode = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
        else:
            self._ssl = False

        self._updated = False
        self._authenticated = False
        self._time = time.time()
        self._data = {}

    def __del__(self):
        """
        Delete the device.

        This closes the async connection if necessary as proposed here:
          https://stackoverflow.com/a/67577364/13613140
        """
        if self._session:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except Exception:  # pylint: disable=broad-except
                pass

    async def __aenter__(self):
        """Enter context manager scope."""
        await self.login()
        await self.update()
        return self

    async def __aexit__(self, *kwargs):
        """Leave context manager scope."""
        await self.logout()

    def __str__(self):
        """Represent this device as string."""
        name = __class__.__name__
        keys = ["hostname", "ip", "hwaddr", "model"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return f"{name}({vals})"

    @property
    def url(self) -> URL:
        """Return device URL."""
        return self._url

    @property
    def host(self) -> str:
        """Return device host."""
        return self._host

    @property
    def eu_model(self) -> bool:
        """Return whether this device is a EU model with type F sockets."""
        return self._eu_model

    @property
    def manufacturer(self) -> str:
        """Return the device manufacturer."""
        return "Ubiquiti"

    async def request(
        self, method: str, url: str | URL, data: dict | None = None
    ) -> ClientResponse:
        """Session wrapper for general requests."""
        _url = URL(url)
        if not _url.is_absolute():
            _url = self.url / str(_url).lstrip("/")
        try:
            resp = await self.session.request(
                method=method,
                url=_url,
                headers={"Cookie": self._cookie},
                data=data,
                ssl=self._ssl,
                chunked=None,
            )
        except asyncio.CancelledError as exc:
            raise asyncio.CancelledError(
                f"Request to device {self.hostname} was cancelled",
            ) from exc
        except asyncio.TimeoutError as exc:
            raise asyncio.TimeoutError(
                f"Request to device {self.hostname} timed out"
            ) from exc
        except aiohttp.ClientSSLError as exc:
            raise CannotConnect(
                f"Could not verify SSL certificate of device {self.hostname}"
            ) from exc
        except aiohttp.ClientError as exc:
            raise CannotConnect(
                f"Connection to device device {self.hostname} failed"
            ) from exc

        if resp.status != 200:
            raise InvalidResponse(
                f"Received bad HTTP status code from device {self.hostname}: {resp.status}"
            )

        # NOTE: Un-authorized request will redirect to /login.cgi
        if str(resp.url.path) == "/login.cgi":
            self._authenticated = False
        else:
            self._authenticated = True

        return resp

    async def login(self) -> None:
        """Login to this device."""
        if not self._authenticated:
            await self.request(
                "POST",
                "/login.cgi",
                data={"username": self._username, "password": self._password},
            )

            if not self._authenticated:
                raise InvalidAuth(
                    f"Login to device {self.hostname} failed due to wrong credentials"
                )

    async def logout(self) -> None:
        """Logout from this device."""
        if self._authenticated:
            await self.request("POST", "/logout.cgi")

    async def update(self) -> None:
        """Update sensor data."""
        await self.login()

        if not self._data or (time.time() - self._time) > self._cache_time:
            resp_status = await self.request("GET", "/status.cgi")
            resp_sensors = await self.request("GET", "/mfi/sensors.cgi")

            try:
                data = await resp_status.json()
                data.update(await resp_sensors.json())
            except aiohttp.ContentTypeError as exc:
                raise InvalidData(
                    f"Received invalid data from device {self.hostname}"
                ) from exc

            status = data.get("status", None)
            if status != "success":
                raise InvalidData(
                    f"Received invalid sensor update status from device {self.hostname}: {status}"
                )

            self._time = time.time()
            self._data = data

    @property
    def updated(self) -> bool:
        """Return if the device has already been updated."""
        return bool(self._data)

    @property
    def data(self) -> dict:
        """Return device data."""
        if not self._data:
            raise InvalidData(f"Device {self.hostname} must be updated first")
        return self._data

    @data.setter
    def data(self, data: dict) -> None:
        """Set device data."""
        self._data = data

    @property
    def host_data(self) -> dict:
        """Return the device host data."""
        return self.data.get("host", {})

    @property
    def fwversion(self) -> str:
        """Return the device host firmware version."""
        return self.host_data.get("fwversion", "")

    @property
    def hostname(self) -> str:
        """Return the device host name."""
        return self.host_data.get("hostname", self._host)

    @property
    def lan_data(self) -> dict:
        """Return the device LAN data."""
        return self.data.get("lan", {})

    @property
    def wlan_data(self) -> dict:
        """Return the device WLAN data."""
        return self.data.get("wlan", {})

    @property
    def ip(self) -> str:
        """Return the device IP address from LAN if connected, else from WLAN."""
        lan_connected = self.lan_data.get("status", "") != "Unplugged"
        if lan_connected:
            ip = self.lan_data.get("ip", "")
        else:
            ip = self.wlan_data.get("ip", "")
        return ip

    @property
    def hwaddr(self) -> str:
        """Return the device hardware address from LAN if connected, else from WLAN."""
        lan_connected = self.lan_data.get("status", "") != "Unplugged"
        if lan_connected:
            hwaddr = self.lan_data.get("hwaddr", "")
        else:
            hwaddr = self.wlan_data.get("hwaddr", "")
        return hwaddr

    @property
    def unique_id(self) -> str:
        """Return a unique device id from combined LAN/WLAN hardware addresses."""
        lan_hwaddr = self.lan_data.get("hwaddr", "")
        wlan_hwaddr = self.wlan_data.get("hwaddr", "")
        if lan_hwaddr and wlan_hwaddr:
            return f"{lan_hwaddr}-{wlan_hwaddr}"
        return ""

    @property
    def port_data(self) -> list[dict]:
        """Return the device port data."""
        return self.data.get("sensors", [])

    @property
    def ports(self) -> int:
        """Return the number of available device ports."""
        return len(self.port_data)

    @property
    def model(self) -> str:
        """Return the model name of this device as string."""
        ports = self.ports
        prefix = "mPower"
        suffix = " (EU)" if self._eu_model else ""
        if ports == 1:
            return f"{prefix} mini" + suffix
        if ports == 3:
            return prefix + suffix
        if ports in [6, 8]:
            return f"{prefix} PRO" + suffix
        return "Unknown"

    @property
    def description(self) -> str:
        """Return the device description as string."""
        ports = self.ports
        if ports == 1:
            return "mFi Power Adapter with Wi-Fi"
        if ports == 3:
            return "3-Port mFi Power Strip with Wi-Fi"
        if ports == 6:
            return "6-Port mFi Power Strip with Ethernet and Wi-Fi"
        if ports == 8:
            return "8-Port mFi Power Strip with Ethernet and Wi-Fi"
        return ""

    async def create_sensor(self, port: int) -> MPowerSensor:
        """Create a single sensor."""
        if not self.updated:
            await self.update()
        return MPowerSensor(self, port)

    async def create_sensors(self) -> list[MPowerSensor]:
        """Create all sensors as list."""
        if not self.updated:
            await self.update()
        return [MPowerSensor(self, i + 1) for i in range(self.ports)]

    async def create_switch(self, port: int) -> MPowerSwitch:
        """Create a single switch."""
        if not self.updated:
            await self.update()
        return MPowerSwitch(self, port)

    async def create_switches(self) -> list[MPowerSwitch]:
        """Create all switches as list."""
        if not self.updated:
            await self.update()
        return [MPowerSwitch(self, i + 1) for i in range(self.ports)]


class MPowerEntity:
    """mFi mPower entity baseclass."""

    _device: MPowerDevice
    _port: int
    _data: dict

    def __init__(self, device: MPowerDevice, port: int) -> None:
        """Initialize the entity."""
        self._device = device
        self._port = port

        if not device.updated:
            raise InvalidData(f"Device {device.hostname} must be updated first")

        self._data = device.port_data[self._port - 1]

        if port < 1:
            raise ValueError(
                f"Port number {port} for device {device.hostname} is too small: 1-{device.ports}"
            )
        if port > device.ports:
            raise ValueError(
                f"Port number {port} for device {device.hostname} is too large: 1-{device.ports}"
            )

    def __str__(self):
        """Represent this entity as string."""
        name = __class__.__name__
        host = f"hostname={self._device.hostname}"
        keys = ["port", "label"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return f"{name}({host}, {vals})"

    async def update(self) -> None:
        """Update entity data from device data."""
        await self._device.update()
        self._data = self._device.port_data[self._port - 1]

    @property
    def device(self) -> MPowerDevice:
        """Return the entity device."""
        return self._device

    @property
    def data(self) -> dict:
        """Return all entity data."""
        return self._data

    @data.setter
    def data(self, data: dict) -> None:
        """Update entity data."""
        self._data = data

    @property
    def unique_id(self) -> str:
        """Return unique entity id from unique device id and port."""
        return f"{self.device.unique_id}-{self.port}"

    @property
    def port(self) -> int:
        """Return the port number (starting with 1)."""
        return int(self._port)

    @property
    def label(self) -> str:
        """Return the entity label."""
        return str(self._data.get("label", ""))

    @property
    def output(self) -> bool:
        """Return the current output state."""
        return bool(self._data["output"])

    @property
    def relay(self) -> bool:
        """Return the initial output state which is applied after device boot."""
        return bool(self._data["relay"])

    @property
    def lock(self) -> bool:
        """Return the output lock state which prevents switching if enabled."""
        return bool(self._data["lock"])


class MPowerSensor(MPowerEntity):
    """mFi mPower sensor representation."""

    _precision: dict[str, float | None] = {
        "power": None,
        "current": None,
        "voltage": None,
        "powerfactor": None,
    }

    def __str__(self):
        """Represent this sensor as string."""
        name = __class__.__name__
        host = f"hostname={self._device.hostname}"
        keys = ["port", "label", "power", "current", "voltage", "powerfactor"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return f"{name}({host}, {vals})"

    def _value(self, key: str, scale: float = 1.0) -> float:
        """Process sensor value with fallback to 0."""
        value = scale * float(self._data.get(key, 0))
        precision = self.precision.get(key, None)
        if precision is not None:
            return round(value, precision)
        return value

    @property
    def precision(self) -> dict:
        """Return the precision dictionary."""
        return self._precision

    @property
    def power(self) -> float:
        """Return the output power [W]."""
        return self._value("power")

    @property
    def current(self) -> float:
        """Return the output current [A]."""
        return self._value("current")

    @property
    def voltage(self) -> float:
        """Return the output voltage [V]."""
        return self._value("voltage")

    @property
    def powerfactor(self) -> float:
        """Return the output current factor ("real power" / "apparent power") [%]."""
        return self._value("powerfactor", scale=100)


class MPowerSwitch(MPowerEntity):
    """mFi mPower switch representation."""

    def __str__(self):
        """Represent this switch as string."""
        name = __class__.__name__
        host = f"hostname={self._device.hostname}"
        keys = ["port", "label", "output", "relay", "lock"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return f"{name}({host}, {vals})"

    async def set(self, output: bool, refresh: bool = True) -> None:
        """Set output to on/off."""
        await self._device.request(
            "POST", "/mfi/sensors.cgi", data={"id": self._port, "output": int(output)}
        )
        if refresh:
            await self.update()

    async def turn_on(self, refresh: bool = True) -> None:
        """Turn output on."""
        await self.set(True, refresh=refresh)

    async def turn_off(self, refresh: bool = True) -> None:
        """Turn output off."""
        await self.set(False, refresh=refresh)

    async def toggle(self, refresh: bool = True) -> None:
        """Toggle output."""
        await self.update()
        output = not bool(self._data["output"])
        await self.set(output, refresh=refresh)
