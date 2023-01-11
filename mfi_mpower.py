import aiohttp
from aiohttp import ClientSession
import ssl
import time


class mFimPowerDevice:
    """Async API for Ubiquiti mFi mPower devices as explained here: https://community.ui.com/questions/mPower-mFi-Switch-and-mFi-In-Wall-Outlet-HTTP-API/824c1c63-b7e6-44ed-b19a-f1d68cd07269"""


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
        if session is None:
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
            # Ubiquiti mFi mPower Devices use ancient OpenSSL (1.0.0g 18 Jan 2012)
            self.ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.ssl.set_ciphers("AES256-SHA:AES128-SHA")
            self.ssl.load_default_certs()
            self.ssl.verify_mode = ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE
        else:
            self.ssl = False

        self.cache_time = cache_time

    @property
    def url(self) -> str:
        """Device URL"""
        if self.ssl:
            return f"https://{self.host}"
        else:
            return f"http://{self.host}"

    async def login(self) -> None:
        """Login method"""

        if self._session:
            self.session = ClientSession()

        # Initial get request is required (cookie)
        await self.session.get(
            self.url,
            ssl=self.ssl
        )

        response = await self.session.post(
            f"{self.url}/login.cgi",
            data={
                "username": self.username,
                "password": self.password
            },
            ssl=self.ssl
        )

        if not response.status == 200:
            raise aiohttp.ClientError(f"Login failed with status {response.status}")

        # Successful login will *not* redirect back to /login.cgi
        if str(response.url).endswith("login.cgi"):
            raise aiohttp.ClientError("Login failed due to wrong credentials")

        self._authenticated = True

    async def logout(self) -> None:
        """Logout method"""
        response = await self.session.post(
            f"{self.url}/logout.cgi",
            ssl=self.ssl
        )

        if not response.status == 200:
            raise aiohttp.ClientError(f"Logout failed with status {response.status}")

        self._authenticated = False

        if self._session:
            await self.session.close()
            self.session = None

    async def config(self) -> str:
        """Configuration retrieval"""
        if not self._authenticated:
            await self.login()
        
        response = await self.session.get(
            f"{self.url}/cfg.cgi",
            ssl=self.ssl
        )

        if not response.status == 200:
            raise aiohttp.ClientError(f"Config retrieval failed with status {response.status}")

        return await response.text()

    async def update(self) -> None:
        """Update method for sensor data"""
        if not self._authenticated:
            await self.login()

        if self._data is None or (time.time() - self._time) > self.cache_time:
        
            response = await self.session.get(
                f"{self.url}/sensors",
                ssl=self.ssl
            )

            if not response.status == 200:
                raise aiohttp.ClientError(f"Update failed with status {response.status}")

            self._time = time.time()
            self._data = (await response.json())["sensors"]

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
        
        response = await self.session.put(
            f"{self.url}/sensors/{port}",
            data={"output": int(output)},
            ssl=self.ssl
        )

        if not response.status == 200:
            raise aiohttp.ClientError(f"Setting failed with status {response.status}")

    async def toggle(self, port: int) -> None:
        """Toggle output for individual ports"""
        port_data = await self.get(port)
        output = not bool(port_data["output"])
        await self.set(port=port, output=output)
