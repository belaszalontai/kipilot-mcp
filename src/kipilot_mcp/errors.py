"""Shared exceptions for KiCad IPC client operations."""

from __future__ import annotations


class KiCadBindingUnavailableError(RuntimeError):
    """Raised when the official kicad-python binding is unavailable."""


class KiCadCapabilityError(RuntimeError):
    """Raised when the connected KiCad version lacks a required capability."""


class KiCadLookupError(RuntimeError):
    """Raised when the requested object cannot be resolved on the board."""