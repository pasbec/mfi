"""Ubiquiti mFi MPower exceptions"""


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidResponse(Exception):
    """Error to indicate we received an invalid http status."""


class InvalidData(Exception):
    """Error to indicate we received invalid device data."""