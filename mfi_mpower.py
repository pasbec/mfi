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
unless someone finds a way to replace OpenSSL with a more recent version until then.

A brief description of the old API can be found here:
    https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269
"""

from __future__ import annotations

from aiohttp import ClientSession, ClientResponse
import asyncio
from random import randrange
import ssl
import time


class BadResponse(Exception):
    """Error to indicate we got a response status != 200."""


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class UpdateError(Exception):
    """Error to indicate that there was an update error."""


class MPowerDevice:
    """mFi mPower device representation."""

    _host: str = None
    _url: str = None
    _username: str = None
    _password: str = None
    _cache_time: float = None
    _eu_model: bool = None

    _session = None
    _ssl = None

    _authenticated: bool = None
    _time: float = None
    _data: list[dict] = None

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_ssl: bool = True,
        verify_ssl: bool = True,
        cache_time: float = 0.0,
        eu_model: bool = False,
        session: ClientSession = None,
    ) -> None:
        self._host = host
        self._url = f"https://{host}" if use_ssl else f"http://{host}"
        self._username = username
        self._password = password
        self._cache_time = cache_time
        self._eu_model = eu_model

        cookie = "".join([str(randrange(9)) for i in range(32)])
        cookie = f"AIROS_SESSIONID={cookie}"

        if session is None:
            self.session = ClientSession(headers={"Cookie": cookie})
            self._session = True
        else:
            self.session = session
            session.headers.add("Cookie", cookie)
            self._session = False

        if use_ssl:
            # NOTE: Ubiquiti mFi mPower Devices only support SSLv3 and TLSv1.0
            self._ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self._ssl.set_ciphers("AES256-SHA:AES128-SHA:SEED-SHA")
            self._ssl.load_default_certs()
            self._ssl.verify_mode = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
        else:
            self._ssl = False

        self._authenticated = False
        self._time = time.time()
        self._data = []

    def __del__(self):
        """
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
        await self.login()
        await self.update()
        return self

    async def __aexit__(self, *excinfo):
        await self.logout()

    def __str__(self):
        if not self._data:
            return f"{self.model} ({self._host})"
        else:
            pstr = "ports" if self.ports > 1 else "port"
            return f"{self.model} [{self._host}, {self.ports} {pstr}]"

    async def request(self, method: str, url: str, data: dict = None) -> ClientResponse:
        """General request method."""
        _url = self._url + url if url.startswith("/") else url
        resp = await self.session.request(
            method=method,
            url=_url,
            data=data,
            ssl=self._ssl,
            chunked=None,
        )

        if resp.status != 200:
            raise BadResponse(f"Bad HTTP status code: {resp.status}")

        return resp

    async def login(self) -> None:
        """Login method."""
        if not self._authenticated:
            try:
                resp = await self.request(
                    "POST",
                    "/login.cgi",
                    data={"username": self._username, "password": self._password},
                )
            except Exception as exception:
                self.__del__()  # pylint: disable=unnecessary-dunder-call
                raise CannotConnect(str(exception)) from exception

            # NOTE: Successful login will redirect to /power
            if not str(resp.url).endswith("/power"):
                raise InvalidAuth("Login failed due to wrong credentials")

            self._authenticated = True

    async def logout(self) -> None:
        """Logout method."""
        if self._authenticated:
            await self.request("POST", "/logout.cgi")

            self._authenticated = False

    async def update(self) -> None:
        """Update method for sensor data."""
        await self.login()
        if not self._data or (time.time() - self._time) > self._cache_time:
            resp = await self.request("GET", "/mfi/sensors.cgi")
            json = await resp.json()
            status = json.get("status", None)
            if status != "success":
                raise UpdateError(f"Bad sensor update status: {status}")
            self._time = time.time()
            self._data = json["sensors"]

    @property
    async def config(self) -> str:
        """Configuration retrieval method."""
        await self.login()
        resp = await self.request("GET", "/cfg.cgi")
        return await resp.text()

    @property
    def host(self) -> dict:
        """Device hostname."""
        return self._host

    @property
    def data(self) -> dict:
        """Device data."""
        return self._data

    @property
    def ports(self) -> int:
        """Number of available ports for this device."""
        return len(self._data)

    @property
    def eu_model(self) -> bool:
        """True if this is a EU model with type F sockets."""
        return self._eu_model

    @property
    def model(self) -> str:
        """Model of this device."""
        ports = self.ports
        eu = " (EU)" if self._eu_model else ""
        if ports == 1:
            return "mPower mini" + eu
        elif ports == 3:
            return "mPower" + eu
        elif ports == 6 or ports == 8:
            return "mPower PRO" + eu
        else:
            return "Unknown"

    @property
    def description(self) -> str:
        """Model of this device."""
        ports = self.ports
        if ports == 1:
            return "mFi Power Adapter with Wi-Fi"
        elif ports == 3:
            return "3-Port mFi Power Strip with Wi-Fi"
        elif ports == 6:
            return "6-Port mFi Power Strip with Ethernet and Wi-Fi"
        elif ports == 8:
            return "8-Port mFi Power Strip with Ethernet and Wi-Fi"
        else:
            return ""

    async def create_sensor(self, port: int) -> MPowerSensor:
        """Factory method for a single sensor."""
        await self.update()
        return MPowerSensor(self, port)

    async def create_sensors(self) -> list[MPowerSensor]:
        """Factory method for all sensors as list."""
        await self.update()
        return [MPowerSensor(self, i + 1) for i in range(self.ports)]

    async def create_switch(self, port: int) -> MPowerSwitch:
        """Factory method for a single switch."""
        await self.update()
        return MPowerSwitch(self, port)

    async def create_switches(self) -> list[MPowerSwitch]:
        """Factory method for all switch as list."""
        await self.update()
        return [MPowerSwitch(self, i + 1) for i in range(self.ports)]


class MPowerEntity:
    """mFi mPower entity baseclass."""

    _device: MPowerDevice = None
    _port: int = None
    _data: dict = None

    def __init__(self, device: MPowerDevice, port: int) -> None:
        self._device = device
        self._port = port

        data = self._device._data
        if not data:
            raise ValueError("Device must be updated to create entity")
        self._data = self._device._data[self._port - 1]

        ports = self._device.ports
        if port < 1:
            raise ValueError(f"Port number {port} is too small: 1-{ports}")
        elif port > ports:
            raise ValueError(f"Port number {port} is too large: 1-{ports}")

    def __str__(self):
        return " ".join([str(self._device), "Entity"])

    async def update(self) -> None:
        """Update entity data."""
        await self._device.update()
        data = self._device._data
        self._data.update(data[self._port - 1])

    @property
    def device(self) -> MPowerDevice:
        """Entity device."""
        return self._device

    @property
    def data(self) -> dict:
        """Entity data."""
        return self._data

    @property
    def port(self) -> int:
        """Port number (starting with 1)."""
        return int(self._port)

    @property
    def label(self) -> str:
        """Label."""
        return str(self._data.get("label", f"Port {self._port}"))

    @property
    def output(self) -> bool:
        """Output state."""
        return bool(self._data["output"])

    @property
    def relay(self) -> bool:
        """Initial output state which is applied after device boot."""
        return bool(self._data["relay"])

    @property
    def lock(self) -> bool:
        """Output lock state which prevents switching if enabled."""
        return bool(self._data["lock"])


class MPowerSensor(MPowerEntity):
    """mFi mPower sensor representation."""

    def __str__(self):
        keys = ["label", "power", "current", "voltage", "powerfactor"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return " ".join([str(self._device), f"Sensor {self._port}: {vals}"])

    @property
    def power(self) -> float:
        """Output power [W]."""
        return float(self._data["power"])

    @property
    def current(self) -> float:
        """Output current [A]."""
        return float(self._data["current"])

    @property
    def voltage(self) -> float:
        """Output voltage [V]."""
        return float(self._data["voltage"])

    @property
    def powerfactor(self) -> float:
        """Output current factor ("real power" / "apparent power") [1]."""
        return float(self._data["powerfactor"])


class MPowerSwitch(MPowerEntity):
    """mFi mPower switch representation."""

    def __str__(self):
        keys = ["label", "output", "relay", "lock"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return " ".join([str(self._device), f"Switch {self._port}: {vals}"])

    async def set(self, output: bool) -> None:
        """Set output to on/off."""
        await self._device.request(
            "POST", "/mfi/sensors.cgi", data={"id": self._port, "output": int(output)}
        )

    async def turn_on(self) -> None:
        """Turn output on."""
        await self.set(True)

    async def turn_off(self) -> None:
        """Turn output off."""
        await self.set(False)

    async def toggle(self) -> None:
        """Toggle output."""
        await self.update()
        output = not bool(self._data["output"])
        await self.set(output=output)
