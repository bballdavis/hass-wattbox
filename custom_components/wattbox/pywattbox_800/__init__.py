"""
SnapAV WattBox API Client Library v2.4

A Python client library for controlling SnapAV WattBox devices using the Integration Protocol v2.4.
Supports both Telnet (port 23) and SSH (port 22) connections.
"""

__version__ = "2.4.0"
__author__ = "WattBox Integration Team"

from .client import WattBoxClient
from .models import (
    WattBoxDevice,
    OutletInfo,
    PowerStatus,
    UPSStatus,
    SystemInfo,
)
from .exceptions import (
    WattBoxError,
    WattBoxConnectionError,
    WattBoxAuthenticationError,
    WattBoxCommandError,
    WattBoxTimeoutError,
)

__all__ = [
    "WattBoxClient",
    "WattBoxDevice", 
    "OutletInfo",
    "PowerStatus",
    "UPSStatus",
    "SystemInfo",
    "WattBoxError",
    "WattBoxConnectionError", 
    "WattBoxAuthenticationError",
    "WattBoxCommandError",
    "WattBoxTimeoutError",
]
