import aiohttp
from aiohttp import ClientSession
import asyncio
import ssl
import time


class mFimPowerDevice:
    """
    Async API for Ubiquiti mFi mPower devices which are sadly EOL since 2015

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
    
    Some inspiration for this API came from another old mFi API:
      https://github.com/acedrew/ubnt-mfi-py
    """


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
        session: ClientSession = None
    ):
        """Initialize mFi mPower device object"""
        if session is None:
            self.session = ClientSession()
            self._session = True
        else:
            self.session = session
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
        else:
            self.ssl = False

        self.cache_time = cache_time
        
    def __del__(self):
        """
        Delete mFi mPower device object

        This closes the async connection if necessary as proposed here:
          https://stackoverflow.com/a/67577364/13613140
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.session.close())
            else:
                loop.run_until_complete(self.session.close())
        except Exception:
            pass

    @property
    def url(self) -> str:
        """Device URL"""
        if self.ssl:
            return f"https://{self.host}"
        else:
            return f"http://{self.host}"

    async def login(self) -> None:
        """Login method"""

        # NOTE: Initial get request sets cookie
        await self.session.get(
            self.url,
            ssl=self.ssl
        )

        resp = await self.session.post(
            f"{self.url}/login.cgi",
            data={
                "username": self.username,
                "password": self.password
            },
            ssl=self.ssl
        )

        if not resp.status == 200:
            raise aiohttp.ClientResponseError(f"Login failed with status {resp.status}")

        # NOTE: Successful login will *not* redirect back to /login.cgi
        if str(resp.url).endswith("login.cgi"):
            raise aiohttp.ClientError("Login failed due to wrong credentials")

        self._authenticated = True

    async def logout(self) -> None:
        """Logout method"""
        resp = await self.session.post(
            f"{self.url}/logout.cgi",
            ssl=self.ssl
        )

        if not resp.status == 200:
            raise aiohttp.ClientResponseError(f"Logout failed with status {resp.status}")

        self._authenticated = False

    async def config(self) -> str:
        """Configuration retrieval"""
        if not self._authenticated:
            await self.login()
        
        resp = await self.session.get(
            f"{self.url}/cfg.cgi",
            ssl=self.ssl
        )

        if not resp.status == 200:
            raise aiohttp.ClientResponseError(f"Config retrieval failed with status {resp.status}")

        return await resp.text()

    async def update(self) -> None:
        """Update method for sensor data"""
        if not self._authenticated:
            await self.login()

        if self._data is None or (time.time() - self._time) > self.cache_time:
            resp = await self.session.get(
                f"{self.url}/sensors",
                ssl=self.ssl
            )

            if not resp.status == 200:
                raise aiohttp.ClientResponseError(f"Update failed with status {resp.status}")

            self._time = time.time()
            self._data = (await resp.json())["sensors"]

    @property
    async def data(self) -> list:
        """Accessor for sensor data"""
        await self.update()
        return self._data

    @property
    async def cached_data(self) -> list:
        """Cached accessor for sensor data"""
        if self._data is None:
            return await self.data
        else:
            return self._data

    @property
    async def ports(self) -> int:
        """Number of available ports for this device"""
        data = await self.cached_data
        return len(data)

    async def get(self, port: int) -> dict:
        """Get data for individual ports"""
        data = await self.data
        return data[port - 1]

    async def set(self, port: int, output: bool) -> None:
        """Set output for individual ports"""
        if port < 1:
            raise ValueError(f"Port number {port} is too small")

        if port > await self.ports:
            raise ValueError("Port number {port} is too large")
        
        resp = await self.session.post(
            f"{self.url}/sensors/{port}",
            data={"output": int(output)},
            ssl=self.ssl
        )

        if not resp.status == 200:
            raise aiohttp.ClientResponseError(f"Setting failed with status {resp.status}")

    async def toggle(self, port: int) -> None:
        """Toggle output for individual ports"""
        port_data = await self.get(port)
        output = not bool(port_data["output"])
        await self.set(port=port, output=output)
