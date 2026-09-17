"""Tests for KiCad IPC endpoint resolution (including Windows named pipes)."""

from __future__ import annotations

from kipilot_mcp.ipc_endpoint import (
    discover_socket_urls,
    normalize_socket_url,
    resolve_socket_url,
)

LONG_PIPE = r"C:\Users\Szalontai Béla\AppData\Local\Temp\kicad\api.sock"
SHORT_PIPE = r"C:\Users\SZALON~2\AppData\Local\Temp\kicad\api.sock"
NUMBERED_PIPE = r"C:\msys64\tmp\kicad\api-4242.sock"
UNRELATED_PIPES = [
    r"mcp-63b13f40-bf42-4b10-a0ec-acf5df675cf7.sock",
    r"vscode-git-2880f11800-sock",
    r"Winsock2\CatalogChangeListener-1f8-0",
]


def pipe_lister(names: list[str]):
    def list_pipes() -> list[str]:
        return names

    return list_pipes


def test_normalize_socket_url_adds_ipc_scheme() -> None:
    assert normalize_socket_url(SHORT_PIPE) == f"ipc://{SHORT_PIPE}"
    assert normalize_socket_url("ipc:///tmp/kicad/api.sock") == "ipc:///tmp/kicad/api.sock"
    assert normalize_socket_url("  ") == ""


def test_configured_path_wins_over_discovery() -> None:
    resolved = resolve_socket_url(
        SHORT_PIPE,
        pipe_lister=pipe_lister([LONG_PIPE]),
        system_name="Windows",
    )
    assert resolved == f"ipc://{SHORT_PIPE}"


def test_discovery_uses_short_form_pipe_when_no_path_is_configured() -> None:
    resolved = resolve_socket_url(
        None,
        pipe_lister=pipe_lister([*UNRELATED_PIPES, SHORT_PIPE]),
        system_name="Windows",
    )
    assert resolved == f"ipc://{SHORT_PIPE}"


def test_discovery_ignores_unrelated_pipes() -> None:
    resolved = resolve_socket_url(
        None,
        pipe_lister=pipe_lister(UNRELATED_PIPES),
        system_name="Windows",
    )
    assert resolved is None


def test_discovery_is_skipped_on_non_windows() -> None:
    discovered = discover_socket_urls(
        pipe_lister=pipe_lister([SHORT_PIPE]),
        system_name="Linux",
    )
    assert discovered == []


def test_discovery_prefers_main_socket_over_numbered_sockets() -> None:
    discovered = discover_socket_urls(
        pipe_lister=pipe_lister([NUMBERED_PIPE, LONG_PIPE]),
        system_name="Windows",
    )
    assert discovered[0] == f"ipc://{LONG_PIPE}"
    assert f"ipc://{NUMBERED_PIPE}" in discovered


def test_discovery_accepts_numbered_sockets() -> None:
    resolved = resolve_socket_url(
        None,
        pipe_lister=pipe_lister([NUMBERED_PIPE]),
        system_name="Windows",
    )
    assert resolved == f"ipc://{NUMBERED_PIPE}"


def test_discovery_handles_forward_slashes() -> None:
    resolved = resolve_socket_url(
        None,
        pipe_lister=pipe_lister(["C:/Users/SZALON~2/AppData/Local/Temp/kicad/api.sock"]),
        system_name="Windows",
    )
    assert resolved == f"ipc://{SHORT_PIPE}"


def test_discovery_survives_pipe_listing_failures() -> None:
    def broken_lister():
        raise OSError("pipe namespace unavailable")

    assert resolve_socket_url(None, pipe_lister=broken_lister, system_name="Windows") is None
