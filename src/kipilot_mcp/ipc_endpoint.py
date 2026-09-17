"""Resolve the KiCad IPC endpoint.

KiCad exposes its API server on ``<temp>/kicad/api.sock``.  On Windows that path
becomes a named pipe, and the pipe name is not always the long form of the temp
path: when the user profile contains non-ASCII characters, Windows also creates
an 8.3 short name (``C:\\Users\\SZALON~2\\...``) and KiCad binds the pipe with the
short form.  A client that dials the long form then gets "connection refused"
even though KiCad is running and the API server is enabled.

The endpoint is therefore resolved in this order:

1. an explicitly configured socket path (``KICAD_API_SOCKET`` or the client config);
2. an already existing KiCad pipe discovered in ``\\\\.\\pipe\\`` (Windows only),
   which also covers the case where KiCad runs in a different shell/session than
   the MCP server and therefore uses a different temp directory;
3. ``None``, which lets ``kicad-python`` fall back to its own platform default.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import tempfile
from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)

WINDOWS_PIPE_ROOT = "\\\\.\\pipe\\"
KICAD_SOCKET_SUFFIX = re.compile(r"kicad[\\/]api(?:-\d+)?\.sock$", re.IGNORECASE)
KICAD_MAIN_SOCKET_SUFFIX = re.compile(r"kicad[\\/]api\.sock$", re.IGNORECASE)


def normalize_socket_url(value: str) -> str:
    """Return ``value`` as an ``ipc://`` endpoint URL."""

    stripped = value.strip()
    if not stripped:
        return stripped

    if "://" in stripped:
        return stripped

    return f"ipc://{stripped}"


def default_socket_url() -> str:
    """Return the default endpoint the ``kicad-python`` binding would dial."""

    if platform.system() == "Windows":
        return f"ipc://{tempfile.gettempdir()}\\kicad\\api.sock"

    return "ipc:///tmp/kicad/api.sock"


def list_windows_pipes() -> list[str]:
    """Return the names in the Windows named-pipe namespace."""

    try:
        return list(os.listdir(WINDOWS_PIPE_ROOT))
    except OSError:  # pragma: no cover - non-Windows or restricted environment
        return []


def _temp_directory_names() -> set[str]:
    """Return candidate spellings of the local temp directory (long and short form)."""

    names: set[str] = set()

    temp_dir = tempfile.gettempdir()
    names.add(temp_dir.replace("/", "\\").lower())

    short_name = _windows_short_path(temp_dir)
    if short_name:
        names.add(short_name.replace("/", "\\").lower())

    return names


def _windows_short_path(path: str) -> str | None:
    """Return the 8.3 short form of ``path`` on Windows, when one exists."""

    if platform.system() != "Windows":  # pragma: no cover - Windows-only helper
        return None

    try:
        import ctypes
        from ctypes import wintypes

        get_short_path_name = ctypes.windll.kernel32.GetShortPathNameW
        get_short_path_name.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_short_path_name.restype = wintypes.DWORD

        buffer = ctypes.create_unicode_buffer(len(path) + 1)
        written = get_short_path_name(path, buffer, len(buffer))
        if written == 0 or written > len(buffer):
            return None

        short_path = buffer.value
        if not short_path or short_path.lower() == path.lower():
            return None

        return short_path
    except Exception:  # noqa: BLE001 - best effort only
        return None


def discover_socket_urls(
    pipe_lister: Callable[[], Iterable[str]] | None = None,
    *,
    system_name: str | None = None,
) -> list[str]:
    """Return endpoints of running KiCad API servers, most likely first."""

    resolved_system = system_name or platform.system()
    if resolved_system != "Windows":
        return []

    lister = pipe_lister or list_windows_pipes
    try:
        pipe_names = list(lister())
    except Exception as exc:  # noqa: BLE001 - discovery must never fail hard
        logger.debug("Named-pipe discovery failed: %s", exc)
        return []

    local_directories = _temp_directory_names()

    def sort_key(name: str) -> tuple[int, int, str]:
        normalized = name.replace("/", "\\")
        directory = normalized.rsplit("\\", 1)[0].lower() if "\\" in normalized else ""
        is_main_socket = 1 if KICAD_MAIN_SOCKET_SUFFIX.search(normalized) else 0
        is_local = 1 if directory in local_directories else 0
        return (0 if is_main_socket else 1, 0 if is_local else 1, normalized.lower())

    matches = [
        name.replace("/", "\\")
        for name in pipe_names
        if KICAD_SOCKET_SUFFIX.search(name.replace("/", "\\"))
    ]

    return [f"ipc://{name}" for name in sorted(matches, key=sort_key)]


def resolve_socket_url(
    configured: str | None = None,
    *,
    pipe_lister: Callable[[], Iterable[str]] | None = None,
    system_name: str | None = None,
) -> str | None:
    """Return the endpoint KiPilot should dial, or ``None`` for the binding default."""

    if configured and configured.strip():
        return normalize_socket_url(configured)

    discovered = discover_socket_urls(pipe_lister=pipe_lister, system_name=system_name)
    if discovered:
        logger.debug("Using discovered KiCad IPC endpoint %s", discovered[0])
        return discovered[0]

    return None
