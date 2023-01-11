"""Ubiquiti mFi MPower board"""
from __future__ import annotations

import asyncssh

from . import device  # pylint: disable=unused-import
from .exceptions import MPowerAPIDataError
from .exceptions import (
    MPowerSSHConnError,
    MPowerSSHAuthError,
    MPowerSSHReadError,
    MPowerSSHDataError,
)


class MPowerBoard:
    """mFi mPower board representation."""

    # NOTE: Ubiquiti mFi mPower Devices with firmware 2.1.11 use Dropbear SSH 0.51 (27 Mar 2008).
    _ssh: dict = {
        "kex_algs": "diffie-hellman-group1-sha1",
        "encryption_algs": "aes128-cbc",
        # https://github.com/ronf/asyncssh/issues/263
        "server_host_key_algs": "ssh-rsa",
        # https://github.com/ronf/asyncssh/issues/132
        "known_hosts": None,
    }

    def __init__(
        self,
        device: device.MPowerDevice,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Initialize the board."""
        self._device = device
        self._data = {}

    def __str__(self):
        """Represent this board as string."""
        if self._data:
            keys = [
                "name",
                "sysid",
                "cpurevision",
                "revision",
                "hwaddr",
                "eu_model",
                "model",
                "ports",
            ]
        else:
            keys = ["host"]
        vals = ", ".join([f"{k}={getattr(self, k)}" for k in keys])
        return f"{__class__.__name__}({vals})"

    @property
    def host(self) -> str:
        """Return the board device host."""
        return self._device.host

    @property
    def name(self) -> str:
        """Return the board name."""
        try:
            return self.hostname
        except Exception:  # pylint: disable=broad-except
            return self.host

    async def update(self) -> None:
        """Update board data."""
        if not self._data:
            try:
                async with asyncssh.connect(
                    host=self.host,
                    username=self._device.username,
                    password=self._device.password,
                    **self._ssh,
                ) as conn:
                    # Read host name
                    result = await conn.run("cat /proc/sys/kernel/hostname")
                    status = result.exit_status
                    if status == 0:
                        try:
                            assert isinstance(result.stdout, str)
                            self._data["hostname"] = result.stdout.rstrip()
                        except Exception as exc:
                            raise MPowerSSHDataError(
                                f"Host name from device {self.host} is not valid: {exc}"
                            ) from exc
                    else:
                        raise MPowerSSHReadError(
                            f"Host name from device {self.host} could not be read: {status}"
                        )

                    # Read board data
                    result = await conn.run("cat /var/etc/board.info")
                    status = result.exit_status
                    if status == 0:
                        try:
                            assert isinstance(result.stdout, str)
                            for line in result.stdout.splitlines():
                                key_value = line.split("=")
                                if len(key_value) == 2:
                                    key, value = key_value
                                    self._data[key] = value
                        except Exception as exc:
                            raise MPowerSSHDataError(
                                f"Board data from device {self.host} is not valid: {exc}"
                            ) from exc
                    else:
                        raise MPowerSSHReadError(
                            f"Board data from device {self.host} could not be read: {status}"
                        )
            except asyncssh.PermissionDenied as exc:
                raise MPowerSSHAuthError(
                    f"Login to device {self.host} failed due to wrong SSH credentials"
                ) from exc
            except (OSError, asyncssh.Error) as exc:
                raise MPowerSSHConnError(
                    f"Connection to device {self.host} failed: {type(exc).__name__}({exc})"
                ) from exc

    @property
    def updated(self) -> bool:
        """Return if the board data has already been updated."""
        return bool(self._data)

    @property
    def data(self) -> dict:
        """Return board data."""
        if not self._data:
            raise MPowerAPIDataError(
                f"Board data for device {self.host} must be updated first"
            )
        return self._data

    @property
    def hostname(self) -> str:
        """Return if the board name."""
        return self.data.get("hostname", "")

    @property
    def sysid(self) -> str:
        """Return if the board system id."""
        return self.data.get("board.sysid", "")

    @property
    def cpurevision(self) -> str:
        """Return if the board CPU revision."""
        return self.data.get("board.cpurevision", "")

    @property
    def revision(self) -> str:
        """Return if the board revision."""
        return self.data.get("board.revision", "")

    @property
    def hwaddr(self) -> str:
        """Return if the board hardware address."""
        return self.data.get("board.hwaddr", "")

    @property
    def eu_model(self) -> bool | None:
        """Return whether this device is a EU model with type F sockets."""
        shortname = self.data.get("board.shortname", "")
        if len(shortname) > 2 and shortname.endswith("E"):
            return True
        elif len(shortname) > 1:
            return False
        else:
            return None

    @property
    def model(self) -> str:
        """Return if the board model."""
        name = self.data.get("board.name", "")
        eu_tag = " (EU)" if self.eu_model else ""
        if name:
            return name + eu_tag
        return ""

    @property
    def ports(self) -> int | None:
        """Return the number of available ports for the board device."""
        shortname = self.data.get("board.shortname", "")
        if len(shortname) > 1:
            return int(shortname[1])
        else:
            return None
