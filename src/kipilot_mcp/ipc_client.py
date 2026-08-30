"""Async-friendly wrapper around KiCad's official Python IPC bindings."""

from __future__ import annotations

from .ipc_client_core import ApiError, KiCadIpcClientCore
from .ipc_client_pcb import KiCadPcbClientMixin
from .ipc_client_sch import KiCadSchematicClientMixin


class KiCadIpcClient(KiCadPcbClientMixin, KiCadSchematicClientMixin, KiCadIpcClientCore):
    """Connect to a user-running KiCad instance through the IPC API."""

    pass


__all__ = ["ApiError", "KiCadIpcClient"]
