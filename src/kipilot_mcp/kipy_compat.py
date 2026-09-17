"""Helpers for tolerating different kicad-python (kipy) binding versions.

KiPilot MCP supports a range of kipy releases. Older releases can be missing whole
modules (for example ``kipy.schematic_types`` on very old versions) or individual
names inside an existing module (for example ``kipy.common_types.PathType`` or
``kipy.common_types.EmbeddedFile``). Both cases raise ``ImportError`` at import
time, which must never prevent the MCP server from starting: tools that need a
missing binding report an explicit capability error instead.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def optional_import(module_name: str, attribute: str | None = None) -> Any:
    """Return ``module_name`` (or ``module_name.attribute``) when the binding provides it.

    Returns ``None`` when the module, the attribute, or a dotted submodule is not
    available in the installed kicad-python version. Any import-time failure is
    treated as "binding not available" and only logged at debug level.
    """

    target = f"{module_name}.{attribute}" if attribute else module_name

    try:
        module = importlib.import_module(module_name)
        if attribute is None:
            return module

        value = getattr(module, attribute, None)
        if value is not None:
            return value

        # The attribute may also be a submodule (for example ``project_settings_pb2``).
        return importlib.import_module(target)
    except Exception as exc:  # noqa: BLE001 - optional binding, never fatal
        logger.debug("Optional kicad-python binding %s is unavailable: %s", target, exc)
        return None


def log_binding_gaps(scope: str, bindings: dict[str, Any]) -> list[str]:
    """Log which optional kicad-python bindings are missing and return their names."""

    missing = sorted(name for name, value in bindings.items() if value is None)
    if missing:
        logger.info(
            "%s: %d optional kicad-python binding(s) are unavailable with the installed "
            "kicad-python version: %s. Tools that require them report a capability error.",
            scope,
            len(missing),
            ", ".join(missing),
        )
    return missing
