"""Runtime configuration for the KiPilot MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class KiCadIpcConfig:
    """Connection settings for KiCad's IPC server."""

    socket_path: str | None = None
    api_token: str | None = None
    client_name: str = "kipilot-mcp"
    timeout_ms: int = 60000
    enable_mutations: bool = False
    commit_message_prefix: str = "KiPilot MCP"
    log_level: str = "INFO"
    log_file: str | None = None

    @classmethod
    def from_env(cls) -> KiCadIpcConfig:
        return cls(
            socket_path=os.getenv("KICAD_API_SOCKET") or None,
            api_token=os.getenv("KICAD_API_TOKEN") or None,
            client_name=os.getenv("KIPILOT_KICAD_CLIENT_NAME", cls.client_name),
            timeout_ms=_read_int("KIPILOT_KICAD_TIMEOUT_MS", cls.timeout_ms),
            enable_mutations=_read_bool("KIPILOT_ENABLE_MUTATIONS", cls.enable_mutations),
            commit_message_prefix=os.getenv(
                "KIPILOT_COMMIT_MESSAGE_PREFIX",
                cls.commit_message_prefix,
            ),
            log_level=_read_log_level("KIPILOT_LOG_LEVEL", cls.log_level),
            log_file=os.getenv("KIPILOT_LOG_FILE") or None,
        )


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        msg = f"{name} must be an integer, got {raw_value!r}."
        raise ValueError(msg) from exc


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    msg = f"{name} must be a boolean-like value, got {raw_value!r}."
    raise ValueError(msg)


def _read_log_level(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().upper()
    if normalized in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        return normalized

    msg = f"{name} must be one of CRITICAL, ERROR, WARNING, INFO, or DEBUG, got {raw_value!r}."
    raise ValueError(msg)
