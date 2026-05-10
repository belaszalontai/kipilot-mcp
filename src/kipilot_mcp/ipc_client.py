"""Async-friendly wrapper around KiCad's official Python IPC bindings."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Sequence
from typing import Any

from .config import KiCadIpcConfig
from .errors import KiCadBindingUnavailableError, KiCadCapabilityError, KiCadLookupError
from .lookups import (
    BoundingBoxFilter,
    filter_items_by_area,
    item_matches_layer,
    resolve_footprint,
    resolve_layer_id,
    resolve_net,
)
from .serializers import (
    merge_boxes,
    serialize_board_text,
    serialize_document,
    serialize_footprint,
    serialize_identifier,
    serialize_item,
    serialize_layer,
    serialize_net,
    serialize_net_class,
    serialize_pad,
    serialize_polygon,
    serialize_project,
    serialize_shape,
    serialize_stackup,
    serialize_text_variables,
    serialize_title_block,
    serialize_track,
    serialize_vector,
    serialize_via,
    serialize_zone,
)

BOARD_ORIGIN_GRID = 1
BOARD_ORIGIN_DRILL = 2
VIA_TYPE_THROUGH = 1
BOARD_ORIGIN_NAMES = {
    BOARD_ORIGIN_GRID: "grid",
    BOARD_ORIGIN_DRILL: "drill",
}
VIA_TYPE_NAMES = {
    VIA_TYPE_THROUGH: "through",
}
BOARD_ORIGIN_ALIASES = {
    "1": BOARD_ORIGIN_GRID,
    "grid": BOARD_ORIGIN_GRID,
    "grid_origin": BOARD_ORIGIN_GRID,
    "grid-origin": BOARD_ORIGIN_GRID,
    "2": BOARD_ORIGIN_DRILL,
    "drill": BOARD_ORIGIN_DRILL,
    "drill_place": BOARD_ORIGIN_DRILL,
    "drill-place": BOARD_ORIGIN_DRILL,
    "drill/place": BOARD_ORIGIN_DRILL,
    "place": BOARD_ORIGIN_DRILL,
}
VIA_TYPE_ALIASES = {
    "1": VIA_TYPE_THROUGH,
    "through": VIA_TYPE_THROUGH,
    "through_hole": VIA_TYPE_THROUGH,
    "through-hole": VIA_TYPE_THROUGH,
}
BOARD_WRITE_RETRY_ATTEMPTS = {
    "refill_zones": 3,
    "revert_board": 2,
}
BOARD_WRITE_RETRY_DELAY_SECONDS = {
    "refill_zones": 2.0,
    "revert_board": 1.0,
}
WHITELISTED_UPDATE_ITEM_KINDS = ("footprint", "track", "zone")

logger = logging.getLogger(__name__)

try:
    from kipy import KiCad  # type: ignore[import-not-found]
    from kipy.board_types import Track as KiCadTrack  # type: ignore[import-not-found]
    from kipy.board_types import Via as KiCadVia  # type: ignore[import-not-found]
    from kipy.errors import ApiError  # type: ignore[import-not-found]
    from kipy.geometry import (
        PolygonWithHoles as KiCadPolygonWithHoles,
    )  # type: ignore[import-not-found]
    from kipy.geometry import PolyLine as KiCadPolyLine  # type: ignore[import-not-found]
    from kipy.geometry import PolyLineNode as KiCadPolyLineNode  # type: ignore[import-not-found]
    from kipy.geometry import Vector2 as KiCadVector2  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local environment
    KiCad = None
    KiCadTrack = None
    KiCadVia = None
    KiCadPolyLine = None
    KiCadPolyLineNode = None
    KiCadPolygonWithHoles = None
    KiCadVector2 = None

    class ApiError(RuntimeError):
        """Fallback API error used when kicad-python is unavailable."""

    _KIPY_IMPORT_ERROR = exc
else:
    _KIPY_IMPORT_ERROR = None


class KiCadIpcClient:
    """Connect to a user-running KiCad instance through the IPC API."""

    def __init__(
        self,
        config: KiCadIpcConfig | None = None,
        kicad_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._config = config or KiCadIpcConfig.from_env()
        self._kicad_factory = kicad_factory

    @property
    def config(self) -> KiCadIpcConfig:
        return self._config

    async def check_connection(self) -> dict[str, Any]:
        """Check whether KiCad's IPC API accepts a connection."""

        try:
            return await asyncio.to_thread(self._probe_connection)
        except Exception as exc:  # noqa: BLE001
            result = self._translate_error(
                exc,
                default_message=(
                    "KiCad IPC is not reachable. Start KiCad 10 or newer, open the PCB Editor, "
                    "and verify KICAD_API_SOCKET/KICAD_API_TOKEN if you are not using the "
                    "default platform IPC endpoint."
                ),
            )
            result["socket_path"] = self._config.socket_path
            result["client_name"] = self._config.client_name
            return result

    async def list_open_documents(
        self,
        document_types: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Return the current board/project documents or query explicit document types."""

        return await self._run_kicad(
            lambda kicad: self._list_open_documents(kicad, document_types),
            default_message="Unable to list open KiCad documents through the IPC API.",
        )

    async def get_board_summary(self) -> dict[str, Any]:
        """Return high-level information about the currently open PCB."""

        return await self._run_board_read(
            self._get_board_summary,
            default_message="Unable to read the current KiCad PCB through the IPC API.",
        )

    async def get_stackup(self) -> dict[str, Any]:
        """Return board stackup and enabled layer information."""

        return await self._run_board_read(
            self._get_stackup,
            default_message="Unable to read the board stackup through the IPC API.",
        )

    async def get_footprints(self, limit: int = 200) -> dict[str, Any]:
        """Return placed footprint references and positions from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_footprints(board, limit),
            default_message="Unable to read board footprints through the IPC API.",
        )

    async def find_footprints(
        self,
        reference: str | None = None,
        footprint_id: str | None = None,
        text_query: str | None = None,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Find footprints by reference, ID, text query, layer, or board area."""

        return await self._run_board_read(
            lambda board: self._find_footprints(
                board, reference, footprint_id, text_query, layer, area, limit
            ),
            default_message="Unable to search footprints through the IPC API.",
        )

    async def get_nets(self, limit: int = 200) -> dict[str, Any]:
        """Return net names from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_nets(board, limit),
            default_message="Unable to read board nets through the IPC API.",
        )

    async def get_tracks(self, limit: int = 200) -> dict[str, Any]:
        """Return tracks from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_tracks(board, limit),
            default_message="Unable to read board tracks through the IPC API.",
        )

    async def get_vias(self, limit: int = 200) -> dict[str, Any]:
        """Return vias from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_vias(board, limit),
            default_message="Unable to read board vias through the IPC API.",
        )

    async def get_zones(self, limit: int = 200) -> dict[str, Any]:
        """Return zones from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_zones(board, limit),
            default_message="Unable to read board zones through the IPC API.",
        )

    async def get_board_text(
        self,
        text_id: str | None = None,
        text_query: str | None = None,
        layer: int | str | None = None,
        exact: bool = False,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return standalone board text items, with optional ID/text/layer filters."""

        return await self._run_board_read(
            lambda board: self._get_board_text(
                board,
                text_id=text_id,
                text_query=text_query,
                layer=layer,
                exact=exact,
                limit=limit,
            ),
            default_message="Unable to read board text through the IPC API.",
        )

    async def get_pads(
        self,
        net_name: str | None = None,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return pads from the current PCB, with optional net, layer, and area filters."""

        return await self._run_board_read(
            lambda board: self._get_pads(board, net_name, layer, area, limit),
            default_message="Unable to read board pads through the IPC API.",
        )

    async def get_graphics(
        self,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return generic board graphics from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_graphics(board, layer, area, limit),
            default_message="Unable to read board graphics through the IPC API.",
        )

    async def get_project_text_variables(self) -> dict[str, Any]:
        """Return text variables from the current board project."""

        return await self._run_project(
            self._get_project_text_variables,
            default_message="Unable to read project text variables through the IPC API.",
        )

    async def expand_project_text_variables(self, text: str) -> dict[str, Any]:
        """Expand project text variables inside a user-provided text fragment."""

        return await self._run_project(
            lambda project: self._expand_project_text_variables(project, text),
            default_message="Unable to expand project text variables through the IPC API.",
        )

    async def get_project_net_classes(self) -> dict[str, Any]:
        """Return project net classes from the active board project."""

        return await self._run_project(
            self._get_project_net_classes,
            default_message="Unable to read project net classes through the IPC API.",
        )

    async def get_board_origins(self) -> dict[str, Any]:
        """Return the grid and drill/place board origins."""

        return await self._run_board_read(
            self._get_board_origins,
            default_message="Unable to read board origins through the IPC API.",
        )

    async def get_title_block(self) -> dict[str, Any]:
        """Return the current board title block information."""

        return await self._run_board_read(
            self._get_title_block,
            default_message="Unable to read board title block information through the IPC API.",
        )

    async def get_items_by_net(
        self,
        net_name: str,
        item_types: Sequence[int] | None = None,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return board items filtered by a resolved net name."""

        return await self._run_board_read(
            lambda board: self._get_items_by_net(board, net_name, item_types, layer, area, limit),
            default_message="Unable to read items by net through the IPC API.",
        )

    async def get_items_by_netclass(
        self,
        netclass_name: str,
        item_types: Sequence[int] | None = None,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return board items filtered by a named net class."""

        return await self._run_kicad(
            lambda kicad: self._get_items_by_netclass(
                kicad,
                netclass_name,
                item_types,
                layer,
                area,
                limit,
            ),
            default_message="Unable to read items by net class through the IPC API.",
        )

    async def get_netclass_for_nets(self, net_names: Sequence[str]) -> dict[str, Any]:
        """Return the effective net class for one or more named nets."""

        return await self._run_kicad(
            lambda kicad: self._get_netclass_for_nets(kicad, net_names),
            default_message="Unable to resolve net classes for the requested nets.",
        )

    async def get_connected_items(
        self,
        item_id: str,
        item_types: Sequence[int] | None = None,
        layer: int | str | None = None,
        area: dict[str, float | int] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return copper-connected items for one source board item."""

        return await self._run_board_read(
            lambda board: self._get_connected_items(board, item_id, item_types, layer, area, limit),
            default_message="Unable to read copper-connected items through the IPC API.",
        )

    async def get_board_outline(self) -> dict[str, Any]:
        """Derive the board outline from Edge.Cuts shapes."""

        return await self._run_board_read(
            self._get_board_outline,
            default_message="Unable to derive the board outline through the IPC API.",
        )

    async def _run_kicad(
        self,
        operation: Callable[[Any], dict[str, Any]],
        *,
        default_message: str,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._with_kicad, operation)
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    async def _run_project(
        self,
        operation: Callable[[Any], dict[str, Any]],
        *,
        default_message: str,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._with_project, operation)
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    async def _run_board_read(
        self,
        operation: Callable[[Any], dict[str, Any]],
        *,
        default_message: str,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._with_board, operation)
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    async def _run_board_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        *,
        default_message: str,
        mutation_name: str,
        dry_run: bool = False,
        commit_message: str | None = None,
        use_commit: bool = True,
        dangerous: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            self._assert_mutation_allowed(dry_run=dry_run, dangerous=dangerous, force=force)
            return await asyncio.to_thread(
                self._with_board_write,
                operation,
                mutation_name,
                dry_run,
                commit_message,
                use_commit,
            )
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    async def set_visible_layers(
        self,
        layers: Sequence[int | str],
        *,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Set the currently visible board layers."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_visible_layers(board, layers, is_dry_run),
            default_message="Unable to update visible board layers through the IPC API.",
            mutation_name="set_visible_layers",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def set_active_layer(
        self,
        layer: int | str,
        *,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Set the active board layer."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_active_layer(board, layer, is_dry_run),
            default_message="Unable to update the active board layer through the IPC API.",
            mutation_name="set_active_layer",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def set_enabled_layers(
        self,
        non_copper_layers: Sequence[int | str],
        *,
        dry_run: bool = False,
        commit_message: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Set enabled non-copper board layers while keeping the copper stackup intact."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_enabled_layers(
                board,
                non_copper_layers,
                dry_run=is_dry_run,
                force=force,
            ),
            default_message="Unable to update enabled board layers through the IPC API.",
            mutation_name="set_enabled_layers",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def revert_board(
        self,
        *,
        dry_run: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Revert the board to its last saved state."""

        return await self._run_board_write(
            self._revert_board,
            default_message="Unable to revert the current board through the IPC API.",
            mutation_name="revert_board",
            dry_run=dry_run,
            use_commit=False,
            dangerous=True,
            force=force,
        )

    async def move_footprint(
        self,
        *,
        reference: str | None = None,
        footprint_id: str | None = None,
        x_mm: float,
        y_mm: float,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Move a footprint instance to an absolute board position."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._move_footprint(
                board,
                reference=reference,
                footprint_id=footprint_id,
                x_mm=x_mm,
                y_mm=y_mm,
                dry_run=is_dry_run,
            ),
            default_message="Unable to move the requested footprint through the IPC API.",
            mutation_name="move_footprint",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def rotate_footprint(
        self,
        *,
        reference: str | None = None,
        footprint_id: str | None = None,
        orientation_degrees: float,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Set a footprint instance to an absolute orientation in degrees."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._rotate_footprint(
                board,
                reference=reference,
                footprint_id=footprint_id,
                orientation_degrees=orientation_degrees,
                dry_run=is_dry_run,
            ),
            default_message="Unable to rotate the requested footprint through the IPC API.",
            mutation_name="rotate_footprint",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def set_board_origin(
        self,
        *,
        origin_type: int | str,
        x_mm: float,
        y_mm: float,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Set either the grid or drill/place board origin."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_board_origin(
                board,
                origin_type=origin_type,
                x_mm=x_mm,
                y_mm=y_mm,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the requested board origin through the IPC API.",
            mutation_name="set_board_origin",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def set_title_block(
        self,
        *,
        title: str | None = None,
        revision: str | None = None,
        date: str | None = None,
        company: str | None = None,
        comments: dict[str | int, str] | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Update one or more title block fields on the current board."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_title_block(
                board,
                title=title,
                revision=revision,
                date=date,
                company=company,
                comments=comments,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the board title block through the IPC API.",
            mutation_name="set_title_block",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_board_text(
        self,
        *,
        text_id: str,
        new_text: str,
        expected_current_text: str | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Update one board text or text box value by board item ID."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._update_board_text(
                board,
                text_id=text_id,
                new_text=new_text,
                expected_current_text=expected_current_text,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the requested board text through the IPC API.",
            mutation_name="update_board_text",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def create_track_segments(
        self,
        *,
        points: Sequence[dict[str, float | int]],
        layer: int | str,
        width_mm: float,
        net_name: str | None = None,
        locked: bool = False,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Create straight copper track segments from a polyline of points."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._create_track_segments(
                board,
                points=points,
                layer=layer,
                width_mm=width_mm,
                net_name=net_name,
                locked=locked,
                dry_run=is_dry_run,
            ),
            default_message="Unable to create track segments through the IPC API.",
            mutation_name="create_track_segments",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def create_via(
        self,
        *,
        x_mm: float,
        y_mm: float,
        diameter_mm: float,
        drill_diameter_mm: float,
        net_name: str | None = None,
        via_type: int | str = VIA_TYPE_THROUGH,
        locked: bool = False,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Create a via at an absolute board position."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._create_via(
                board,
                x_mm=x_mm,
                y_mm=y_mm,
                diameter_mm=diameter_mm,
                drill_diameter_mm=drill_diameter_mm,
                net_name=net_name,
                via_type=via_type,
                locked=locked,
                dry_run=is_dry_run,
            ),
            default_message="Unable to create a via through the IPC API.",
            mutation_name="create_via",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_items(
        self,
        *,
        updates: Sequence[dict[str, Any]],
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Apply whitelisted low-level updates to footprints, tracks, and zones."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._update_items(
                board,
                updates=updates,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the requested board items through the IPC API.",
            mutation_name="update_items",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_track_geometry(
        self,
        *,
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
        """Update one straight track's geometry or metadata fields."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._update_track_geometry(
                board,
                track_id=track_id,
                start_x_mm=start_x_mm,
                start_y_mm=start_y_mm,
                end_x_mm=end_x_mm,
                end_y_mm=end_y_mm,
                width_mm=width_mm,
                layer=layer,
                net_name=net_name,
                locked=locked,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update track geometry through the IPC API.",
            mutation_name="update_track_geometry",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_zone_outline(
        self,
        *,
        zone_id: str,
        outline_points: Sequence[dict[str, float | int]],
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Replace a zone's outer polygon outline with a new point list."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._update_zone_outline(
                board,
                zone_id=zone_id,
                outline_points=outline_points,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the requested zone outline through the IPC API.",
            mutation_name="update_zone_outline",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def delete_items(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
        commit_message: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete one or more board items by KiCad item ID."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._delete_items(
                board,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message="Unable to delete the requested board items through the IPC API.",
            mutation_name="delete_items",
            dry_run=dry_run,
            commit_message=commit_message,
            dangerous=True,
            force=force,
        )

    async def refill_zones(
        self,
        *,
        zone_ids: Sequence[str] | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Refill all zones, or only a selected subset, on the current board."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._refill_zones(
                board,
                zone_ids=zone_ids,
                dry_run=is_dry_run,
            ),
            default_message="Unable to refill zones through the IPC API.",
            mutation_name="refill_zones",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def save_board(
        self,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Save the current board file to disk."""

        return await self._run_board_write(
            self._save_board,
            default_message="Unable to save the current board through the IPC API.",
            mutation_name="save_board",
            dry_run=dry_run,
            use_commit=False,
        )

    def _probe_connection(self) -> dict[str, Any]:
        return self._with_kicad(self._check_connection)

    def _check_connection(self, kicad: Any) -> dict[str, Any]:
        kicad.ping()
        return {
            "ok": True,
            "socket_path": self._config.socket_path,
            "client_name": self._config.client_name,
            "kicad_version": str(kicad.get_version()),
            "api_version": str(kicad.get_api_version()),
            "api_version_matches_binding": bool(kicad.check_version()),
            "message": "KiCad IPC endpoint is reachable.",
        }

    def _connection_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "client_name": self._config.client_name,
            "timeout_ms": self._config.timeout_ms,
        }

        if self._config.socket_path:
            kwargs["socket_path"] = self._config.socket_path
        if self._config.api_token:
            kwargs["kicad_token"] = self._config.api_token

        return kwargs

    def _with_kicad(self, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        factory = self._resolve_kicad_factory()
        kicad = factory(**self._connection_kwargs())

        try:
            return operation(kicad)
        finally:
            close = getattr(kicad, "close", None)
            if callable(close):
                close()

    def _with_project(self, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        return self._with_kicad(lambda kicad: operation(self._resolve_project(kicad)))

    def _with_board(self, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        return self._with_kicad(lambda kicad: operation(kicad.get_board()))

    def _with_board_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
        commit_message: str | None,
        use_commit: bool,
    ) -> dict[str, Any]:
        resolved_commit_message = self._resolve_commit_message(mutation_name, commit_message)
        max_attempts = self._board_write_attempt_limit(mutation_name, dry_run)
        last_error: Exception | None = None

        for attempt_number in range(1, max_attempts + 1):
            try:
                result = self._with_kicad(
                    lambda kicad: self._execute_board_write(
                        kicad,
                        operation,
                        mutation_name,
                        dry_run,
                        resolved_commit_message,
                        use_commit,
                    )
                )
                if attempt_number > 1:
                    logger.info(
                        "Board write recovered after retry. mutation=%s attempts=%s",
                        mutation_name,
                        attempt_number,
                    )
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not self._should_retry_board_write(
                    exc,
                    mutation_name=mutation_name,
                    dry_run=dry_run,
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                ):
                    raise

                retry_delay_seconds = self._board_write_retry_delay_seconds(
                    mutation_name,
                    attempt_number,
                )
                logger.warning(
                    "Retrying board write. mutation=%s attempt=%s/%s delay_seconds=%s error=%s",
                    mutation_name,
                    attempt_number + 1,
                    max_attempts,
                    retry_delay_seconds,
                    exc,
                )
                if retry_delay_seconds > 0:
                    time.sleep(retry_delay_seconds)

        if last_error is not None:
            raise last_error

        raise KiCadCapabilityError("Board write failed without a captured error.")

    def _execute_board_write(
        self,
        kicad: Any,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
        resolved_commit_message: str,
        use_commit: bool,
    ) -> dict[str, Any]:
        board = kicad.get_board()
        commit = None

        if use_commit and not dry_run:
            begin_commit = getattr(board, "begin_commit", None)
            if callable(begin_commit):
                commit = begin_commit()

        try:
            result = operation(board, dry_run)
            if commit is not None:
                push_commit = getattr(board, "push_commit", None)
                if not callable(push_commit):
                    raise KiCadCapabilityError(
                        "The active KiCad board does not expose "
                        "push_commit(), so atomic writes are unavailable."
                    )
                push_commit(commit, resolved_commit_message)
        except Exception:
            if commit is not None:
                drop_commit = getattr(board, "drop_commit", None)
                if callable(drop_commit):
                    drop_commit(commit)
            raise

        return {
            "ok": True,
            "mutation": mutation_name,
            "dry_run": dry_run,
            "commit_message": None if dry_run or not use_commit else resolved_commit_message,
            **result,
        }

    def _board_write_attempt_limit(self, mutation_name: str, dry_run: bool) -> int:
        if dry_run:
            return 1
        return BOARD_WRITE_RETRY_ATTEMPTS.get(mutation_name, 1)

    def _should_retry_board_write(
        self,
        exc: Exception,
        *,
        mutation_name: str,
        dry_run: bool,
        attempt_number: int,
        max_attempts: int,
    ) -> bool:
        if dry_run or attempt_number >= max_attempts:
            return False

        if mutation_name not in BOARD_WRITE_RETRY_ATTEMPTS:
            return False

        message = str(exc)
        return self._is_retryable_board_write_message(message)

    def _board_write_retry_delay_seconds(
        self,
        mutation_name: str,
        attempt_number: int,
    ) -> float:
        base_delay_seconds = BOARD_WRITE_RETRY_DELAY_SECONDS.get(mutation_name, 0.0)
        return base_delay_seconds * attempt_number

    def _is_retryable_board_write_message(self, message: str) -> bool:
        normalized = message.strip().lower()
        return any(
            candidate in normalized
            for candidate in (
                "timed out",
                "kicad is busy",
                "cannot respond to api requests right now",
            )
        )

    def _resolve_kicad_factory(self) -> Callable[..., Any]:
        if self._kicad_factory is not None:
            return self._kicad_factory
        if KiCad is not None:
            return KiCad

        raise KiCadBindingUnavailableError(
            "The kicad-python binding is not installed in this Python environment. "
            "Use a stable Python release such as 3.13, 3.12, or 3.11 for "
            "local development, then install the project "
            f"dependencies. Import error: {_KIPY_IMPORT_ERROR}"
        )

    def _resolve_project(self, kicad: Any) -> Any:
        board = kicad.get_board()
        get_project = getattr(board, "get_project", None)
        if callable(get_project):
            project = get_project()
            if project is not None:
                return project

        document = getattr(board, "document", None)
        kicad_get_project = getattr(kicad, "get_project", None)
        if callable(kicad_get_project) and document is not None:
            return kicad_get_project(document)

        raise KiCadCapabilityError(
            "Unable to resolve the current KiCad project from the active board."
        )

    def _assert_mutation_allowed(self, *, dry_run: bool, dangerous: bool, force: bool) -> None:
        if dangerous and not force:
            raise KiCadCapabilityError(
                "This mutation is destructive. Re-run with force=True after "
                "verifying the board target."
            )

        if not dry_run and not self._config.enable_mutations:
            raise KiCadCapabilityError(
                "KiCad mutations are disabled. Set KIPILOT_ENABLE_MUTATIONS=1 "
                "to allow write operations. "
                "Dry-run requests are still allowed without this gate."
            )

    def _resolve_commit_message(self, mutation_name: str, commit_message: str | None) -> str:
        if commit_message:
            return commit_message

        prefix = self._config.commit_message_prefix.strip() or "KiPilot MCP"
        return f"{prefix}: {mutation_name}"

    def _list_open_documents(
        self,
        kicad: Any,
        document_types: Sequence[int] | None,
    ) -> dict[str, Any]:
        documents: list[dict[str, Any]] = []
        seen: set[str] = set()

        if document_types:
            get_open_documents = getattr(kicad, "get_open_documents", None)
            if not callable(get_open_documents):
                raise KiCadCapabilityError(
                    "This KiCad binding does not expose get_open_documents() "
                    "on the active endpoint."
                )

            for document_type in document_types:
                for document in get_open_documents(document_type):
                    self._append_document(documents, seen, document)

            return {
                "ok": True,
                "count": len(documents),
                "document_types": list(document_types),
                "documents": documents,
                "source": "explicit_types",
            }

        board = kicad.get_board()
        self._append_document(documents, seen, getattr(board, "document", None))

        try:
            project = self._resolve_project(kicad)
        except Exception:  # noqa: BLE001
            project = None

        self._append_document(documents, seen, getattr(project, "document", None))

        return {
            "ok": True,
            "count": len(documents),
            "documents": documents,
            "source": "active_board",
        }

    def _get_board_summary(self, board: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "counts": {
                "footprints": len(board.get_footprints()),
                "nets": len(board.get_nets()),
                "tracks": len(board.get_tracks()),
                "vias": len(board.get_vias()),
                "zones": len(board.get_zones()),
                "graphics": len(board.get_shapes()),
                "text_items": len(board.get_text()),
            },
            "copper_layer_count": board.get_copper_layer_count(),
            "active_layer": board.get_active_layer(),
        }

    def _get_stackup(self, board: Any) -> dict[str, Any]:
        visible_layers = self._get_optional_layers(board, "get_visible_layers")
        enabled_layers = self._get_optional_layers(board, "get_enabled_layers")

        return {
            "ok": True,
            "stackup": serialize_stackup(board.get_stackup(), board),
            "copper_layer_count": board.get_copper_layer_count(),
            "visible_layers": visible_layers,
            "enabled_layers": enabled_layers,
        }

    def _get_footprints(self, board: Any, limit: int) -> dict[str, Any]:
        footprints = list(board.get_footprints())

        return {
            "ok": True,
            "count": len(footprints),
            "limit": limit,
            "footprints": [serialize_footprint(footprint) for footprint in footprints[:limit]],
        }

    def _find_footprints(
        self,
        board: Any,
        reference: str | None,
        footprint_id: str | None,
        text_query: str | None,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        reference_query = (reference or "").strip().lower()
        footprint_id_query = (footprint_id or "").strip().lower()
        text_query_normalized = (text_query or "").strip().lower()
        resolved_layer = resolve_layer_id(board, layer)
        area_filter = BoundingBoxFilter.from_query(area)

        matches = []
        for footprint in board.get_footprints():
            serialized = serialize_footprint(footprint)
            serialized_reference = str(serialized["reference"]).lower()
            serialized_value = str(serialized["value"]).lower()
            serialized_id = str(serialized["id"]).lower()

            if footprint_id_query and serialized_id != footprint_id_query:
                continue
            if reference_query and reference_query not in serialized_reference:
                continue
            if resolved_layer is not None and not item_matches_layer(footprint, resolved_layer):
                continue
            if text_query_normalized and not any(
                text_query_normalized in candidate
                for candidate in (serialized_reference, serialized_value, serialized_id)
            ):
                continue
            if area_filter is not None and not filter_items_by_area(
                board, [footprint], area_filter
            ):
                continue

            matches.append(serialized)

        return {
            "ok": True,
            "count": len(matches),
            "limit": limit,
            "query": {
                "reference": reference,
                "footprint_id": footprint_id,
                "text_query": text_query,
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "footprints": matches[:limit],
        }

    def _get_nets(self, board: Any, limit: int) -> dict[str, Any]:
        nets = list(board.get_nets())

        return {
            "ok": True,
            "count": len(nets),
            "limit": limit,
            "nets": [serialize_net(net) for net in nets[:limit]],
        }

    def _get_tracks(self, board: Any, limit: int) -> dict[str, Any]:
        tracks = list(board.get_tracks())

        return {
            "ok": True,
            "count": len(tracks),
            "limit": limit,
            "tracks": [serialize_track(track, board) for track in tracks[:limit]],
        }

    def _get_vias(self, board: Any, limit: int) -> dict[str, Any]:
        vias = list(board.get_vias())

        return {
            "ok": True,
            "count": len(vias),
            "limit": limit,
            "vias": [serialize_via(via, board) for via in vias[:limit]],
        }

    def _get_zones(self, board: Any, limit: int) -> dict[str, Any]:
        zones = list(board.get_zones())

        return {
            "ok": True,
            "count": len(zones),
            "limit": limit,
            "zones": [serialize_zone(zone, board) for zone in zones[:limit]],
        }

    def _get_board_text(
        self,
        board: Any,
        *,
        text_id: str | None,
        text_query: str | None,
        layer: int | str | None,
        exact: bool,
        limit: int,
    ) -> dict[str, Any]:
        text_id_query = (text_id or "").strip().lower()
        text_query_normalized = (text_query or "").strip().lower()
        resolved_layer = resolve_layer_id(board, layer)

        matches = []
        for text_item in board.get_text():
            serialized = serialize_board_text(text_item, board)
            serialized_id = str(serialized["id"]).strip().lower()
            serialized_text = str(serialized["text"]).strip().lower()

            if text_id_query and serialized_id != text_id_query:
                continue
            if resolved_layer is not None and not item_matches_layer(text_item, resolved_layer):
                continue
            if text_query_normalized:
                if exact and serialized_text != text_query_normalized:
                    continue
                if not exact and text_query_normalized not in serialized_text:
                    continue

            matches.append(serialized)

        return {
            "ok": True,
            "count": len(matches),
            "limit": limit,
            "query": {
                "text_id": text_id,
                "text_query": text_query,
                "exact": bool(exact),
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
            },
            "text_items": matches[:limit],
        }

    def _get_pads(
        self,
        board: Any,
        net_name: str | None,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        get_pads = getattr(board, "get_pads", None)
        if not callable(get_pads):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_pads()."
            )

        resolved_layer = resolve_layer_id(board, layer)
        resolved_net = resolve_net(board, net_name) if net_name else None
        area_filter = BoundingBoxFilter.from_query(area)

        pads = list(get_pads())
        if resolved_net is not None:
            target_name = str(getattr(resolved_net, "name", "")).strip().lower()
            pads = [
                pad
                for pad in pads
                if str(getattr(getattr(pad, "net", None), "name", "")).strip().lower()
                == target_name
            ]
        if resolved_layer is not None:
            pads = [pad for pad in pads if item_matches_layer(pad, resolved_layer)]
        pads = filter_items_by_area(board, pads, area_filter)

        return {
            "ok": True,
            "count": len(pads),
            "limit": limit,
            "query": {
                "net_name": net_name,
                "net": serialize_net(resolved_net),
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "pads": [serialize_pad(pad, board) for pad in pads[:limit]],
        }

    def _get_graphics(
        self,
        board: Any,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        get_shapes = getattr(board, "get_shapes", None)
        if not callable(get_shapes):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_shapes()."
            )

        resolved_layer = resolve_layer_id(board, layer)
        area_filter = BoundingBoxFilter.from_query(area)

        graphics = list(get_shapes())
        if resolved_layer is not None:
            graphics = [item for item in graphics if item_matches_layer(item, resolved_layer)]
        graphics = filter_items_by_area(board, graphics, area_filter)

        return {
            "ok": True,
            "count": len(graphics),
            "limit": limit,
            "query": {
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "graphics": [serialize_shape(shape, board) for shape in graphics[:limit]],
        }

    def _get_project_text_variables(self, project: Any) -> dict[str, Any]:
        get_text_variables = getattr(project, "get_text_variables", None)
        if not callable(get_text_variables):
            raise KiCadCapabilityError(
                "This KiCad binding does not expose project text variables on the active endpoint."
            )

        return {
            "ok": True,
            "project": serialize_project(project),
            "text_variables": serialize_text_variables(get_text_variables()),
        }

    def _expand_project_text_variables(self, project: Any, text: str) -> dict[str, Any]:
        expand_text_variables = getattr(project, "expand_text_variables", None)
        if not callable(expand_text_variables):
            raise KiCadCapabilityError(
                "This KiCad binding does not expose project text-variable expansion "
                "on the active endpoint."
            )

        return {
            "ok": True,
            "project": serialize_project(project),
            "input_text": text,
            "expanded_text": str(expand_text_variables(text)),
        }

    def _get_project_net_classes(self, project: Any) -> dict[str, Any]:
        net_classes = self._get_project_net_class_items(project)

        return {
            "ok": True,
            "project": serialize_project(project),
            "count": len(net_classes),
            "net_classes": [serialize_net_class(net_class) for net_class in net_classes],
        }

    def _get_board_origins(self, board: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "origins": {
                BOARD_ORIGIN_NAMES[origin_type]: self._serialize_board_origin(
                    origin_type,
                    self._get_origin_value(board, origin_type),
                )
                for origin_type in BOARD_ORIGIN_NAMES
            },
        }

    def _get_title_block(self, board: Any) -> dict[str, Any]:
        title_block = self._get_title_block_info(board)
        return {
            "ok": True,
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "title_block": serialize_title_block(title_block),
        }

    def _get_items_by_net(
        self,
        board: Any,
        net_name: str,
        item_types: Sequence[int] | None,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        get_items_by_net = getattr(board, "get_items_by_net", None)
        if not callable(get_items_by_net):
            raise KiCadCapabilityError(
                "kicad_get_items_by_net requires KiCad 10.0.1 or newer board bindings."
            )

        net = resolve_net(board, net_name)
        resolved_layer = resolve_layer_id(board, layer)
        area_filter = BoundingBoxFilter.from_query(area)
        try:
            items = (
                get_items_by_net(net, types=item_types)
                if item_types is not None
                else get_items_by_net(net)
            )
        except TypeError:
            items = (
                get_items_by_net(net, item_types)
                if item_types is not None
                else get_items_by_net(net)
            )

        resolved_items = list(items)
        if resolved_layer is not None:
            resolved_items = [
                item for item in resolved_items if item_matches_layer(item, resolved_layer)
            ]
        resolved_items = filter_items_by_area(board, resolved_items, area_filter)

        serialized_items = [serialize_item(item, board) for item in resolved_items[:limit]]
        return {
            "ok": True,
            "net": serialize_net(net),
            "count": len(resolved_items),
            "limit": limit,
            "item_types": list(item_types) if item_types is not None else None,
            "query": {
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "items": serialized_items,
        }

    def _get_items_by_netclass(
        self,
        kicad: Any,
        netclass_name: str,
        item_types: Sequence[int] | None,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        board = kicad.get_board()
        project = self._resolve_project(kicad)
        net_class = self._resolve_project_net_class(project, netclass_name)

        get_items_by_netclass = getattr(board, "get_items_by_netclass", None)
        if not callable(get_items_by_netclass):
            raise KiCadCapabilityError(
                "kicad_get_items_by_netclass requires KiCad 10.0.1 or newer board bindings."
            )

        resolved_layer = resolve_layer_id(board, layer)
        area_filter = BoundingBoxFilter.from_query(area)
        resolved_name = str(getattr(net_class, "name", netclass_name))
        try:
            items = (
                get_items_by_netclass(resolved_name, types=item_types)
                if item_types is not None
                else get_items_by_netclass(resolved_name)
            )
        except TypeError:
            items = (
                get_items_by_netclass(resolved_name, item_types)
                if item_types is not None
                else get_items_by_netclass(resolved_name)
            )

        resolved_items = list(items)
        if resolved_layer is not None:
            resolved_items = [
                item for item in resolved_items if item_matches_layer(item, resolved_layer)
            ]
        resolved_items = filter_items_by_area(board, resolved_items, area_filter)

        return {
            "ok": True,
            "net_class": serialize_net_class(net_class),
            "count": len(resolved_items),
            "limit": limit,
            "item_types": list(item_types) if item_types is not None else None,
            "query": {
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "items": [serialize_item(item, board) for item in resolved_items[:limit]],
        }

    def _get_netclass_for_nets(self, kicad: Any, net_names: Sequence[str]) -> dict[str, Any]:
        normalized_net_names = self._normalize_non_empty_strings(
            net_names,
            field_name="net_names",
        )
        board = kicad.get_board()
        resolved_nets = [resolve_net(board, net_name) for net_name in normalized_net_names]

        get_netclass_for_nets = getattr(board, "get_netclass_for_nets", None)
        if not callable(get_netclass_for_nets):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_netclass_for_nets()."
            )

        lookup_input: Any = resolved_nets[0] if len(resolved_nets) == 1 else resolved_nets
        raw_result = get_netclass_for_nets(lookup_input)
        if isinstance(raw_result, dict):
            netclass_map = {str(key): value for key, value in raw_result.items()}
        else:
            netclass_map = {str(getattr(resolved_nets[0], "name", "")): raw_result}

        results = []
        for net in resolved_nets:
            net_name = str(getattr(net, "name", ""))
            results.append(
                {
                    "net": serialize_net(net),
                    "net_class": serialize_net_class(netclass_map.get(net_name)),
                }
            )

        return {
            "ok": True,
            "count": len(results),
            "results": results,
        }

    def _get_connected_items(
        self,
        board: Any,
        item_id: str,
        item_types: Sequence[int] | None,
        layer: int | str | None,
        area: dict[str, float | int] | None,
        limit: int,
    ) -> dict[str, Any]:
        get_connected_items = getattr(board, "get_connected_items", None)
        if not callable(get_connected_items):
            raise KiCadCapabilityError(
                "kicad_get_connected_items requires KiCad 10.0.1 or newer board bindings."
            )

        source_item = self._resolve_board_item_by_id(
            board,
            item_id,
            ("get_tracks", "get_vias", "get_pads", "get_zones"),
            "connectivity source item",
        )
        resolved_layer = resolve_layer_id(board, layer)
        area_filter = BoundingBoxFilter.from_query(area)
        try:
            connected_items = (
                get_connected_items(source_item, types=item_types)
                if item_types is not None
                else get_connected_items(source_item)
            )
        except TypeError:
            connected_items = (
                get_connected_items(source_item, item_types)
                if item_types is not None
                else get_connected_items(source_item)
            )

        source_item_id = serialize_identifier(getattr(source_item, "id", "")).strip().lower()
        resolved_items = [
            item
            for item in list(connected_items)
            if serialize_identifier(getattr(item, "id", "")).strip().lower() != source_item_id
        ]
        if resolved_layer is not None:
            resolved_items = [
                item for item in resolved_items if item_matches_layer(item, resolved_layer)
            ]
        resolved_items = filter_items_by_area(board, resolved_items, area_filter)

        return {
            "ok": True,
            "source_item": serialize_item(source_item, board),
            "count": len(resolved_items),
            "limit": limit,
            "item_types": list(item_types) if item_types is not None else None,
            "query": {
                "layer": layer,
                "resolved_layer": serialize_layer(resolved_layer, board)
                if resolved_layer is not None
                else None,
                "area": area_filter.to_query_dict() if area_filter is not None else None,
            },
            "items": [serialize_item(item, board) for item in resolved_items[:limit]],
        }

    def _get_board_outline(self, board: Any) -> dict[str, Any]:
        edge_cuts_layer = resolve_layer_id(board, "Edge.Cuts")
        outline_shapes = []
        for shape in board.get_shapes():
            if edge_cuts_layer is None or not item_matches_layer(shape, edge_cuts_layer):
                continue
            outline_shapes.append(serialize_shape(shape, board))

        bounding_boxes = [shape.get("bounding_box") for shape in outline_shapes]
        return {
            "ok": True,
            "count": len(outline_shapes),
            "layer_name": "Edge.Cuts",
            "shapes": outline_shapes,
            "bounding_box": merge_boxes(bounding_boxes),
        }

    def _set_visible_layers(
        self,
        board: Any,
        layers: Sequence[int | str],
        dry_run: bool,
    ) -> dict[str, Any]:
        resolved_layers: list[int] = []
        for layer in layers:
            resolved_layer = resolve_layer_id(board, layer)
            if resolved_layer is None:
                continue
            if resolved_layer not in resolved_layers:
                resolved_layers.append(resolved_layer)

        if not resolved_layers:
            raise KiCadLookupError("At least one visible layer must be provided.")

        previous_visible_layers = self._get_optional_layers(board, "get_visible_layers")
        target_visible_layers = [serialize_layer(layer, board) for layer in resolved_layers]

        if not dry_run:
            set_visible_layers = getattr(board, "set_visible_layers", None)
            if not callable(set_visible_layers):
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose set_visible_layers()."
                )
            set_visible_layers(resolved_layers)

        current_visible_layers = (
            target_visible_layers
            if dry_run
            else self._get_optional_layers(board, "get_visible_layers")
        )

        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "previous_visible_layers": previous_visible_layers,
            "visible_layers": current_visible_layers,
            "requested_layers": list(layers),
            "resolved_layers": target_visible_layers,
        }

    def _set_active_layer(
        self,
        board: Any,
        layer: int | str,
        dry_run: bool,
    ) -> dict[str, Any]:
        resolved_layer = resolve_layer_id(board, layer)
        if resolved_layer is None:
            raise KiCadLookupError("A target layer must be provided.")

        get_active_layer = getattr(board, "get_active_layer", None)
        if not callable(get_active_layer):
            raise KiCadCapabilityError("The active KiCad board does not expose get_active_layer().")

        previous_active_layer = get_active_layer()
        if not dry_run:
            set_active_layer = getattr(board, "set_active_layer", None)
            if not callable(set_active_layer):
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose set_active_layer()."
                )
            set_active_layer(resolved_layer)

        current_active_layer = resolved_layer if dry_run else get_active_layer()
        return {
            "board": self._serialize_board(board),
            "previous_active_layer": serialize_layer(previous_active_layer, board),
            "active_layer": serialize_layer(current_active_layer, board),
            "requested_layer": layer,
        }

    def _set_enabled_layers(
        self,
        board: Any,
        non_copper_layers: Sequence[int | str],
        *,
        dry_run: bool,
        force: bool,
    ) -> dict[str, Any]:
        previous_enabled_layers = self._get_optional_layers(board, "get_enabled_layers")
        current_enabled_layer_ids = [
            layer["id"]
            for layer in previous_enabled_layers or []
            if isinstance(layer.get("id"), int)
        ]
        current_copper_layers = [
            layer_id
            for layer_id in current_enabled_layer_ids
            if self._is_copper_layer(board, layer_id)
        ]

        resolved_non_copper_layers: list[int] = []
        for layer in non_copper_layers:
            resolved_layer = resolve_layer_id(board, layer)
            if resolved_layer is None:
                continue
            if self._is_copper_layer(board, resolved_layer):
                raise KiCadLookupError(
                    "kicad_set_enabled_layers only accepts non-copper layers. "
                    "Use the board stackup workflow for copper layer-count changes."
                )
            if resolved_layer not in resolved_non_copper_layers:
                resolved_non_copper_layers.append(resolved_layer)

        copper_layer_count = board.get_copper_layer_count()
        preview_enabled_layers = [
            serialize_layer(layer_id, board)
            for layer_id in [*current_copper_layers, *resolved_non_copper_layers]
        ]

        if not dry_run:
            if not force:
                raise KiCadCapabilityError(
                    "Changing enabled layers can delete items on layers that are disabled. "
                    "Re-run with force=True after verifying the target layer set."
                )

            set_enabled_layers = getattr(board, "set_enabled_layers", None)
            if not callable(set_enabled_layers):
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose set_enabled_layers()."
                )
            set_enabled_layers(copper_layer_count, resolved_non_copper_layers)

        current_enabled_layers = (
            preview_enabled_layers
            if dry_run
            else self._get_optional_layers(board, "get_enabled_layers")
        )
        return {
            "board": self._serialize_board(board),
            "dangerous": True,
            "copper_layer_count": copper_layer_count,
            "previous_enabled_layers": previous_enabled_layers,
            "enabled_layers": current_enabled_layers,
            "requested_non_copper_layers": list(non_copper_layers),
            "resolved_non_copper_layers": [
                serialize_layer(layer_id, board) for layer_id in resolved_non_copper_layers
            ],
        }

    def _revert_board(self, board: Any, dry_run: bool) -> dict[str, Any]:
        if not dry_run:
            revert = getattr(board, "revert", None)
            if not callable(revert):
                raise KiCadCapabilityError("The active KiCad board does not expose revert().")
            revert()

        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "dangerous": True,
        }

    def _set_board_origin(
        self,
        board: Any,
        *,
        origin_type: int | str,
        x_mm: float,
        y_mm: float,
        dry_run: bool,
    ) -> dict[str, Any]:
        resolved_origin_type = self._resolve_board_origin_type(origin_type)
        previous_origin = self._get_origin_value(board, resolved_origin_type)
        updated_origin = self._make_vector_like(
            previous_origin,
            self._millimeters_to_nanometers(x_mm),
            self._millimeters_to_nanometers(y_mm),
        )

        if not dry_run:
            set_origin = getattr(board, "set_origin", None)
            if not callable(set_origin):
                raise KiCadCapabilityError("The active KiCad board does not expose set_origin().")
            set_origin(resolved_origin_type, updated_origin)

        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "origin_type": self._serialize_origin_type(resolved_origin_type),
            "previous_origin": serialize_vector(previous_origin),
            "origin": serialize_vector(updated_origin),
            "requested_origin": {
                "x_nm": self._millimeters_to_nanometers(x_mm),
                "y_nm": self._millimeters_to_nanometers(y_mm),
                "x_mm": float(x_mm),
                "y_mm": float(y_mm),
            },
        }

    def _set_title_block(
        self,
        board: Any,
        *,
        title: str | None,
        revision: str | None,
        date: str | None,
        company: str | None,
        comments: dict[str | int, str] | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        if (
            title is None
            and revision is None
            and date is None
            and company is None
            and comments is None
        ):
            raise KiCadLookupError("At least one title block field or comment must be provided.")

        previous_title_block = self._get_title_block_info(board)
        updated_title_block = self._clone_proto_wrapper(previous_title_block)

        if title is not None:
            updated_title_block.title = title
        if revision is not None:
            updated_title_block.revision = revision
        if date is not None:
            updated_title_block.date = date
        if company is not None:
            updated_title_block.company = company
        normalized_comments = self._normalize_title_block_comments(comments)
        if normalized_comments is not None:
            merged_comments = dict(getattr(updated_title_block, "comments", {}) or {})
            merged_comments.update(normalized_comments)
            try:
                updated_title_block.comments = merged_comments
            except Exception:  # noqa: BLE001
                existing_comments = getattr(updated_title_block, "comments", None)
                if hasattr(existing_comments, "clear") and hasattr(existing_comments, "update"):
                    existing_comments.clear()
                    existing_comments.update(merged_comments)
                else:
                    raise

        if not dry_run:
            set_title_block_info = getattr(board, "set_title_block_info", None)
            if not callable(set_title_block_info):
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose set_title_block_info()."
                )
            set_title_block_info(updated_title_block)

        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "previous_title_block": serialize_title_block(previous_title_block),
            "title_block": serialize_title_block(updated_title_block),
            "requested_changes": {
                "title": title,
                "revision": revision,
                "date": date,
                "company": company,
                "comments": {str(key): value for key, value in (normalized_comments or {}).items()}
                or None,
            },
        }

    def _update_board_text(
        self,
        board: Any,
        *,
        text_id: str,
        new_text: str,
        expected_current_text: str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        board_text = self._resolve_board_item_by_id(board, text_id, ("get_text",), "board text")
        previous_text_item = serialize_board_text(board_text, board)
        current_text = self._get_text_item_value(board_text)

        if expected_current_text is not None and current_text != expected_current_text:
            raise KiCadLookupError(
                f"Board text {text_id!r} did not match expected text "
                f"{expected_current_text!r}; current text is {current_text!r}."
            )

        updated_text_item = self._clone_item(board_text)
        self._set_text_item_value(updated_text_item, new_text)

        applied_text_item = updated_text_item
        if not dry_run:
            update_items = getattr(board, "update_items", None)
            if not callable(update_items):
                raise KiCadCapabilityError("The active KiCad board does not expose update_items().")

            try:
                update_result = update_items([updated_text_item])
            except TypeError:
                update_result = update_items(updated_text_item)

            resolved_items = self._as_item_sequence(update_result)
            if resolved_items:
                applied_text_item = resolved_items[0]

        return {
            "board": self._serialize_board(board),
            "target": {"text_id": text_id},
            "previous_text_item": previous_text_item,
            "text_item": serialize_board_text(applied_text_item, board),
            "requested_changes": {
                "new_text": str(new_text),
                "expected_current_text": expected_current_text,
            },
        }

    def _move_footprint(
        self,
        board: Any,
        *,
        reference: str | None,
        footprint_id: str | None,
        x_mm: float,
        y_mm: float,
        dry_run: bool,
    ) -> dict[str, Any]:
        x_nm = self._millimeters_to_nanometers(x_mm)
        y_nm = self._millimeters_to_nanometers(y_mm)

        return self._update_footprint(
            board,
            reference=reference,
            footprint_id=footprint_id,
            dry_run=dry_run,
            mutate=lambda footprint: setattr(
                footprint,
                "position",
                self._make_vector_like(getattr(footprint, "position", None), x_nm, y_nm),
            ),
            details={
                "requested_position": {
                    "x_nm": x_nm,
                    "y_nm": y_nm,
                    "x_mm": x_mm,
                    "y_mm": y_mm,
                },
            },
        )

    def _rotate_footprint(
        self,
        board: Any,
        *,
        reference: str | None,
        footprint_id: str | None,
        orientation_degrees: float,
        dry_run: bool,
    ) -> dict[str, Any]:
        return self._update_footprint(
            board,
            reference=reference,
            footprint_id=footprint_id,
            dry_run=dry_run,
            mutate=lambda footprint: setattr(
                footprint,
                "orientation",
                self._make_angle_like(getattr(footprint, "orientation", None), orientation_degrees),
            ),
            details={
                "requested_orientation_degrees": float(orientation_degrees),
            },
        )

    def _create_track_segments(
        self,
        board: Any,
        *,
        points: Sequence[dict[str, float | int]],
        layer: int | str,
        width_mm: float,
        net_name: str | None,
        locked: bool,
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_points = self._normalize_points(points, minimum=2, label="track polyline")
        resolved_layer = resolve_layer_id(board, layer)
        if resolved_layer is None:
            raise KiCadLookupError(f"Unable to resolve layer {layer!r}.")

        width_nm = self._validate_positive_measurement_mm(width_mm, field_name="Track width")
        net = resolve_net(board, net_name) if net_name is not None else None

        preview_tracks = []
        for start_point, end_point in zip(normalized_points, normalized_points[1:], strict=False):
            track = self._construct_new_item(
                board,
                getter_name="get_tracks",
                imported_type=KiCadTrack,
                kind_name="Track",
            )
            track.start = self._construct_vector(board, start_point["x_nm"], start_point["y_nm"])
            track.end = self._construct_vector(board, end_point["x_nm"], end_point["y_nm"])
            track.layer = resolved_layer
            track.width = width_nm
            if net is not None:
                track.net = net
            track.locked = bool(locked)
            preview_tracks.append(track)

        applied_tracks = preview_tracks
        if not dry_run:
            create_items = getattr(board, "create_items", None)
            if not callable(create_items):
                raise KiCadCapabilityError("The active KiCad board does not expose create_items().")

            try:
                create_result = create_items(preview_tracks)
            except TypeError:
                if len(preview_tracks) != 1:
                    raise
                create_result = create_items(preview_tracks[0])

            resolved_items = self._as_item_sequence(create_result)
            if resolved_items:
                applied_tracks = resolved_items

        return {
            "board": self._serialize_board(board),
            "count": len(applied_tracks),
            "layer": serialize_layer(resolved_layer, board),
            "net": serialize_net(net),
            "locked": bool(locked),
            "requested_width": {
                "width_nm": width_nm,
                "width_mm": float(width_mm),
            },
            "requested_points": normalized_points,
            "tracks": [serialize_track(track, board) for track in applied_tracks],
        }

    def _create_via(
        self,
        board: Any,
        *,
        x_mm: float,
        y_mm: float,
        diameter_mm: float,
        drill_diameter_mm: float,
        net_name: str | None,
        via_type: int | str,
        locked: bool,
        dry_run: bool,
    ) -> dict[str, Any]:
        diameter_nm = self._validate_positive_measurement_mm(
            diameter_mm,
            field_name="Via diameter",
        )
        drill_diameter_nm = self._validate_positive_measurement_mm(
            drill_diameter_mm,
            field_name="Via drill diameter",
        )
        if drill_diameter_nm > diameter_nm:
            raise KiCadLookupError("Via drill diameter must not exceed the via diameter.")

        resolved_via_type = self._resolve_via_type(via_type)
        net = resolve_net(board, net_name) if net_name is not None else None
        preview_via = self._construct_new_item(
            board,
            getter_name="get_vias",
            imported_type=KiCadVia,
            kind_name="Via",
        )
        preview_via.position = self._construct_vector(
            board,
            self._millimeters_to_nanometers(x_mm),
            self._millimeters_to_nanometers(y_mm),
        )
        preview_via.diameter = diameter_nm
        preview_via.drill_diameter = drill_diameter_nm
        preview_via.type = resolved_via_type
        preview_via.locked = bool(locked)
        if net is not None:
            preview_via.net = net

        applied_via = preview_via
        if not dry_run:
            create_items = getattr(board, "create_items", None)
            if not callable(create_items):
                raise KiCadCapabilityError("The active KiCad board does not expose create_items().")

            try:
                create_result = create_items([preview_via])
            except TypeError:
                create_result = create_items(preview_via)

            resolved_items = self._as_item_sequence(create_result)
            if resolved_items:
                applied_via = resolved_items[0]

        return {
            "board": self._serialize_board(board),
            "position": {
                "x_nm": self._millimeters_to_nanometers(x_mm),
                "y_nm": self._millimeters_to_nanometers(y_mm),
                "x_mm": float(x_mm),
                "y_mm": float(y_mm),
            },
            "diameter": {
                "value_nm": diameter_nm,
                "value_mm": float(diameter_mm),
            },
            "drill_diameter": {
                "value_nm": drill_diameter_nm,
                "value_mm": float(drill_diameter_mm),
            },
            "via_type": self._serialize_via_type(resolved_via_type),
            "net": serialize_net(net),
            "locked": bool(locked),
            "via": serialize_via(applied_via, board),
        }

    def _update_items(
        self,
        board: Any,
        *,
        updates: Sequence[dict[str, Any]],
        dry_run: bool,
    ) -> dict[str, Any]:
        if not updates:
            raise KiCadLookupError("At least one item update must be provided.")

        prepared_updates = []
        seen_targets: set[tuple[str, str]] = set()
        for index, update in enumerate(updates, start=1):
            prepared_update = self._prepare_whitelisted_item_update(board, update, index)
            target_key = (prepared_update["kind"], prepared_update["target_id"])
            if target_key in seen_targets:
                raise KiCadLookupError(
                    "Each item may only be updated once per request. "
                    f"Duplicate target: {prepared_update['kind']} {prepared_update['target_id']!r}."
                )
            seen_targets.add(target_key)
            prepared_updates.append(prepared_update)

        updated_items = [prepared_update["updated_item"] for prepared_update in prepared_updates]
        applied_items = (
            updated_items if dry_run else self._apply_board_item_updates(board, updated_items)
        )

        return {
            "board": self._serialize_board(board),
            "count": len(prepared_updates),
            "allowed_kinds": list(WHITELISTED_UPDATE_ITEM_KINDS),
            "updates": [
                {
                    "kind": prepared_update["kind"],
                    "target": prepared_update["target"],
                    "previous_item": prepared_update["previous_item"],
                    "item": prepared_update["serialize"](applied_item),
                    "requested_changes": prepared_update["requested_changes"],
                }
                for prepared_update, applied_item in zip(
                    prepared_updates,
                    applied_items,
                    strict=False,
                )
            ],
        }

    def _prepare_whitelisted_item_update(
        self,
        board: Any,
        update: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        if not isinstance(update, dict):
            raise KiCadLookupError(f"Item update {index} must be an object.")

        kind = str(update.get("kind", "")).strip().lower()
        if kind == "footprint":
            return self._prepare_whitelisted_footprint_update(board, update, index)
        if kind == "track":
            return self._prepare_whitelisted_track_update(board, update, index)
        if kind == "zone":
            return self._prepare_whitelisted_zone_update(board, update, index)

        supported = ", ".join(WHITELISTED_UPDATE_ITEM_KINDS)
        raise KiCadLookupError(
            f"Item update {index} has unsupported kind {kind!r}. Supported kinds: {supported}."
        )

    def _prepare_whitelisted_footprint_update(
        self,
        board: Any,
        update: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        self._validate_allowed_update_keys(
            update,
            allowed_keys={
                "kind",
                "reference",
                "footprint_id",
                "x_mm",
                "y_mm",
                "orientation_degrees",
            },
            item_label=f"Item update {index}",
        )

        reference = update.get("reference")
        footprint_id = update.get("footprint_id")
        if reference is None and footprint_id is None:
            raise KiCadLookupError(
                f"Item update {index} must include reference or footprint_id for footprint updates."
            )

        has_position = "x_mm" in update or "y_mm" in update
        if ("x_mm" in update) != ("y_mm" in update):
            raise KiCadLookupError(
                f"Item update {index} must include both x_mm and y_mm for footprint moves."
            )
        has_orientation = "orientation_degrees" in update
        if not has_position and not has_orientation:
            raise KiCadLookupError(
                f"Item update {index} must include x_mm/y_mm and/or orientation_degrees."
            )

        footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
        previous_item = serialize_footprint(footprint)
        updated_footprint = self._clone_item(footprint)
        requested_changes: dict[str, Any] = {
            "position": None,
            "orientation_degrees": None,
        }

        if has_position:
            x_mm = float(update["x_mm"])
            y_mm = float(update["y_mm"])
            x_nm = self._millimeters_to_nanometers(x_mm)
            y_nm = self._millimeters_to_nanometers(y_mm)
            updated_footprint.position = self._make_vector_like(
                getattr(updated_footprint, "position", None),
                x_nm,
                y_nm,
            )
            requested_changes["position"] = {
                "x_nm": x_nm,
                "y_nm": y_nm,
                "x_mm": x_mm,
                "y_mm": y_mm,
            }

        if has_orientation:
            orientation_degrees = float(update["orientation_degrees"])
            updated_footprint.orientation = self._make_angle_like(
                getattr(updated_footprint, "orientation", None),
                orientation_degrees,
            )
            requested_changes["orientation_degrees"] = orientation_degrees

        return {
            "kind": "footprint",
            "target_id": str(previous_item["id"]),
            "target": {
                "reference": previous_item["reference"],
                "footprint_id": previous_item["id"],
            },
            "previous_item": previous_item,
            "updated_item": updated_footprint,
            "serialize": serialize_footprint,
            "requested_changes": requested_changes,
        }

    def _prepare_whitelisted_track_update(
        self,
        board: Any,
        update: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        self._validate_allowed_update_keys(
            update,
            allowed_keys={
                "kind",
                "track_id",
                "start_x_mm",
                "start_y_mm",
                "end_x_mm",
                "end_y_mm",
                "width_mm",
                "layer",
                "net_name",
                "locked",
            },
            item_label=f"Item update {index}",
        )

        track_id = str(update.get("track_id", "")).strip()
        if not track_id:
            raise KiCadLookupError(f"Item update {index} must include a non-empty track_id.")

        requested_start = self._normalize_optional_point(
            x_mm=update.get("start_x_mm") if "start_x_mm" in update else None,
            y_mm=update.get("start_y_mm") if "start_y_mm" in update else None,
            label=f"Item update {index} track start",
        )
        requested_end = self._normalize_optional_point(
            x_mm=update.get("end_x_mm") if "end_x_mm" in update else None,
            y_mm=update.get("end_y_mm") if "end_y_mm" in update else None,
            label=f"Item update {index} track end",
        )
        has_width = "width_mm" in update
        has_layer = "layer" in update
        has_net = "net_name" in update
        has_locked = "locked" in update
        if not any((requested_start, requested_end, has_width, has_layer, has_net, has_locked)):
            raise KiCadLookupError(
                f"Item update {index} must change at least one track field."
            )

        track = self._resolve_board_item_by_id(board, track_id, ("get_tracks",), "track")
        previous_item = serialize_track(track, board)
        updated_track = self._clone_item(track)

        if requested_start is not None:
            updated_track.start = self._make_vector_like(
                getattr(updated_track, "start", None),
                requested_start["x_nm"],
                requested_start["y_nm"],
            )
        if requested_end is not None:
            updated_track.end = self._make_vector_like(
                getattr(updated_track, "end", None),
                requested_end["x_nm"],
                requested_end["y_nm"],
            )

        resolved_layer = None
        if has_width:
            updated_track.width = self._validate_positive_measurement_mm(
                update["width_mm"],
                field_name="Track width",
            )
        if has_layer:
            resolved_layer = resolve_layer_id(board, update.get("layer"))
            if resolved_layer is None:
                raise KiCadLookupError(
                    f"Item update {index} could not resolve layer {update.get('layer')!r}."
                )
            updated_track.layer = resolved_layer

        resolved_net = None
        if has_net:
            resolved_net = resolve_net(board, update.get("net_name"))
            updated_track.net = resolved_net
        if has_locked:
            updated_track.locked = bool(update.get("locked"))

        return {
            "kind": "track",
            "target_id": str(previous_item["id"]),
            "target": {"track_id": previous_item["id"]},
            "previous_item": previous_item,
            "updated_item": updated_track,
            "serialize": lambda item: serialize_track(item, board),
            "requested_changes": {
                "start": requested_start,
                "end": requested_end,
                "width_mm": float(update["width_mm"]) if has_width else None,
                "layer": None if resolved_layer is None else serialize_layer(resolved_layer, board),
                "net": serialize_net(resolved_net),
                "locked": bool(update.get("locked")) if has_locked else None,
            },
        }

    def _prepare_whitelisted_zone_update(
        self,
        board: Any,
        update: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        self._validate_allowed_update_keys(
            update,
            allowed_keys={
                "kind",
                "zone_id",
                "outline_points",
            },
            item_label=f"Item update {index}",
        )

        zone_id = str(update.get("zone_id", "")).strip()
        if not zone_id:
            raise KiCadLookupError(f"Item update {index} must include a non-empty zone_id.")
        if "outline_points" not in update:
            raise KiCadLookupError(
                f"Item update {index} must include outline_points for zone updates."
            )

        normalized_points = self._normalize_points(
            update["outline_points"],
            minimum=3,
            label=f"item update {index} zone outline",
        )
        zone = self._resolve_board_item_by_id(board, zone_id, ("get_zones",), "zone")
        previous_item = serialize_zone(zone, board)
        updated_zone = self._clone_item(zone)
        updated_zone.outline = self._make_polygon_like(
            board,
            getattr(updated_zone, "outline", None),
            normalized_points,
        )

        return {
            "kind": "zone",
            "target_id": str(previous_item["id"]),
            "target": {"zone_id": previous_item["id"]},
            "previous_item": previous_item,
            "updated_item": updated_zone,
            "serialize": lambda item: serialize_zone(item, board),
            "requested_changes": {
                "outline_points": normalized_points,
            },
        }

    def _apply_board_item_updates(self, board: Any, updated_items: Sequence[Any]) -> list[Any]:
        update_items = getattr(board, "update_items", None)
        if not callable(update_items):
            raise KiCadCapabilityError("The active KiCad board does not expose update_items().")

        try:
            update_result = update_items(list(updated_items))
        except TypeError:
            if len(updated_items) != 1:
                raise
            update_result = update_items(updated_items[0])

        resolved_items = self._as_item_sequence(update_result)
        if not resolved_items:
            return list(updated_items)

        resolved_items_by_id = {
            serialize_identifier(getattr(item, "id", "")): item for item in resolved_items
        }
        return [
            resolved_items_by_id.get(serialize_identifier(getattr(item, "id", "")), item)
            for item in updated_items
        ]

    def _validate_allowed_update_keys(
        self,
        update: dict[str, Any],
        *,
        allowed_keys: set[str],
        item_label: str,
    ) -> None:
        unexpected_keys = sorted(set(update) - allowed_keys)
        if not unexpected_keys:
            return

        formatted_keys = ", ".join(unexpected_keys)
        raise KiCadLookupError(
            f"{item_label} includes unsupported fields: {formatted_keys}."
        )

    def _update_track_geometry(
        self,
        board: Any,
        *,
        track_id: str,
        start_x_mm: float | None,
        start_y_mm: float | None,
        end_x_mm: float | None,
        end_y_mm: float | None,
        width_mm: float | None,
        layer: int | str | None,
        net_name: str | None,
        locked: bool | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        requested_start = self._normalize_optional_point(
            x_mm=start_x_mm,
            y_mm=start_y_mm,
            label="Track start",
        )
        requested_end = self._normalize_optional_point(
            x_mm=end_x_mm,
            y_mm=end_y_mm,
            label="Track end",
        )

        if (
            requested_start is None
            and requested_end is None
            and width_mm is None
            and layer is None
            and net_name is None
            and locked is None
        ):
            raise KiCadLookupError(
                "At least one track field must be provided: start, end, width_mm, "
                "layer, net_name, or locked."
            )

        track = self._resolve_board_item_by_id(board, track_id, ("get_tracks",), "track")
        previous_track = serialize_track(track, board)
        updated_track = self._clone_item(track)

        if requested_start is not None:
            updated_track.start = self._make_vector_like(
                getattr(updated_track, "start", None),
                requested_start["x_nm"],
                requested_start["y_nm"],
            )
        if requested_end is not None:
            updated_track.end = self._make_vector_like(
                getattr(updated_track, "end", None),
                requested_end["x_nm"],
                requested_end["y_nm"],
            )
        if width_mm is not None:
            updated_track.width = self._validate_positive_measurement_mm(
                width_mm,
                field_name="Track width",
            )
        resolved_layer = None
        if layer is not None:
            resolved_layer = resolve_layer_id(board, layer)
            if resolved_layer is None:
                raise KiCadLookupError(f"Unable to resolve layer {layer!r}.")
            updated_track.layer = resolved_layer
        resolved_net = None
        if net_name is not None:
            resolved_net = resolve_net(board, net_name)
            updated_track.net = resolved_net
        if locked is not None:
            updated_track.locked = bool(locked)

        applied_track = updated_track
        if not dry_run:
            update_items = getattr(board, "update_items", None)
            if not callable(update_items):
                raise KiCadCapabilityError("The active KiCad board does not expose update_items().")

            try:
                update_result = update_items([updated_track])
            except TypeError:
                update_result = update_items(updated_track)

            resolved_items = self._as_item_sequence(update_result)
            if resolved_items:
                applied_track = resolved_items[0]

        return {
            "board": self._serialize_board(board),
            "target": {"track_id": track_id},
            "previous_track": previous_track,
            "track": serialize_track(applied_track, board),
            "requested_changes": {
                "start": requested_start,
                "end": requested_end,
                "width_mm": None if width_mm is None else float(width_mm),
                "layer": None if resolved_layer is None else serialize_layer(resolved_layer, board),
                "net": serialize_net(resolved_net),
                "locked": locked,
            },
        }

    def _update_zone_outline(
        self,
        board: Any,
        *,
        zone_id: str,
        outline_points: Sequence[dict[str, float | int]],
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_points = self._normalize_points(
            outline_points,
            minimum=3,
            label="zone outline",
        )
        zone = self._resolve_board_item_by_id(board, zone_id, ("get_zones",), "zone")
        previous_zone = serialize_zone(zone, board)
        updated_zone = self._clone_item(zone)
        updated_zone.outline = self._make_polygon_like(
            board,
            getattr(updated_zone, "outline", None),
            normalized_points,
        )

        applied_zone = updated_zone
        if not dry_run:
            update_items = getattr(board, "update_items", None)
            if not callable(update_items):
                raise KiCadCapabilityError("The active KiCad board does not expose update_items().")

            try:
                update_result = update_items([updated_zone])
            except TypeError:
                update_result = update_items(updated_zone)

            resolved_items = self._as_item_sequence(update_result)
            if resolved_items:
                applied_zone = resolved_items[0]

        return {
            "board": self._serialize_board(board),
            "target": {"zone_id": zone_id},
            "previous_zone": previous_zone,
            "zone": serialize_zone(applied_zone, board),
            "requested_outline": {
                "points": normalized_points,
                "polygon": serialize_polygon(getattr(updated_zone, "outline", None)),
            },
        }

    def _delete_items(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_item_ids = self._normalize_item_ids(item_ids)
        items = [
            self._resolve_board_item_by_id(
                board,
                item_id,
                ("get_tracks", "get_vias", "get_zones", "get_footprints", "get_shapes"),
                "board item",
            )
            for item_id in normalized_item_ids
        ]
        serialized_items = [serialize_item(item, board) for item in items]

        if not dry_run:
            remove_items = getattr(board, "remove_items", None)
            remove_items_by_id = getattr(board, "remove_items_by_id", None)

            if callable(remove_items):
                try:
                    remove_items(items)
                except TypeError:
                    if len(items) != 1:
                        raise
                    remove_items(items[0])
            elif callable(remove_items_by_id):
                try:
                    remove_items_by_id(normalized_item_ids)
                except TypeError:
                    if len(normalized_item_ids) != 1:
                        raise
                    remove_items_by_id(normalized_item_ids[0])
            else:
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose remove_items() or remove_items_by_id()."
                )

        return {
            "board": self._serialize_board(board),
            "dangerous": True,
            "count": len(serialized_items),
            "item_ids": normalized_item_ids,
            "items": serialized_items,
        }

    def _refill_zones(
        self,
        board: Any,
        *,
        zone_ids: Sequence[str] | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        selected_zone_ids = None if zone_ids is None else self._normalize_item_ids(zone_ids)
        all_zones = list(board.get_zones())
        if selected_zone_ids is None:
            zones = all_zones
        else:
            zones = [
                self._resolve_board_item_by_id(board, zone_id, ("get_zones",), "zone")
                for zone_id in selected_zone_ids
            ]

        if not zones:
            raise KiCadLookupError("No zones matched the refill request.")

        applied_zones = zones
        if not dry_run:
            refill_zones = getattr(board, "refill_zones", None)
            if not callable(refill_zones):
                raise KiCadCapabilityError("The active KiCad board does not expose refill_zones().")

            if selected_zone_ids is None:
                try:
                    refill_result = refill_zones()
                except TypeError:
                    refill_result = refill_zones(zones)
            else:
                try:
                    refill_result = refill_zones(zones)
                except TypeError:
                    if len(zones) != 1:
                        raise
                    refill_result = refill_zones(zones[0])

            resolved_items = self._as_item_sequence(refill_result)
            if resolved_items:
                applied_zones = resolved_items

        return {
            "board": self._serialize_board(board),
            "count": len(applied_zones),
            "zone_ids": selected_zone_ids,
            "zones": [serialize_zone(zone, board) for zone in applied_zones],
        }

    def _save_board(self, board: Any, dry_run: bool) -> dict[str, Any]:
        if not dry_run:
            save = getattr(board, "save", None)
            if not callable(save):
                raise KiCadCapabilityError("The active KiCad board does not expose save().")
            save()

        board_info = self._serialize_board(board)
        board_document = board_info.get("document") or {}
        return {
            "board": board_info,
            "saved_filename": board_document.get("board_filename") or getattr(board, "name", None),
        }

    def _update_footprint(
        self,
        board: Any,
        *,
        reference: str | None,
        footprint_id: str | None,
        dry_run: bool,
        mutate: Callable[[Any], None],
        details: dict[str, Any],
    ) -> dict[str, Any]:
        footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
        previous_footprint = serialize_footprint(footprint)
        updated_footprint = self._clone_item(footprint)
        mutate(updated_footprint)

        applied_footprint = updated_footprint
        if not dry_run:
            update_items = getattr(board, "update_items", None)
            if not callable(update_items):
                raise KiCadCapabilityError("The active KiCad board does not expose update_items().")

            try:
                update_result = update_items([updated_footprint])
            except TypeError:
                update_result = update_items(updated_footprint)

            resolved_items = self._as_item_sequence(update_result)
            if resolved_items:
                applied_footprint = resolved_items[0]

        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "target": {
                "reference": reference,
                "footprint_id": footprint_id,
            },
            "previous_footprint": previous_footprint,
            "footprint": serialize_footprint(applied_footprint),
            **details,
        }

    def _clone_item(self, item: Any) -> Any:
        return self._clone_proto_wrapper(item)

    def _get_text_item_value(self, item: Any) -> str:
        value = getattr(item, "value", None)
        if value is None:
            value = getattr(item, "text", None)
        if value is None:
            return ""
        return str(value)

    def _set_text_item_value(self, item: Any, value: str) -> None:
        try:
            item.value = str(value)
            return
        except Exception:  # noqa: BLE001
            pass

        if hasattr(item, "text"):
            try:
                item.text = str(value)
                return
            except Exception:  # noqa: BLE001
                pass

        raise KiCadCapabilityError(
            f"The active KiCad type {type(item).__name__} does not expose a mutable text value."
        )

    def _clone_proto_wrapper(self, value: Any) -> Any:
        value_type = type(value)
        proto = getattr(value, "proto", None)
        if proto is None:
            raise KiCadCapabilityError(
                f"The active KiCad type {value_type.__name__} does not expose proto-based cloning."
            )

        try:
            return value_type(proto)
        except Exception as exc:  # noqa: BLE001
            raise KiCadCapabilityError(
                f"Unable to clone {value_type.__name__} for safe mutation preview/update."
            ) from exc

    def _make_vector_like(self, current: Any, x_nm: int, y_nm: int) -> Any:
        if current is None:
            raise KiCadCapabilityError("The target item does not expose a mutable position vector.")

        vector_type = type(current)
        from_xy = getattr(vector_type, "from_xy", None)
        if callable(from_xy):
            return from_xy(x_nm, y_nm)

        try:
            return vector_type(x_nm, y_nm)
        except Exception as exc:  # noqa: BLE001
            raise KiCadCapabilityError(
                f"Unable to construct a position value for {vector_type.__name__}."
            ) from exc

    def _make_angle_like(self, current: Any, degrees: float) -> Any:
        if current is None:
            raise KiCadCapabilityError(
                "The target item does not expose a mutable orientation angle."
            )

        angle_type = type(current)
        from_degrees = getattr(angle_type, "from_degrees", None)
        if callable(from_degrees):
            angle = from_degrees(degrees)
        else:
            try:
                angle = angle_type(degrees)
            except Exception as exc:  # noqa: BLE001
                raise KiCadCapabilityError(
                    f"Unable to construct an orientation value for {angle_type.__name__}."
                ) from exc

        normalize = getattr(angle, "normalize", None)
        if callable(normalize):
            return normalize()
        return angle

    def _as_item_sequence(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return list(value)
        return [value]

    def _serialize_board(self, board: Any) -> dict[str, Any]:
        return {
            "name": getattr(board, "name", None),
            "document": serialize_document(getattr(board, "document", None)),
        }

    def _construct_new_item(
        self,
        board: Any,
        *,
        getter_name: str,
        imported_type: Callable[[], Any] | None,
        kind_name: str,
    ) -> Any:
        getter = getattr(board, getter_name, None)
        if callable(getter):
            items = list(getter())
            if items:
                item_type = type(items[0])
                try:
                    return item_type()
                except Exception:
                    pass

        if imported_type is not None:
            try:
                return imported_type()
            except Exception as exc:  # noqa: BLE001
                raise KiCadCapabilityError(
                    f"Unable to construct a new {kind_name} instance for board creation."
                ) from exc

        raise KiCadCapabilityError(
            f"Unable to construct a new {kind_name} instance for board creation."
        )

    def _construct_vector(self, board: Any, x_nm: int, y_nm: int) -> Any:
        sample_vector = self._find_sample_vector(board)
        if sample_vector is not None:
            return self._make_vector_like(sample_vector, x_nm, y_nm)

        if KiCadVector2 is not None:
            from_xy = getattr(KiCadVector2, "from_xy", None)
            if callable(from_xy):
                return from_xy(x_nm, y_nm)
            try:
                return KiCadVector2(x_nm, y_nm)
            except Exception as exc:  # noqa: BLE001
                raise KiCadCapabilityError(
                    "Unable to construct a KiCad Vector2 for board mutation."
                ) from exc

        raise KiCadCapabilityError(
            "Unable to construct a position vector for board mutation."
        )

    def _find_sample_vector(self, board: Any) -> Any | None:
        for getter_name, attribute_name in (
            ("get_tracks", "start"),
            ("get_tracks", "end"),
            ("get_vias", "position"),
            ("get_footprints", "position"),
        ):
            getter = getattr(board, getter_name, None)
            if not callable(getter):
                continue
            for item in getter():
                vector = getattr(item, attribute_name, None)
                if vector is not None:
                    return vector
        return None

    def _normalize_points(
        self,
        points: Sequence[dict[str, float | int]],
        *,
        minimum: int,
        label: str,
    ) -> list[dict[str, float | int]]:
        normalized_points = []
        for index, point in enumerate(points, start=1):
            if "x_mm" not in point or "y_mm" not in point:
                raise KiCadLookupError(
                    f"Each point in the {label} must include x_mm and y_mm. "
                    f"Point {index} is incomplete."
                )

            x_mm = float(point["x_mm"])
            y_mm = float(point["y_mm"])
            normalized_points.append(
                {
                    "x_nm": self._millimeters_to_nanometers(x_mm),
                    "y_nm": self._millimeters_to_nanometers(y_mm),
                    "x_mm": x_mm,
                    "y_mm": y_mm,
                }
            )

        if len(normalized_points) < minimum:
            raise KiCadLookupError(
                f"The {label} requires at least {minimum} points."
            )

        return normalized_points

    def _normalize_optional_point(
        self,
        *,
        x_mm: float | None,
        y_mm: float | None,
        label: str,
    ) -> dict[str, float | int] | None:
        if x_mm is None and y_mm is None:
            return None
        if x_mm is None or y_mm is None:
            raise KiCadLookupError(f"{label} requires both x_mm and y_mm.")

        return {
            "x_nm": self._millimeters_to_nanometers(x_mm),
            "y_nm": self._millimeters_to_nanometers(y_mm),
            "x_mm": float(x_mm),
            "y_mm": float(y_mm),
        }

    def _validate_positive_measurement_mm(self, value_mm: float | int, *, field_name: str) -> int:
        value_nm = self._millimeters_to_nanometers(value_mm)
        if value_nm <= 0:
            raise KiCadLookupError(f"{field_name} must be greater than 0 mm.")
        return value_nm

    def _resolve_via_type(self, via_type: int | str) -> int:
        if isinstance(via_type, int):
            return via_type

        normalized = str(via_type).strip().lower()
        if normalized.isdigit():
            return int(normalized)

        resolved = VIA_TYPE_ALIASES.get(normalized)
        if resolved is None:
            raise KiCadLookupError(
                f"Via type {via_type!r} is not supported. Use an integer value or 'through'."
            )
        return resolved

    def _serialize_via_type(self, via_type: int) -> dict[str, Any]:
        return {
            "id": via_type,
            "name": VIA_TYPE_NAMES.get(via_type, str(via_type)),
        }

    def _resolve_board_item_by_id(
        self,
        board: Any,
        item_id: str,
        getter_names: Sequence[str],
        item_kind: str,
    ) -> Any:
        normalized_item_id = str(item_id).strip().lower()
        if not normalized_item_id:
            raise KiCadLookupError(f"A non-empty {item_kind} ID must be provided.")

        for getter_name in getter_names:
            getter = getattr(board, getter_name, None)
            if not callable(getter):
                continue

            for item in getter():
                serialized_id = serialize_identifier(getattr(item, "id", "")).strip().lower()
                if serialized_id == normalized_item_id:
                    return item

        raise KiCadLookupError(f"Unable to find {item_kind} with id {item_id!r}.")

    def _normalize_item_ids(self, item_ids: Sequence[str]) -> list[str]:
        normalized_item_ids = []
        seen = set()
        for item_id in item_ids:
            normalized_item_id = str(item_id).strip()
            if not normalized_item_id:
                continue
            if normalized_item_id in seen:
                continue
            seen.add(normalized_item_id)
            normalized_item_ids.append(normalized_item_id)

        if not normalized_item_ids:
            raise KiCadLookupError("At least one non-empty item ID must be provided.")

        return normalized_item_ids

    def _normalize_non_empty_strings(
        self,
        values: Sequence[str],
        *,
        field_name: str,
    ) -> list[str]:
        normalized_values = []
        seen = set()
        for value in values:
            normalized_value = str(value).strip()
            if not normalized_value or normalized_value in seen:
                continue
            seen.add(normalized_value)
            normalized_values.append(normalized_value)

        if not normalized_values:
            raise KiCadLookupError(f"At least one non-empty {field_name} value must be provided.")

        return normalized_values

    def _get_project_net_class_items(self, project: Any) -> list[Any]:
        get_net_classes = getattr(project, "get_net_classes", None)
        if not callable(get_net_classes):
            raise KiCadCapabilityError(
                "This KiCad binding does not expose project net classes on the active endpoint."
            )

        raw_net_classes = get_net_classes()
        if isinstance(raw_net_classes, dict):
            return list(raw_net_classes.values())
        if hasattr(raw_net_classes, "values") and callable(raw_net_classes.values):
            return list(raw_net_classes.values())
        return list(raw_net_classes)

    def _resolve_project_net_class(self, project: Any, netclass_name: str) -> Any:
        target = str(netclass_name).strip().lower()
        if not target:
            raise KiCadLookupError("A non-empty net class name must be provided.")

        for net_class in self._get_project_net_class_items(project):
            current_name = str(getattr(net_class, "name", "")).strip().lower()
            if current_name == target:
                return net_class

        raise KiCadLookupError(
            f"Net class {netclass_name!r} was not found in the active project."
        )

    def _make_polygon_like(
        self,
        board: Any,
        current: Any,
        points: Sequence[dict[str, float | int]],
    ) -> Any:
        if (
            KiCadPolygonWithHoles is not None
            and KiCadPolyLine is not None
            and KiCadPolyLineNode is not None
        ):
            polygon = KiCadPolygonWithHoles()
            outline = KiCadPolyLine()
            outline.closed = True
            append = getattr(outline, "append", None)
            if not callable(append):
                raise KiCadCapabilityError(
                    "The active KiCad polygon type does not expose append()."
                )

            for point in points:
                append(self._make_polyline_node(point["x_nm"], point["y_nm"]))

            polygon.outline = outline
            holes = getattr(current, "holes", None)
            if holes is not None:
                try:
                    polygon.holes.extend(list(holes))
                except Exception:
                    try:
                        polygon.holes = list(holes)
                    except Exception:
                        pass
            return polygon

        polygon = type(current)() if current is not None else type("PolygonLike", (), {})()
        polygon.outline = [
            self._construct_vector(board, point["x_nm"], point["y_nm"])
            for point in points
        ]
        if current is not None and hasattr(current, "holes"):
            try:
                polygon.holes = list(getattr(current, "holes", []))
            except Exception:
                pass
        return polygon

    def _make_polyline_node(self, x_nm: int, y_nm: int) -> Any:
        if KiCadPolyLineNode is None:
            raise KiCadCapabilityError("The active KiCad binding does not expose PolyLineNode.")

        from_xy = getattr(KiCadPolyLineNode, "from_xy", None)
        if callable(from_xy):
            return from_xy(x_nm, y_nm)

        raise KiCadCapabilityError(
            "The active KiCad binding does not expose PolyLineNode.from_xy()."
        )

    def _millimeters_to_nanometers(self, value_mm: float | int) -> int:
        return int(round(float(value_mm) * 1_000_000))

    def _resolve_board_origin_type(self, origin_type: int | str) -> int:
        if isinstance(origin_type, int):
            if origin_type in BOARD_ORIGIN_NAMES:
                return origin_type
            raise KiCadLookupError(
                f"Board origin type {origin_type!r} is not supported. Use 1/'grid' or 2/'drill'."
            )

        normalized = str(origin_type).strip().lower()
        resolved = BOARD_ORIGIN_ALIASES.get(normalized)
        if resolved is None:
            raise KiCadLookupError(
                f"Board origin type {origin_type!r} is not supported. Use 'grid' or 'drill'."
            )
        return resolved

    def _serialize_origin_type(self, origin_type: int) -> dict[str, Any]:
        return {
            "id": origin_type,
            "name": BOARD_ORIGIN_NAMES.get(origin_type, str(origin_type)),
        }

    def _serialize_board_origin(self, origin_type: int, origin: Any) -> dict[str, Any]:
        return {
            "type": self._serialize_origin_type(origin_type),
            "position": serialize_vector(origin),
        }

    def _get_origin_value(self, board: Any, origin_type: int) -> Any:
        get_origin = getattr(board, "get_origin", None)
        if not callable(get_origin):
            raise KiCadCapabilityError("The active KiCad board does not expose get_origin().")
        return get_origin(origin_type)

    def _get_title_block_info(self, board: Any) -> Any:
        get_title_block_info = getattr(board, "get_title_block_info", None)
        if not callable(get_title_block_info):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_title_block_info()."
            )
        return get_title_block_info()

    def _normalize_title_block_comments(
        self,
        comments: dict[str | int, str] | None,
    ) -> dict[int, str] | None:
        if comments is None:
            return None

        normalized: dict[int, str] = {}
        for raw_key, raw_value in comments.items():
            key_text = str(raw_key).strip()
            if not key_text.isdigit():
                raise KiCadLookupError(
                    f"Title block comment key {raw_key!r} is invalid. "
                    "Use integer slots 1 through 9."
                )

            key = int(key_text)
            if key < 1 or key > 9:
                raise KiCadLookupError(
                    f"Title block comment key {raw_key!r} is invalid. "
                    "Use integer slots 1 through 9."
                )

            normalized[key] = str(raw_value)

        return normalized

    def _is_copper_layer(self, board: Any, layer_id: int) -> bool:
        layer_info = serialize_layer(layer_id, board) or {}
        layer_name = str(layer_info.get("name", ""))
        return layer_name.lower().endswith(".cu")

    def _get_optional_layers(self, board: Any, method_name: str) -> list[dict[str, Any]] | None:
        method = getattr(board, method_name, None)
        if not callable(method):
            return None

        return [serialize_layer(layer, board) for layer in method()]

    def _append_document(
        self,
        documents: list[dict[str, Any]],
        seen: set[str],
        document: Any,
    ) -> None:
        serialized = serialize_document(document)
        if serialized is None:
            return

        key = "|".join(
            [
                str(serialized.get("type", "")),
                str(serialized.get("board_filename", "")),
                str(serialized.get("path", "")),
                str(serialized.get("project", {}).get("path", "")),
            ]
        )
        if key in seen:
            return

        seen.add(key)
        documents.append(serialized)

    def _translate_error(self, exc: Exception, *, default_message: str) -> dict[str, Any]:
        message = str(exc)

        if isinstance(exc, KiCadBindingUnavailableError):
            return {
                "ok": False,
                "message": str(exc),
                "error": message,
            }

        if isinstance(exc, KiCadCapabilityError | KiCadLookupError):
            return {
                "ok": False,
                "message": str(exc),
                "error": message,
            }

        if isinstance(exc, ApiError) and "no handler available" in message:
            return {
                "ok": False,
                "message": (
                    "Connected to KiCad IPC, but this endpoint does not expose PCB editor "
                    "document APIs. Open the PCB Editor and connect to its API endpoint. If the "
                    "MCP server is launched outside KiCad, set KICAD_API_SOCKET and "
                    "KICAD_API_TOKEN from the PCB editor/plugin environment."
                ),
                "error": message,
            }

        if isinstance(exc, ApiError) and self._is_retryable_board_write_message(message):
            return {
                "ok": False,
                "message": (
                    "KiCad did not answer before the IPC timeout or is still busy processing a "
                    "long-running board operation. Retry when the UI is idle, or increase "
                    "KIPILOT_KICAD_TIMEOUT_MS for larger boards."
                ),
                "error": message,
            }

        return {
            "ok": False,
            "message": default_message,
            "error": message,
        }
