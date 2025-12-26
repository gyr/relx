"""
This module contains custom exceptions for the relx application.
"""


class RelxError(Exception):
    """Base class for all application-specific errors."""

    pass


class RelxUserCancelError(RelxError):
    """Raised when a user explicitly cancels an operation."""

    pass


class RelxResourceNotFoundError(RelxError):
    """Raised when a requested resource (user, package, etc.) is not found."""

    pass
