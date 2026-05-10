"""MCP stdio server entry point for KiPilot."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import KiCadIpcConfig
from .ipc_client import KiCadIpcClient

mcp = FastMCP("kipilot-mcp")

logger = logging.getLogger(__name__)
_LOGGING_CONFIGURED = False


def _configure_logging(config: KiCadIpcConfig) -> None:
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return

    package_logger = logging.getLogger("kipilot_mcp")
    package_logger.handlers.clear()
    package_logger.setLevel(getattr(logging, config.log_level, logging.INFO))
    package_logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    package_logger.addHandler(stderr_handler)

    if config.log_file:
        log_path = Path(config.log_file)
        if str(log_path.parent) not in {"", "."}:
            log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        package_logger.addHandler(file_handler)

    _LOGGING_CONFIGURED = True
    logger.info(
        "Logging configured. level=%s file=%s",
        config.log_level,
        config.log_file,
    )


def _build_client() -> KiCadIpcClient:
    config = KiCadIpcConfig.from_env()
    _configure_logging(config)
    return KiCadIpcClient(config)


def _summarize_for_log(value: Any, *, limit: int = 300) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


async def _run_client_tool(
    tool_name: str,
    method_name: str,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    client = _build_client()
    method = getattr(client, method_name)
    start_time = time.perf_counter()

    logger.info(
        "Tool start. name=%s method=%s args=%s kwargs=%s",
        tool_name,
        method_name,
        _summarize_for_log(args),
        _summarize_for_log(kwargs),
    )

    try:
        result = await method(*args, **kwargs)
    except Exception:
        logger.exception(
            "Tool raised an unexpected exception. name=%s method=%s",
            tool_name,
            method_name,
        )
        raise

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    if result.get("ok"):
        logger.info(
            "Tool finish. name=%s method=%s ok=true duration_ms=%s",
            tool_name,
            method_name,
            duration_ms,
        )
    else:
        logger.warning(
            "Tool finish. name=%s method=%s ok=false duration_ms=%s message=%s error=%s",
            tool_name,
            method_name,
            duration_ms,
            result.get("message"),
            result.get("error"),
        )

    return result


@mcp.tool()
async def ping_kicad() -> dict[str, Any]:
    """Check whether a user-running KiCad 10 PCB IPC server is reachable."""

    return await _run_client_tool("ping_kicad", "check_connection")


@mcp.tool()
async def get_kicad_version() -> dict[str, Any]:
    """Return KiCad and IPC API version information from the running GUI instance."""

    return await _run_client_tool("get_kicad_version", "check_connection")


@mcp.tool()
async def kicad_get_board_summary() -> dict[str, Any]:
    """Return high-level counts and metadata for the currently open PCB."""

    return await _run_client_tool("kicad_get_board_summary", "get_board_summary")


@mcp.tool()
async def kicad_list_open_documents(document_types: list[int] | None = None) -> dict[str, Any]:
    """Return the active board/project documents or query explicit document types."""

    return await _run_client_tool(
        "kicad_list_open_documents",
        "list_open_documents",
        document_types,
    )


@mcp.tool()
async def kicad_get_board_outline() -> dict[str, Any]:
    """Return Edge.Cuts-derived board outline shapes for the current PCB."""

    return await _run_client_tool("kicad_get_board_outline", "get_board_outline")


@mcp.tool()
async def kicad_get_stackup() -> dict[str, Any]:
    """Return layer stackup information for the current PCB."""

    return await _run_client_tool("kicad_get_stackup", "get_stackup")


@mcp.tool()
async def kicad_get_footprints(limit: int = 200) -> dict[str, Any]:
    """Return placed footprint references and positions from the current PCB."""

    return await _run_client_tool("kicad_get_footprints", "get_footprints", limit)


@mcp.tool()
async def kicad_find_footprints(
    reference: str | None = None,
    footprint_id: str | None = None,
    text_query: str | None = None,
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Find footprints by reference, ID, text query, layer, or area."""

    return await _run_client_tool(
        "kicad_find_footprints",
        "find_footprints",
        reference,
        footprint_id,
        text_query,
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_get_nets(limit: int = 200) -> dict[str, Any]:
    """Return net names from the current PCB."""

    return await _run_client_tool("kicad_get_nets", "get_nets", limit)


@mcp.tool()
async def kicad_get_items_by_net(
    net_name: str,
    item_types: list[int] | None = None,
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return board items associated with a named net, with optional layer and area filters."""

    return await _run_client_tool(
        "kicad_get_items_by_net",
        "get_items_by_net",
        net_name,
        item_types,
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_get_tracks(limit: int = 200) -> dict[str, Any]:
    """Return tracks from the current PCB."""

    return await _run_client_tool("kicad_get_tracks", "get_tracks", limit)


@mcp.tool()
async def kicad_get_vias(limit: int = 200) -> dict[str, Any]:
    """Return vias from the current PCB."""

    return await _run_client_tool("kicad_get_vias", "get_vias", limit)


@mcp.tool()
async def kicad_get_zones(limit: int = 200) -> dict[str, Any]:
    """Return zones from the current PCB."""

    return await _run_client_tool("kicad_get_zones", "get_zones", limit)


@mcp.tool()
async def kicad_get_board_text(
    text_id: str | None = None,
    text_query: str | None = None,
    layer: int | str | None = None,
    exact: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Return standalone board text items, with optional ID/text/layer filters."""

    return await _run_client_tool(
        "kicad_get_board_text",
        "get_board_text",
        text_id,
        text_query,
        layer,
        exact,
        limit,
    )


@mcp.tool()
async def kicad_get_pads(
    net_name: str | None = None,
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return board pads, with optional net, layer, and area filters."""

    return await _run_client_tool(
        "kicad_get_pads",
        "get_pads",
        net_name,
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_get_graphics(
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return generic board graphics, with optional layer and area filters."""

    return await _run_client_tool(
        "kicad_get_graphics",
        "get_graphics",
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_get_project_text_variables() -> dict[str, Any]:
    """Return text variables from the active project behind the current PCB."""

    return await _run_client_tool(
        "kicad_get_project_text_variables",
        "get_project_text_variables",
    )


@mcp.tool()
async def kicad_expand_project_text_variables(text: str) -> dict[str, Any]:
    """Expand project text variables inside one text fragment."""

    return await _run_client_tool(
        "kicad_expand_project_text_variables",
        "expand_project_text_variables",
        text,
    )


@mcp.tool()
async def kicad_get_project_net_classes() -> dict[str, Any]:
    """Return project net classes from the active board project."""

    return await _run_client_tool(
        "kicad_get_project_net_classes",
        "get_project_net_classes",
    )


@mcp.tool()
async def kicad_get_board_origins() -> dict[str, Any]:
    """Return the current grid and drill/place origins for the board."""

    return await _run_client_tool("kicad_get_board_origins", "get_board_origins")


@mcp.tool()
async def kicad_get_title_block() -> dict[str, Any]:
    """Return the current board title block metadata."""

    return await _run_client_tool("kicad_get_title_block", "get_title_block")


@mcp.tool()
async def kicad_get_items_by_netclass(
    netclass_name: str,
    item_types: list[int] | None = None,
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return board items associated with a named net class."""

    return await _run_client_tool(
        "kicad_get_items_by_netclass",
        "get_items_by_netclass",
        netclass_name,
        item_types,
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_get_netclass_for_nets(net_names: list[str]) -> dict[str, Any]:
    """Return the effective net class for one or more named nets."""

    return await _run_client_tool(
        "kicad_get_netclass_for_nets",
        "get_netclass_for_nets",
        net_names,
    )


@mcp.tool()
async def kicad_get_connected_items(
    item_id: str,
    item_types: list[int] | None = None,
    layer: int | str | None = None,
    area: dict[str, float] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return copper-connected items for one source board item."""

    return await _run_client_tool(
        "kicad_get_connected_items",
        "get_connected_items",
        item_id,
        item_types,
        layer,
        area,
        limit,
    )


@mcp.tool()
async def kicad_set_visible_layers(
    layers: list[int | str],
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Set the visible board layers, optionally as a dry run."""

    return await _run_client_tool(
        "kicad_set_visible_layers",
        "set_visible_layers",
        layers,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_set_active_layer(
    layer: int | str,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Set the active board layer, optionally as a dry run."""

    return await _run_client_tool(
        "kicad_set_active_layer",
        "set_active_layer",
        layer,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_set_enabled_layers(
    non_copper_layers: list[int | str],
    dry_run: bool = False,
    commit_message: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Set enabled non-copper board layers, guarded by force for live changes."""

    return await _run_client_tool(
        "kicad_set_enabled_layers",
        "set_enabled_layers",
        non_copper_layers,
        dry_run=dry_run,
        commit_message=commit_message,
        force=force,
    )


@mcp.tool()
async def kicad_revert_board(dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    """Revert the board to the last saved state, guarded by force and mutation gating."""

    return await _run_client_tool(
        "kicad_revert_board",
        "revert_board",
        dry_run=dry_run,
        force=force,
    )


@mcp.tool()
async def kicad_move_footprint(
    x_mm: float,
    y_mm: float,
    reference: str | None = None,
    footprint_id: str | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Move a footprint to an absolute board position, with optional dry run."""

    return await _run_client_tool(
        "kicad_move_footprint",
        "move_footprint",
        reference=reference,
        footprint_id=footprint_id,
        x_mm=x_mm,
        y_mm=y_mm,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_rotate_footprint(
    orientation_degrees: float,
    reference: str | None = None,
    footprint_id: str | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Set a footprint orientation in degrees, with optional dry run."""

    return await _run_client_tool(
        "kicad_rotate_footprint",
        "rotate_footprint",
        reference=reference,
        footprint_id=footprint_id,
        orientation_degrees=orientation_degrees,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_set_board_origin(
    origin_type: int | str,
    x_mm: float,
    y_mm: float,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Set the grid or drill/place board origin, with optional dry run."""

    return await _run_client_tool(
        "kicad_set_board_origin",
        "set_board_origin",
        origin_type=origin_type,
        x_mm=x_mm,
        y_mm=y_mm,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_set_title_block(
    title: str | None = None,
    revision: str | None = None,
    date: str | None = None,
    company: str | None = None,
    comments: dict[str, str] | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update board title block fields, with optional dry run."""

    return await _run_client_tool(
        "kicad_set_title_block",
        "set_title_block",
        title=title,
        revision=revision,
        date=date,
        company=company,
        comments=comments,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_update_board_text(
    text_id: str,
    new_text: str,
    expected_current_text: str | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update a board text or board text box value by item ID."""

    return await _run_client_tool(
        "kicad_update_board_text",
        "update_board_text",
        text_id=text_id,
        new_text=new_text,
        expected_current_text=expected_current_text,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_create_track_segments(
    points: list[dict[str, float]],
    layer: int | str,
    width_mm: float,
    net_name: str | None = None,
    locked: bool = False,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Create straight track segments from a polyline of board-space points."""

    return await _run_client_tool(
        "kicad_create_track_segments",
        "create_track_segments",
        points=points,
        layer=layer,
        width_mm=width_mm,
        net_name=net_name,
        locked=locked,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_create_via(
    x_mm: float,
    y_mm: float,
    diameter_mm: float,
    drill_diameter_mm: float,
    net_name: str | None = None,
    via_type: int | str = 1,
    locked: bool = False,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Create a via at an absolute board position."""

    return await _run_client_tool(
        "kicad_create_via",
        "create_via",
        x_mm=x_mm,
        y_mm=y_mm,
        diameter_mm=diameter_mm,
        drill_diameter_mm=drill_diameter_mm,
        net_name=net_name,
        via_type=via_type,
        locked=locked,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_update_items(
    updates: list[dict[str, Any]],
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Apply whitelisted low-level updates to footprints, tracks, and zones."""

    return await _run_client_tool(
        "kicad_update_items",
        "update_items",
        updates=updates,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_update_track_geometry(
    track_id: str,
    start_x_mm: float | None = None,
    start_y_mm: float | None = None,
    end_x_mm: float | None = None,
    end_y_mm: float | None = None,
    width_mm: float | None = None,
    layer: int | str | None = None,
    net_name: str | None = None,
    locked: bool | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update a straight track's endpoints or metadata fields."""

    return await _run_client_tool(
        "kicad_update_track_geometry",
        "update_track_geometry",
        track_id=track_id,
        start_x_mm=start_x_mm,
        start_y_mm=start_y_mm,
        end_x_mm=end_x_mm,
        end_y_mm=end_y_mm,
        width_mm=width_mm,
        layer=layer,
        net_name=net_name,
        locked=locked,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_update_zone_outline(
    zone_id: str,
    outline_points: list[dict[str, float]],
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Replace a zone's outer polygon with a new point list."""

    return await _run_client_tool(
        "kicad_update_zone_outline",
        "update_zone_outline",
        zone_id=zone_id,
        outline_points=outline_points,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_delete_items(
    item_ids: list[str],
    dry_run: bool = False,
    commit_message: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Delete board items by KiCad item ID, guarded by force and mutation gating."""

    return await _run_client_tool(
        "kicad_delete_items",
        "delete_items",
        item_ids=item_ids,
        dry_run=dry_run,
        commit_message=commit_message,
        force=force,
    )


@mcp.tool()
async def kicad_refill_zones(
    zone_ids: list[str] | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Refill all zones, or only the supplied zone IDs, on the current board."""

    return await _run_client_tool(
        "kicad_refill_zones",
        "refill_zones",
        zone_ids=zone_ids,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_save_board(dry_run: bool = False) -> dict[str, Any]:
    """Save the current board file to disk, with optional dry run."""

    return await _run_client_tool("kicad_save_board", "save_board", dry_run=dry_run)


def main() -> None:
    """Run the MCP server over stdio."""

    config = KiCadIpcConfig.from_env()
    _configure_logging(config)
    logger.info(
        "Starting KiPilot MCP server. transport=stdio client_name=%s timeout_ms=%s",
        config.client_name,
        config.timeout_ms,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
