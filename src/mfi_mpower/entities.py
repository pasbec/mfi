"""Ubiquiti mFi MPower entities"""
from __future__ import annotations

from . import device
from .exceptions import InvalidData


class MPowerEntity:
    """mFi mPower entity baseclass."""

    _device: device.MPowerDevice
    _port: int
    _data: dict

    def __init__(self, device: device.MPowerDevice, port: int) -> None:
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
    def device(self) -> device.MPowerDevice:
        """Return the entity device."""
        return self._device

    @property
    def data(self) -> dict:
        """Return all entity data."""
        return self._data

    @data.setter
    def data(self, data: dict) -> None:
        """Set entity data."""
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
