"""This is the mFi mPower module."""
from __future__ import annotations

from .board import MPowerBoard
from .device import MPowerDevice
from .entities import MPowerEntity, MPowerSensor, MPowerSwitch
from .exceptions import *

__version__ = "1.2.0"
