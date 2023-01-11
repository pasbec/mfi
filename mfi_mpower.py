from aiohttp import ClientSession
import asyncio
from random import randrange
import ssl
import time
from yarl import URL


class BadResponse(Exception):
    """Error to indicate we got a response statue != 200."""


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class Device:
    """
    Async API for Ubiquiti mFi mPower devices which are sadly EOL since 2015.

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

    _cookie = None
    _session = None
    _authenticated = None
    _time = None
    _data = None

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, *excinfo):
        await self.logout()

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_ssl: bool = True,
        verify_ssl: bool = True,
        cache_time: int = 0,
        session: ClientSession = None,
    ) -> None:
        """Initialize mFi mPower device object."""
        self._cookie = "AIROS_SESSIONID=" + "".join([str(randrange(9)) for i in range(32)])

        if session is None:
            self.session = ClientSession(headers={"Cookie": self._cookie})
            self._session = True
        else:
            self.session = session
            session.headers.add("Cookie", self._cookie)
            self._session = False

        self._authenticated = False
        self._time = time.time()

        self.host = host
        self.username = username
        self.password = password

        if use_ssl:
            # NOTE: Ubiquiti mFi mPower Devices only support SSLv3 and TLSv1.0
            self.ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.ssl.set_ciphers("AES256-SHA:AES128-SHA:SEED-SHA")
            self.ssl.load_default_certs()
            self.ssl.verify_mode = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
            self.session._base_url = URL(f"https://{self.host}")
        else:
            self.ssl = False
            self.session._base_url = URL(f"http://{self.host}")

        self.cache_time = cache_time

    def __del__(self):
        """
        Delete mFi mPower device object.

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

    async def login(self) -> None:
        """Login method."""
        if not self._authenticated:

            try:
                resp = await self.session.post(
                    "/login.cgi",
                    data={"username": self.username, "password": self.password},
                    ssl=self.ssl,
                    chunked=None,
                )
            except Exception as exc:
                self.__del__()  # pylint: disable=unnecessary-dunder-call
                raise CannotConnect(str(exc)) from exc

            if not resp.status == 200:
                raise BadResponse(f"Bad HTTP status code {resp.status}")

            # NOTE: Successful login will redirect back to /power
            if not str(resp.url).endswith("power"):
                raise InvalidAuth("Login failed due to wrong credentials")

            self._authenticated = True

    async def logout(self) -> None:
        """Logout method."""
        if self._authenticated:
            resp = await self.session.post("/logout.cgi", ssl=self.ssl)

            if not resp.status == 200:
                raise BadResponse(f"Bad HTTP status code {resp.status}")

            self._authenticated = False

    async def authenticate(self) -> bool:
        """Athentication method."""
        await self.login()
        return self._authenticated

    @property
    async def config(self) -> str:
        """Configuration retrieval."""
        await self.login()

        resp = await self.session.get("/cfg.cgi", ssl=self.ssl)

        if not resp.status == 200:
            raise BadResponse(f"Bad HTTP status code {resp.status}")

        return await resp.text()

    async def update(self) -> None:
        """Update method for sensor data."""
        await self.login()

        if self._data is None or (time.time() - self._time) > self.cache_time:
            resp = await self.session.get("/sensors", ssl=self.ssl)

            if not resp.status == 200:
                raise BadResponse(f"Bad HTTP status code {resp.status}")

            self._time = time.time()
            self._data = (await resp.json())["sensors"]

    @property
    async def data(self) -> list:
        """Accessor for sensor data."""
        await self.update()
        return self._data

    @property
    async def cached_data(self) -> list:
        """Cached accessor for sensor data."""
        if self._data is None:
            return await self.data
        else:
            return self._data

    @property
    async def ports(self) -> int:
        """Number of available ports for this device."""
        data = await self.cached_data
        return len(data)

    @property
    async def model(self) -> str:
        """Model of this device."""
        ports = await self.ports
        if ports == 1:
            return "mPower mini"
        elif ports == 3:
            return "mPower"
        elif ports == 6 or ports == 8:
            return "mPower PRO"
        else:
            return "Unknown"

    @property
    async def description(self) -> str:
        """Model of this device."""
        ports = await self.ports
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

    async def get(self, port: int) -> dict:
        """Get data for individual ports."""
        data = await self.data
        return data[port - 1]

    async def set(self, port: int, output: bool) -> None:
        """Set output for individual ports."""
        if port < 1:
            raise ValueError(f"Port number {port} is too small")

        if port > await self.ports:
            raise ValueError("Port number {port} is too large")

        resp = await self.session.post(
            f"/sensors/{port}", data={"output": int(output)}, ssl=self.ssl
        )

        if not resp.status == 200:
            raise BadResponse(f"Bad HTTP status code {resp.status}")

    async def toggle(self, port: int) -> None:
        """Toggle output for individual ports."""
        port_data = await self.get(port)
        output = not bool(port_data["output"])
        await self.set(port=port, output=output)
