"""
WattBox API Exceptions

Custom exception classes for the WattBox API client.
"""


class WattBoxError(Exception):
    """Base exception for all WattBox API errors."""
    pass


class WattBoxConnectionError(WattBoxError):
    """Raised when connection to WattBox device fails."""
    pass


class WattBoxAuthenticationError(WattBoxError):
    """Raised when authentication with WattBox device fails."""
    pass


class WattBoxCommandError(WattBoxError):
    """Raised when a command is rejected by the WattBox device."""
    pass


class WattBoxTimeoutError(WattBoxError):
    """Raised when a command times out."""
    pass


class WattBoxResponseError(WattBoxError):
    """Raised when an unexpected response is received."""
    pass
