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
    """Check whether a user-running KiCad IPC endpoint is reachable."""

    return await _run_client_tool("ping_kicad", "check_connection")


@mcp.tool()
async def get_kicad_version() -> dict[str, Any]:
    """Return KiCad and IPC API version information when the active endpoint exposes it."""

    return await _run_client_tool("get_kicad_version", "get_version_info")


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
async def kicad_sch_get_hierarchy() -> dict[str, Any]:
    """Return the top-level schematic hierarchy tree for the current schematic."""

    return await _run_client_tool("kicad_sch_get_hierarchy", "get_schematic_hierarchy")


@mcp.tool()
async def kicad_sch_get_netlist(item_types: list[int] | None = None) -> dict[str, Any]:
    """Return the current schematic netlist, optionally filtered by item types."""

    return await _run_client_tool(
        "kicad_sch_get_netlist",
        "get_schematic_netlist",
        item_types,
    )


@mcp.tool()
async def kicad_sch_hit_test(
    item_id: str,
    x_mm: float,
    y_mm: float,
    tolerance_mm: float = 0.0,
) -> dict[str, Any]:
    """Run a hit test against one schematic item at a schematic-space position."""

    return await _run_client_tool(
        "kicad_sch_hit_test",
        "hit_test_schematic",
        item_id=item_id,
        x_mm=x_mm,
        y_mm=y_mm,
        tolerance_mm=tolerance_mm,
    )


@mcp.tool()
async def kicad_sch_get_page_settings() -> dict[str, Any]:
    """Return the current schematic page settings."""

    return await _run_client_tool(
        "kicad_sch_get_page_settings",
        "get_schematic_page_settings",
    )


@mcp.tool()
async def kicad_sch_set_page_settings(
    page_size: int | str | None = None,
    orientation: int | str | None = None,
    drawing_sheet: str | None = None,
    user_page_size_mm: dict[str, float] | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update one or more page settings fields on the current schematic."""

    return await _run_client_tool(
        "kicad_sch_set_page_settings",
        "set_schematic_page_settings",
        page_size=page_size,
        orientation=orientation,
        drawing_sheet=drawing_sheet,
        user_page_size_mm=user_page_size_mm,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_sch_get_title_block() -> dict[str, Any]:
    """Return the current schematic title block information."""

    return await _run_client_tool(
        "kicad_sch_get_title_block",
        "get_schematic_title_block",
    )


@mcp.tool()
async def kicad_sch_set_title_block(
    title: str | None = None,
    revision: str | None = None,
    date: str | None = None,
    company: str | None = None,
    comments: dict[str | int, str] | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update one or more title block fields on the current schematic."""

    return await _run_client_tool(
        "kicad_sch_set_title_block",
        "set_schematic_title_block",
        title=title,
        revision=revision,
        date=date,
        company=company,
        comments=comments,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_sch_export_svg(
    output_dir: str,
    plot_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export the current schematic to SVG files inside output_dir."""

    return await _run_client_tool(
        "kicad_sch_export_svg",
        "export_schematic_svg",
        output_dir=output_dir,
        plot_settings=plot_settings,
    )


@mcp.tool()
async def kicad_sch_export_dxf(
    output_dir: str,
    plot_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export the current schematic to DXF files inside output_dir."""

    return await _run_client_tool(
        "kicad_sch_export_dxf",
        "export_schematic_dxf",
        output_dir=output_dir,
        plot_settings=plot_settings,
    )


@mcp.tool()
async def kicad_sch_export_pdf(
    output_file: str,
    plot_settings: dict[str, Any] | None = None,
    property_popups: bool = False,
    hierarchical_links: bool = False,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """Export the current schematic to one PDF file using optional schematic plot settings."""

    return await _run_client_tool(
        "kicad_sch_export_pdf",
        "export_schematic_pdf",
        output_file=output_file,
        plot_settings=plot_settings,
        property_popups=property_popups,
        hierarchical_links=hierarchical_links,
        include_metadata=include_metadata,
    )


@mcp.tool()
async def kicad_sch_export_ps(
    output_dir: str,
    plot_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export the current schematic to PostScript files inside output_dir."""

    return await _run_client_tool(
        "kicad_sch_export_ps",
        "export_schematic_ps",
        output_dir=output_dir,
        plot_settings=plot_settings,
    )


@mcp.tool()
async def kicad_sch_export_netlist(
    output_file: str,
    netlist_format: int | str = 2,
    variant_name: str = "",
) -> dict[str, Any]:
    """Export the current schematic netlist to one output file."""

    return await _run_client_tool(
        "kicad_sch_export_netlist",
        "export_schematic_netlist",
        output_file=output_file,
        netlist_format=netlist_format,
        variant_name=variant_name,
    )


@mcp.tool()
async def kicad_sch_export_bom(
    output_file: str,
    format_settings: dict[str, Any] | None = None,
    field_settings: dict[str, Any] | None = None,
    exclude_dnp: bool = False,
    group_symbols: bool = False,
    variant_name: str = "",
) -> dict[str, Any]:
    """Export the current schematic BOM to one output file."""

    return await _run_client_tool(
        "kicad_sch_export_bom",
        "export_schematic_bom",
        output_file=output_file,
        format_settings=format_settings,
        field_settings=field_settings,
        exclude_dnp=exclude_dnp,
        group_symbols=group_symbols,
        variant_name=variant_name,
    )


@mcp.tool()
async def kicad_sch_get_selection(limit: int = 200) -> dict[str, Any]:
    """Return the current schematic selection."""

    return await _run_client_tool("kicad_sch_get_selection", "get_schematic_selection", limit)


@mcp.tool()
async def kicad_sch_add_to_selection(
    item_ids: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Add one or more schematic items to the current selection by their IDs."""

    return await _run_client_tool(
        "kicad_sch_add_to_selection",
        "add_to_schematic_selection",
        item_ids=item_ids,
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_sch_remove_from_selection(
    item_ids: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove one or more schematic items from the current selection by their IDs."""

    return await _run_client_tool(
        "kicad_sch_remove_from_selection",
        "remove_from_schematic_selection",
        item_ids=item_ids,
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_sch_clear_selection(dry_run: bool = False) -> dict[str, Any]:
    """Clear the current schematic selection."""

    return await _run_client_tool(
        "kicad_sch_clear_selection",
        "clear_schematic_selection",
        dry_run=dry_run,
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
async def kicad_get_board_layer_by_name(layer_name: str) -> dict[str, Any]:
    """Resolve a board layer id by its canonical name."""

    return await _run_client_tool(
        "kicad_get_board_layer_by_name",
        "get_board_layer_by_name",
        layer_name,
    )


@mcp.tool()
async def kicad_get_board_plot_settings() -> dict[str, Any]:
    """Return the board plot settings stored in the current PCB."""

    return await _run_client_tool("kicad_get_board_plot_settings", "get_board_plot_settings")


@mcp.tool()
async def kicad_set_board_plot_settings(
    plot_settings: dict[str, Any],
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Update the board plot settings stored in the current PCB."""

    return await _run_client_tool(
        "kicad_set_board_plot_settings",
        "set_board_plot_settings",
        plot_settings=plot_settings,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_get_footprints(limit: int = 200) -> dict[str, Any]:
    """Return placed footprints with instance data and compact child-graphics layer summaries."""

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
    """Find footprints by reference, ID, text query, layer, or area, including child-graphics summaries."""

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
    reference: str | None = None,
    footprint_id: str | None = None,
) -> dict[str, Any]:
    """Return board pads, with optional net, layer, and area filters."""

    return await _run_client_tool(
        "kicad_get_pads",
        "get_pads",
        net_name,
        layer,
        area,
        limit,
        reference,
        footprint_id,
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
async def kicad_get_dimensions(limit: int = 200) -> dict[str, Any]:
    """Return board dimensions from the current PCB."""

    return await _run_client_tool("kicad_get_dimensions", "get_dimensions", limit)


@mcp.tool()
async def kicad_get_groups(limit: int = 200) -> dict[str, Any]:
    """Return board groups from the current PCB."""

    return await _run_client_tool("kicad_get_groups", "get_groups", limit)


@mcp.tool()
async def kicad_get_reference_images(limit: int = 200) -> dict[str, Any]:
    """Return non-plotting reference images from the current PCB."""

    return await _run_client_tool(
        "kicad_get_reference_images",
        "get_reference_images",
        limit,
    )


@mcp.tool()
async def kicad_get_barcodes(limit: int = 200) -> dict[str, Any]:
    """Return barcode items from the current PCB."""

    return await _run_client_tool("kicad_get_barcodes", "get_barcodes", limit)


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
async def kicad_set_project_text_variables(
    variables: dict[str, str],
    merge_mode: str = "merge",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Update active project text variables, with merge or replace behavior."""

    return await _run_client_tool(
        "kicad_set_project_text_variables",
        "set_project_text_variables",
        variables=variables,
        merge_mode=merge_mode,
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_get_project_net_classes() -> dict[str, Any]:
    """Return project net classes from the active board project."""

    return await _run_client_tool(
        "kicad_get_project_net_classes",
        "get_project_net_classes",
    )


@mcp.tool()
async def kicad_get_selection(limit: int = 200) -> dict[str, Any]:
    """Return the current board selection."""

    return await _run_client_tool("kicad_get_selection", "get_selection", limit)


@mcp.tool()
async def kicad_get_graphics_defaults() -> dict[str, Any]:
    """Return default graphics settings for board layer classes."""

    return await _run_client_tool("kicad_get_graphics_defaults", "get_graphics_defaults")


@mcp.tool()
async def kicad_get_editor_appearance_settings() -> dict[str, Any]:
    """Return current board editor appearance settings."""

    return await _run_client_tool(
        "kicad_get_editor_appearance_settings",
        "get_editor_appearance_settings",
    )


@mcp.tool()
async def kicad_get_items(
    item_kinds: list[str] | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Return board items across one or more item kinds."""

    return await _run_client_tool(
        "kicad_get_items",
        "get_items",
        item_kinds=item_kinds,
        limit=limit,
    )


@mcp.tool()
async def kicad_get_items_by_id(item_ids: list[str], limit: int = 200) -> dict[str, Any]:
    """Return board items resolved by KiCad item IDs."""

    return await _run_client_tool(
        "kicad_get_items_by_id",
        "get_items_by_id",
        item_ids=item_ids,
        limit=limit,
    )


@mcp.tool()
async def kicad_hit_test(
    item_id: str,
    x_mm: float,
    y_mm: float,
    tolerance_mm: float = 0.0,
) -> dict[str, Any]:
    """Run a hit test against one board item at a board-space position."""

    return await _run_client_tool(
        "kicad_hit_test",
        "hit_test",
        item_id=item_id,
        x_mm=x_mm,
        y_mm=y_mm,
        tolerance_mm=tolerance_mm,
    )


@mcp.tool()
async def kicad_get_text_extents(text_item_id: str) -> dict[str, Any]:
    """Return the text extents box for one board text or text box item."""

    return await _run_client_tool(
        "kicad_get_text_extents",
        "get_text_extents",
        text_item_id=text_item_id,
    )


@mcp.tool()
async def kicad_get_text_as_shapes(text_item_ids: list[str]) -> dict[str, Any]:
    """Return polygonal shapes representing one or more board text items."""

    return await _run_client_tool(
        "kicad_get_text_as_shapes",
        "get_text_as_shapes",
        text_item_ids=text_item_ids,
    )


@mcp.tool()
async def kicad_check_padstack_presence_on_layers(
    item_ids: list[str],
    layers: list[int | str],
) -> dict[str, Any]:
    """Check whether padstack-bearing items have copper on the requested layers."""

    return await _run_client_tool(
        "kicad_check_padstack_presence_on_layers",
        "check_padstack_presence_on_layers",
        item_ids=item_ids,
        layers=layers,
    )


@mcp.tool()
async def kicad_get_pad_shapes_as_polygons(
    pad_ids: list[str],
    layer: int | str,
    limit: int = 200,
) -> dict[str, Any]:
    """Return polygonized pad outlines for one or more pads on one board layer."""

    return await _run_client_tool(
        "kicad_get_pad_shapes_as_polygons",
        "get_pad_shapes_as_polygons",
        pad_ids=pad_ids,
        layer=layer,
        limit=limit,
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
async def kicad_flip_footprint(
    reference: str | None = None,
    footprint_id: str | None = None,
    target_layer: int | str | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Flip a footprint to the opposite copper side and return the updated child-graphics layer summary."""

    return await _run_client_tool(
        "kicad_flip_footprint",
        "flip_footprint",
        reference=reference,
        footprint_id=footprint_id,
        target_layer=target_layer,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_flip_board_items(
    item_ids: list[str],
    direction: int | str = "left_right",
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Flip one or more board items to the opposite side by their unique IDs."""

    return await _run_client_tool(
        "kicad_flip_board_items",
        "flip_board_items_by_id",
        item_ids=item_ids,
        direction=direction,
        dry_run=dry_run,
        commit_message=commit_message,
    )


@mcp.tool()
async def kicad_update_footprint_pad_net(
    net_name: str,
    reference: str | None = None,
    footprint_id: str | None = None,
    pad_number: str | None = None,
    pad_id: str | None = None,
    expected_current_net_name: str | None = None,
    dry_run: bool = False,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Reassign one footprint pad to a different board net, with optional dry run."""

    return await _run_client_tool(
        "kicad_update_footprint_pad_net",
        "update_footprint_pad_net",
        net_name=net_name,
        reference=reference,
        footprint_id=footprint_id,
        pad_number=pad_number,
        pad_id=pad_id,
        expected_current_net_name=expected_current_net_name,
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
async def kicad_add_to_selection(
    item_ids: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Add one or more items to the current board selection."""

    return await _run_client_tool(
        "kicad_add_to_selection",
        "add_to_selection",
        item_ids=item_ids,
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_remove_from_selection(
    item_ids: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove one or more items from the current board selection."""

    return await _run_client_tool(
        "kicad_remove_from_selection",
        "remove_from_selection",
        item_ids=item_ids,
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_clear_selection(dry_run: bool = False) -> dict[str, Any]:
    """Clear the current board selection."""

    return await _run_client_tool(
        "kicad_clear_selection",
        "clear_selection",
        dry_run=dry_run,
    )


@mcp.tool()
async def kicad_set_editor_appearance_settings(
    inactive_layer_display: int | str | None = None,
    net_color_display: int | str | None = None,
    board_flip: int | str | None = None,
    ratsnest_display: int | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Update board editor appearance settings."""

    return await _run_client_tool(
        "kicad_set_editor_appearance_settings",
        "set_editor_appearance_settings",
        inactive_layer_display=inactive_layer_display,
        net_color_display=net_color_display,
        board_flip=board_flip,
        ratsnest_display=ratsnest_display,
        dry_run=dry_run,
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


@mcp.tool()
async def kicad_save_board_as(
    filename: str,
    overwrite: bool = False,
    include_project: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Save the current board to a new filename, with optional dry run."""

    return await _run_client_tool(
        "kicad_save_board_as",
        "save_board_as",
        filename=filename,
        overwrite=overwrite,
        include_project=include_project,
        dry_run=dry_run,
    )


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
