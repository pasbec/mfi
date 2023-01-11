"""Ubiquiti mFi MPower exceptions"""


class MPowerError(Exception):
    """General mFi MPower error."""


class MPowerConnError(Exception):
    """General mFi MPower connection error."""


class MPowerAuthError(Exception):
    """General mFi MPower authentication error."""


class MPowerReadError(Exception):
    """General mFi MPower data read error."""


class MPowerDataError(Exception):
    """General mFi MPower data validity error."""


class MPowerSSHError(MPowerError):
    """Error related to board info extraction via SSH."""


class MPowerSSHConnError(MPowerSSHError, MPowerConnError):
    """Error related to SSH connections."""


class MPowerSSHAuthError(MPowerSSHError, MPowerAuthError):
    """Error related to SSH data authentication."""


class MPowerSSHReadError(MPowerSSHError, MPowerReadError):
    """Error related to SSH data reading."""


class MPowerSSHDataError(MPowerSSHError, MPowerDataError):
    """Error related to SSH data validity."""


class MPowerAPIError(MPowerError):
    """Error related to the "REST" API from Ubiquiti."""


class MPowerAPIConnError(MPowerAPIError, MPowerConnError):
    """Error related to "REST" API connections."""


class MPowerAPIAuthError(MPowerAPIError, MPowerAuthError):
    """Error related to "REST" API authentication."""


class MPowerAPIReadError(MPowerAPIError, MPowerReadError):
    """Error related to "REST" API data reading."""


class MPowerAPIDataError(MPowerAPIError, MPowerDataError):
    """Error related to "REST" API data validity."""
