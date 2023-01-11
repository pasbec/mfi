"""Ubiquiti mFi MPower exceptions"""
from __future__ import annotations


class MPowerError(Exception):
    """General mFi MPower error."""


class MPowerSSHError(MPowerError):
    """Error related to board info extraction via SSH."""


class MPowerSSHConnError(MPowerSSHError):
    """Error related to SSH connections."""


class MPowerSSHAuthError(MPowerSSHError):
    """Error related to SSH data authentication."""


class MPowerSSHReadError(MPowerSSHError):
    """Error related to SSH data reading."""


class MPowerSSHDataError(MPowerSSHError):
    """Error related to SSH data validity."""


class MPowerAPIError(MPowerError):
    """Error related to the "REST" API from Ubiquiti."""


class MPowerAPIConnError(MPowerAPIError):
    """Error related to "REST" API connections."""


class MPowerAPIAuthError(MPowerAPIError):
    """Error related to "REST" API authentication."""


class MPowerAPIReadError(MPowerAPIError):
    """Error related to "REST" API data reading."""


class MPowerAPIDataError(MPowerAPIError):
    """Error related to "REST" API data validity."""
