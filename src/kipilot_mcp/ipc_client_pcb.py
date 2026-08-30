"""PCB-specific KiCad IPC client mixin."""

from __future__ import annotations

from .ipc_client_core import *  # noqa: F401,F403


class KiCadPcbClientMixin:
    """PCB-specific KiCad IPC client behavior."""

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
        reference: str | None = None,
        footprint_id: str | None = None,
    ) -> dict[str, Any]:
        """Return pads from the current PCB, with optional net, layer, and area filters."""

        return await self._run_board_read(
            lambda board: self._get_pads(
                board,
                net_name,
                layer,
                area,
                limit,
                reference=reference,
                footprint_id=footprint_id,
            ),
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

    async def get_dimensions(self, limit: int = 200) -> dict[str, Any]:
        """Return dimensions from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_board_items_from_method(
                board,
                method_name="get_dimensions",
                result_key="dimensions",
                limit=limit,
                serializer=serialize_dimension,
            ),
            default_message="Unable to read board dimensions through the IPC API.",
        )

    async def get_groups(self, limit: int = 200) -> dict[str, Any]:
        """Return groups from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_board_items_from_method(
                board,
                method_name="get_groups",
                result_key="groups",
                limit=limit,
                serializer=serialize_group,
            ),
            default_message="Unable to read board groups through the IPC API.",
        )

    async def get_reference_images(self, limit: int = 200) -> dict[str, Any]:
        """Return reference images from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_board_items_from_method(
                board,
                method_name="get_reference_images",
                result_key="reference_images",
                limit=limit,
                serializer=serialize_reference_image,
            ),
            default_message="Unable to read board reference images through the IPC API.",
        )

    async def get_barcodes(self, limit: int = 200) -> dict[str, Any]:
        """Return barcodes from the current PCB."""

        return await self._run_board_read(
            lambda board: self._get_board_items_from_method(
                board,
                method_name="get_barcodes",
                result_key="barcodes",
                limit=limit,
                serializer=serialize_barcode,
            ),
            default_message="Unable to read board barcodes through the IPC API.",
        )

    async def get_selection(self, limit: int = 200) -> dict[str, Any]:
        """Return the current board selection."""

        return await self._run_board_read(
            lambda board: self._get_selection(board, limit),
            default_message="Unable to read the current board selection through the IPC API.",
        )

    async def get_graphics_defaults(self) -> dict[str, Any]:
        """Return default graphics settings for board layer classes."""

        return await self._run_board_read(
            self._get_graphics_defaults,
            default_message="Unable to read board graphics defaults through the IPC API.",
        )

    async def get_editor_appearance_settings(self) -> dict[str, Any]:
        """Return current board editor appearance settings."""

        return await self._run_board_read(
            self._get_editor_appearance_settings,
            default_message="Unable to read board editor appearance settings through the IPC API.",
        )

    async def get_items(
        self,
        item_kinds: Sequence[str] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return board items across one or more item kinds."""

        return await self._run_board_read(
            lambda board: self._get_items(board, item_kinds=item_kinds, limit=limit),
            default_message="Unable to read board items through the IPC API.",
        )

    async def get_items_by_id(
        self,
        item_ids: Sequence[str],
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return board items resolved by KiCad item IDs."""

        return await self._run_board_read(
            lambda board: self._get_items_by_id(board, item_ids=item_ids, limit=limit),
            default_message="Unable to read board items by id through the IPC API.",
        )

    async def hit_test(
        self,
        *,
        item_id: str,
        x_mm: float,
        y_mm: float,
        tolerance_mm: float = 0.0,
    ) -> dict[str, Any]:
        """Run a hit test against one board item at a board-space position."""

        return await self._run_board_read(
            lambda board: self._hit_test(
                board,
                item_id=item_id,
                x_mm=x_mm,
                y_mm=y_mm,
                tolerance_mm=tolerance_mm,
            ),
            default_message="Unable to perform the requested board hit test through the IPC API.",
        )

    async def get_text_extents(self, *, text_item_id: str) -> dict[str, Any]:
        """Return the text extents box for one board text or text box item."""

        return await self._run_kicad(
            lambda kicad: self._get_text_extents(kicad, text_item_id=text_item_id),
            default_message="Unable to read text extents through the IPC API.",
        )

    async def get_text_as_shapes(self, *, text_item_ids: Sequence[str]) -> dict[str, Any]:
        """Return polygonal shapes representing one or more board text items."""

        return await self._run_kicad(
            lambda kicad: self._get_text_as_shapes(kicad, text_item_ids=text_item_ids),
            default_message="Unable to convert text to shapes through the IPC API.",
        )

    async def check_padstack_presence_on_layers(
        self,
        *,
        item_ids: Sequence[str],
        layers: Sequence[int | str],
    ) -> dict[str, Any]:
        """Check whether padstack-bearing items have copper on the requested layers."""

        return await self._run_board_read(
            lambda board: self._check_padstack_presence_on_layers(
                board,
                item_ids=item_ids,
                layers=layers,
            ),
            default_message="Unable to check padstack presence through the IPC API.",
        )

    async def get_pad_shapes_as_polygons(
        self,
        *,
        pad_ids: Sequence[str],
        layer: int | str,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Return polygonized pad outlines for one or more pads on one board layer."""

        return await self._run_board_read(
            lambda board: self._get_pad_shapes_as_polygons(
                board,
                pad_ids=pad_ids,
                layer=layer,
                limit=limit,
            ),
            default_message="Unable to read pad polygons through the IPC API.",
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

    async def add_to_selection(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Add one or more items to the current board selection."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._add_to_selection(
                board,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message="Unable to add the requested items to the board selection through the IPC API.",
            mutation_name="add_to_selection",
            dry_run=dry_run,
            use_commit=False,
        )

    async def remove_from_selection(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Remove one or more items from the current board selection."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._remove_from_selection(
                board,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message="Unable to remove the requested items from the board selection through the IPC API.",
            mutation_name="remove_from_selection",
            dry_run=dry_run,
            use_commit=False,
        )

    async def clear_selection(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Clear the current board selection."""

        return await self._run_board_write(
            self._clear_selection,
            default_message="Unable to clear the board selection through the IPC API.",
            mutation_name="clear_selection",
            dry_run=dry_run,
            use_commit=False,
        )

    async def get_board_layer_by_name(self, layer_name: str) -> dict[str, Any]:
        """Resolve a board layer by its canonical name."""

        return await self._run_board_read(
            lambda board: self._get_board_layer_by_name(board, layer_name),
            default_message="Unable to resolve the requested board layer through the IPC API.",
        )

    async def get_board_plot_settings(self) -> dict[str, Any]:
        """Return the board plot settings stored in the current PCB."""

        return await self._run_board_read(
            self._get_board_plot_settings,
            default_message="Unable to read board plot settings through the IPC API.",
        )

    async def set_board_plot_settings(
        self,
        plot_settings: dict[str, Any],
        *,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Update the board plot settings stored in the current PCB."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_board_plot_settings(
                board,
                plot_settings=plot_settings,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update board plot settings through the IPC API.",
            mutation_name="set_board_plot_settings",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def flip_board_items_by_id(
        self,
        item_ids: Sequence[str],
        direction: int | str = "left_right",
        *,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Flip one or more board items to the opposite side by their unique IDs."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._flip_board_items_by_id(
                board,
                item_ids=item_ids,
                direction=direction,
                dry_run=is_dry_run,
            ),
            default_message="Unable to flip the requested board items through the IPC API.",
            mutation_name="flip_board_items",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def set_editor_appearance_settings(
        self,
        *,
        inactive_layer_display: int | str | None = None,
        net_color_display: int | str | None = None,
        board_flip: int | str | None = None,
        ratsnest_display: int | str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Update board editor appearance settings."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._set_editor_appearance_settings(
                board,
                inactive_layer_display=inactive_layer_display,
                net_color_display=net_color_display,
                board_flip=board_flip,
                ratsnest_display=ratsnest_display,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update board editor appearance settings through the IPC API.",
            mutation_name="set_editor_appearance_settings",
            dry_run=dry_run,
            use_commit=False,
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

    async def flip_footprint(
        self,
        *,
        reference: str | None = None,
        footprint_id: str | None = None,
        target_layer: int | str | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Flip a footprint instance to the opposite board side."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._flip_footprint(
                board,
                reference=reference,
                footprint_id=footprint_id,
                target_layer=target_layer,
                dry_run=is_dry_run,
            ),
            default_message="Unable to flip the requested footprint through the IPC API.",
            mutation_name="flip_footprint",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_footprint_pad_net(
        self,
        *,
        net_name: str,
        reference: str | None = None,
        footprint_id: str | None = None,
        pad_number: str | None = None,
        pad_id: str | None = None,
        expected_current_net_name: str | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Reassign one footprint pad to a different board net."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._update_footprint_pad_net(
                board,
                reference=reference,
                footprint_id=footprint_id,
                pad_number=pad_number,
                pad_id=pad_id,
                net_name=net_name,
                expected_current_net_name=expected_current_net_name,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the requested footprint pad net through the IPC API.",
            mutation_name="update_footprint_pad_net",
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

    async def save_board_as(
        self,
        *,
        filename: str,
        overwrite: bool = False,
        include_project: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Save the current board to a new filename."""

        return await self._run_board_write(
            lambda board, is_dry_run: self._save_board_as(
                board,
                filename=filename,
                overwrite=overwrite,
                include_project=include_project,
                dry_run=is_dry_run,
            ),
            default_message="Unable to save the current board to a new file through the IPC API.",
            mutation_name="save_board_as",
            dry_run=dry_run,
            use_commit=False,
        )

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
            "footprints": [serialize_footprint(footprint, board) for footprint in footprints[:limit]],
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
            serialized = serialize_footprint(footprint, board)
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
        *,
        reference: str | None = None,
        footprint_id: str | None = None,
    ) -> dict[str, Any]:
        get_pads = getattr(board, "get_pads", None)
        if not callable(get_pads):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_pads()."
            )

        resolved_layer = resolve_layer_id(board, layer)
        resolved_net = resolve_net(board, net_name) if net_name else None
        area_filter = BoundingBoxFilter.from_query(area)
        resolved_footprint = None
        footprint_pad_ids: set[str] | None = None
        if reference is not None or footprint_id is not None:
            resolved_footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
            footprint_pad_ids = {
                serialize_identifier(getattr(pad, "id", "")).strip().lower()
                for pad in self._iter_footprint_pads(resolved_footprint)
                if serialize_identifier(getattr(pad, "id", "")).strip()
            }

        pads = list(get_pads())
        if footprint_pad_ids is not None:
            pads = [
                pad
                for pad in pads
                if serialize_identifier(getattr(pad, "id", "")).strip().lower() in footprint_pad_ids
            ]
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
                "reference": reference,
                "footprint_id": footprint_id,
            },
            "pads": [
                serialize_pad(pad, board, parent_footprint=resolved_footprint)
                for pad in pads[:limit]
            ],
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

    def _get_board_items_from_method(
        self,
        board: Any,
        *,
        method_name: str,
        result_key: str,
        limit: int,
        serializer: Callable[[Any, Any | None], dict[str, Any]],
    ) -> dict[str, Any]:
        getter = getattr(board, method_name, None)
        if not callable(getter):
            raise KiCadCapabilityError(
                f"The active KiCad board does not expose {method_name}()."
            )

        items = list(getter())

        return {
            "ok": True,
            "count": len(items),
            "limit": limit,
            result_key: [serializer(item, board) for item in items[:limit]],
        }

    def _get_selection(self, board: Any, limit: int) -> dict[str, Any]:
        get_selection = getattr(board, "get_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError("The active KiCad board does not expose get_selection().")

        selection = self._as_item_sequence(get_selection())
        return {
            "ok": True,
            "count": len(selection),
            "limit": limit,
            "selection": [serialize_item(item, board) for item in selection[:limit]],
        }

    def _get_board_layer_by_name(self, board: Any, layer_name: str) -> dict[str, Any]:
        get_layer_by_name = getattr(board, "get_layer_by_name", None)
        if not callable(get_layer_by_name):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_layer_by_name()."
            )

        layer_id = get_layer_by_name(layer_name)
        return {
            "ok": True,
            "board": self._serialize_board(board),
            "layer_name": str(layer_name),
            "layer": serialize_layer(layer_id, board),
        }

    def _get_board_plot_settings(self, board: Any) -> dict[str, Any]:
        get_plot_settings = getattr(board, "get_plot_settings", None)
        if not callable(get_plot_settings):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_plot_settings()."
            )

        return {
            "ok": True,
            "board": self._serialize_board(board),
            "plot_settings": serialize_board_plot_settings(get_plot_settings()),
        }

    def _set_board_plot_settings(
        self,
        board: Any,
        *,
        plot_settings: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        resolved_plot_settings = self._create_board_plot_settings(
            board, plot_settings
        )

        if not dry_run:
            set_plot_settings = getattr(board, "set_plot_settings", None)
            if not callable(set_plot_settings):
                raise KiCadCapabilityError(
                    "The active KiCad board does not expose set_plot_settings()."
                )
            set_plot_settings(resolved_plot_settings)

        return {
            "ok": True,
            "board": self._serialize_board(board),
            "dry_run": dry_run,
            "requested_plot_settings": plot_settings,
            "plot_settings": serialize_board_plot_settings(resolved_plot_settings),
        }

    def _create_board_plot_settings(
        self,
        board: Any,
        plot_settings: dict[str, Any],
    ) -> Any:
        if not isinstance(plot_settings, dict):
            raise KiCadLookupError("plot_settings must be an object when provided.")

        try:
            from kipy.board_jobs import PlotSettings as KiCadBoardPlotSettings
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose "
                "kipy.board_jobs.PlotSettings(). Board plot settings MCP tools require "
                "a newer binding build with board plot settings support."
            ) from exc

        supported_fields = {
            "layers",
            "common_layers",
            "color_theme",
            "drawing_sheet",
            "variant",
            "mirror",
            "black_and_white",
            "negative",
            "scale",
            "sketch_pads_on_fab_layers",
            "hide_dnp_footprints_on_fab_layers",
            "sketch_dnp_footprints_on_fab_layers",
            "crossout_dnp_footprints_on_fab_layers",
            "plot_footprint_values",
            "plot_reference_designators",
            "plot_drawing_sheet",
            "subtract_solder_mask_from_silk",
            "plot_pad_numbers",
            "drill_marks",
            "use_drill_origin",
            "check_zones_before_plot",
        }
        unknown_fields = sorted(set(plot_settings) - supported_fields)
        if unknown_fields:
            unknown_list = ", ".join(unknown_fields)
            raise KiCadLookupError(f"Unsupported plot_settings fields: {unknown_list}.")

        result = KiCadBoardPlotSettings()

        for field_name in ("color_theme", "drawing_sheet", "variant"):
            if field_name in plot_settings and plot_settings[field_name] is not None:
                setattr(result, field_name, str(plot_settings[field_name]))

        for field_name in (
            "mirror",
            "black_and_white",
            "negative",
            "sketch_pads_on_fab_layers",
            "hide_dnp_footprints_on_fab_layers",
            "sketch_dnp_footprints_on_fab_layers",
            "crossout_dnp_footprints_on_fab_layers",
            "plot_footprint_values",
            "plot_reference_designators",
            "plot_drawing_sheet",
            "subtract_solder_mask_from_silk",
            "plot_pad_numbers",
            "use_drill_origin",
            "check_zones_before_plot",
        ):
            if field_name not in plot_settings or plot_settings[field_name] is None:
                continue
            field_value = plot_settings[field_name]
            if not isinstance(field_value, bool):
                raise KiCadLookupError(f"plot_settings.{field_name} must be a boolean.")
            setattr(result, field_name, field_value)

        if "scale" in plot_settings and plot_settings["scale"] is not None:
            scale = plot_settings["scale"]
            if isinstance(scale, bool) or not isinstance(scale, (int, float)):
                raise KiCadLookupError("plot_settings.scale must be a number.")
            result.scale = float(scale)

        if "drill_marks" in plot_settings and plot_settings["drill_marks"] is not None:
            result.drill_marks = self._coerce_enum_value(
                plot_settings["drill_marks"],
                field_name="plot_settings.drill_marks",
            )

        if "layers" in plot_settings and plot_settings["layers"] is not None:
            raw_layers = plot_settings["layers"]
            if isinstance(raw_layers, (str, bytes)) or not isinstance(raw_layers, Sequence):
                raise KiCadLookupError("plot_settings.layers must be a list of layer ids or names.")
            resolved_layers: list[int] = []
            for raw_layer in raw_layers:
                if isinstance(raw_layer, bool):
                    raise KiCadLookupError(
                        "plot_settings.layers entries must be layer ids or names."
                    )
                if isinstance(raw_layer, int):
                    resolved_layers.append(raw_layer)
                    continue
                get_layer_by_name = getattr(board, "get_layer_by_name", None)
                if not callable(get_layer_by_name):
                    raise KiCadCapabilityError(
                        "The active KiCad board does not expose get_layer_by_name(), "
                        "so string layer names cannot be resolved."
                    )
                resolved_layers.append(get_layer_by_name(str(raw_layer)))
            result.layers = resolved_layers

        if "common_layers" in plot_settings and plot_settings["common_layers"] is not None:
            raw_layers = plot_settings["common_layers"]
            if isinstance(raw_layers, (str, bytes)) or not isinstance(raw_layers, Sequence):
                raise KiCadLookupError("plot_settings.common_layers must be a list.")
            result.common_layers = [layer for layer in raw_layers if isinstance(layer, int)]

        return result

    def _coerce_flip_direction(self, direction: int | str) -> int:
        if isinstance(direction, int):
            return direction

        try:
            from kipy.proto.board import board_commands_pb2 as board_commands
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose "
                "kipy.proto.board.board_commands_pb2. Board flip MCP tools require a "
                "newer binding build with board flip support."
            ) from exc

        normalized_direction = str(direction).strip().lower()
        supported_directions = {
            "left_right": board_commands.BFD_LEFT_RIGHT,
            "top_bottom": board_commands.BFD_TOP_BOTTOM,
        }
        if normalized_direction not in supported_directions:
            raise KiCadLookupError(
                f"Unsupported flip direction {direction!r}. "
                "Supported directions: left_right, top_bottom."
            )
        return supported_directions[normalized_direction]

    def _flip_board_items_by_id(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        direction: int | str,
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_item_ids = self._normalize_item_ids(item_ids)
        flip_items_by_id = getattr(board, "flip_items_by_id", None)
        if not callable(flip_items_by_id):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose flip_items_by_id()."
            )

        resolved_direction = self._coerce_flip_direction(direction)

        try:
            from kipy.proto.common.types import KIID as KiCadKIID
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose "
                "kipy.proto.common.types.KIID. Board flip MCP tools require a newer "
                "binding build with board flip support."
            ) from exc

        lookup_ids: list[Any] = []
        for normalized_item_id in normalized_item_ids:
            lookup_id = KiCadKIID()
            lookup_id.value = normalized_item_id
            lookup_ids.append(lookup_id)

        if dry_run:
            return {
                "ok": True,
                "board": self._serialize_board(board),
                "dry_run": True,
                "requested_item_ids": normalized_item_ids,
                "direction": resolved_direction,
                "count": 0,
                "flipped_items": [],
            }

        flipped_items = list(flip_items_by_id(lookup_ids, direction=resolved_direction))
        return {
            "ok": True,
            "board": self._serialize_board(board),
            "requested_item_ids": normalized_item_ids,
            "direction": resolved_direction,
            "count": len(flipped_items),
            "flipped_items": [serialize_item(item, board) for item in flipped_items],
        }

    def _get_graphics_defaults(self, board: Any) -> dict[str, Any]:
        get_graphics_defaults = getattr(board, "get_graphics_defaults", None)
        if not callable(get_graphics_defaults):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_graphics_defaults()."
            )

        defaults_by_layer = get_graphics_defaults()
        serialized_defaults = [
            serialize_graphics_default(defaults)
            for _, defaults in sorted(defaults_by_layer.items(), key=lambda entry: int(entry[0]))
        ]
        return {
            "ok": True,
            "count": len(serialized_defaults),
            "graphics_defaults": serialized_defaults,
        }

    def _get_editor_appearance_settings(self, board: Any) -> dict[str, Any]:
        get_editor_appearance_settings = getattr(board, "get_editor_appearance_settings", None)
        if not callable(get_editor_appearance_settings):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_editor_appearance_settings()."
            )

        return {
            "ok": True,
            "appearance_settings": serialize_editor_appearance_settings(
                get_editor_appearance_settings()
            ),
        }

    def _get_items(
        self,
        board: Any,
        *,
        item_kinds: Sequence[str] | None,
        limit: int,
    ) -> dict[str, Any]:
        getter_names = self._resolve_board_item_getter_names(item_kinds)
        items = self._collect_board_items(board, getter_names)
        return {
            "ok": True,
            "count": len(items),
            "limit": limit,
            "item_kinds": list(item_kinds) if item_kinds is not None else None,
            "items": [serialize_item(item, board) for item in items[:limit]],
        }

    def _get_items_by_id(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        limit: int,
    ) -> dict[str, Any]:
        resolved_item_ids = self._normalize_item_ids(item_ids)
        items = self._resolve_board_items_by_ids(board, resolved_item_ids)
        return {
            "ok": True,
            "count": len(items),
            "limit": limit,
            "item_ids": resolved_item_ids,
            "items": [serialize_item(item, board) for item in items[:limit]],
        }

    def _hit_test(
        self,
        board: Any,
        *,
        item_id: str,
        x_mm: float,
        y_mm: float,
        tolerance_mm: float,
    ) -> dict[str, Any]:
        hit_test = getattr(board, "hit_test", None)
        if not callable(hit_test):
            raise KiCadCapabilityError("The active KiCad board does not expose hit_test().")

        item = self._resolve_board_items_by_ids(board, [item_id])[0]
        x_nm = self._millimeters_to_nanometers(x_mm)
        y_nm = self._millimeters_to_nanometers(y_mm)
        tolerance_nm = max(0, self._millimeters_to_nanometers(tolerance_mm))
        position = self._construct_vector(board, x_nm, y_nm)
        return {
            "ok": True,
            "item": serialize_item(item, board),
            "position": {
                "x_nm": x_nm,
                "y_nm": y_nm,
                "x_mm": float(x_mm),
                "y_mm": float(y_mm),
            },
            "tolerance_nm": tolerance_nm,
            "tolerance_mm": float(tolerance_mm),
            "hit": bool(hit_test(item, position, tolerance=tolerance_nm)),
        }

    def _get_text_extents(self, kicad: Any, *, text_item_id: str) -> dict[str, Any]:
        get_text_extents = getattr(kicad, "get_text_extents", None)
        if not callable(get_text_extents):
            raise KiCadCapabilityError("The active KiCad binding does not expose get_text_extents().")

        board = kicad.get_board()
        text_item = self._resolve_board_item_by_id(board, text_item_id, ("get_text",), "text item")
        text_input = self._coerce_text_item_for_kicad(text_item)
        return {
            "ok": True,
            "item": serialize_item(text_item, board),
            "bounding_box": serialize_box(get_text_extents(text_input)),
        }

    def _get_text_as_shapes(self, kicad: Any, *, text_item_ids: Sequence[str]) -> dict[str, Any]:
        get_text_as_shapes = getattr(kicad, "get_text_as_shapes", None)
        if not callable(get_text_as_shapes):
            raise KiCadCapabilityError(
                "The active KiCad binding does not expose get_text_as_shapes()."
            )

        board = kicad.get_board()
        resolved_item_ids = self._normalize_item_ids(text_item_ids)
        text_items = [
            self._resolve_board_item_by_id(board, item_id, ("get_text",), "text item")
            for item_id in resolved_item_ids
        ]
        text_inputs = [self._coerce_text_item_for_kicad(item) for item in text_items]
        compound_shapes = list(get_text_as_shapes(text_inputs))

        items = []
        for text_item, compound_shape in zip(text_items, compound_shapes):
            shapes = self._extract_graphic_shapes(compound_shape)
            items.append(
                {
                    "item": serialize_item(text_item, board),
                    "shape_count": len(shapes),
                    "shapes": [serialize_shape(shape, board) for shape in shapes],
                }
            )

        return {
            "ok": True,
            "count": len(items),
            "item_ids": resolved_item_ids,
            "items": items,
        }

    def _check_padstack_presence_on_layers(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        layers: Sequence[int | str],
    ) -> dict[str, Any]:
        check_padstack_presence_on_layers = getattr(board, "check_padstack_presence_on_layers", None)
        if not callable(check_padstack_presence_on_layers):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose check_padstack_presence_on_layers()."
            )

        resolved_item_ids = self._normalize_item_ids(item_ids)
        resolved_items = self._resolve_board_items_by_ids(board, resolved_item_ids)
        resolved_layers = [
            resolved_layer
            for layer in layers
            if (resolved_layer := resolve_layer_id(board, layer)) is not None
        ]
        if not resolved_layers:
            raise KiCadLookupError("At least one valid layer must be provided.")

        presence_map = check_padstack_presence_on_layers(resolved_items, resolved_layers)
        items = []
        for item in resolved_items:
            layer_presence = presence_map.get(item, {})
            items.append(
                {
                    "item": serialize_item(item, board),
                    "layers": [
                        {
                            "layer": serialize_layer(layer_id, board),
                            "present": bool(layer_presence.get(layer_id, False)),
                        }
                        for layer_id in resolved_layers
                    ],
                }
            )

        return {
            "ok": True,
            "count": len(items),
            "item_ids": resolved_item_ids,
            "resolved_layers": [serialize_layer(layer_id, board) for layer_id in resolved_layers],
            "items": items,
        }

    def _get_pad_shapes_as_polygons(
        self,
        board: Any,
        *,
        pad_ids: Sequence[str],
        layer: int | str,
        limit: int,
    ) -> dict[str, Any]:
        get_pad_shapes_as_polygons = getattr(board, "get_pad_shapes_as_polygons", None)
        if not callable(get_pad_shapes_as_polygons):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_pad_shapes_as_polygons()."
            )

        resolved_layer = resolve_layer_id(board, layer)
        if resolved_layer is None:
            raise KiCadLookupError(f"Unable to resolve board layer {layer!r}.")

        resolved_pad_ids = self._normalize_item_ids(pad_ids)
        resolved_pads = [
            self._resolve_board_item_by_id(board, pad_id, ("get_pads",), "pad")
            for pad_id in resolved_pad_ids
        ]
        polygons = self._as_item_sequence(get_pad_shapes_as_polygons(resolved_pads, resolved_layer))

        items = []
        for pad, polygon in zip(resolved_pads, polygons):
            items.append(
                {
                    "pad": serialize_pad(pad, board),
                    "polygon": serialize_polygon(polygon),
                }
            )

        return {
            "ok": True,
            "count": len(items),
            "limit": limit,
            "pad_ids": resolved_pad_ids,
            "resolved_layer": serialize_layer(resolved_layer, board),
            "items": items[:limit],
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

    def _flip_footprint(
        self,
        board: Any,
        *,
        reference: str | None,
        footprint_id: str | None,
        target_layer: int | str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
        current_layer = getattr(footprint, "layer", None)
        resolved_target_layer = self._resolve_target_footprint_layer(
            board,
            current_layer=current_layer,
            target_layer=target_layer,
            item_label="Footprint",
        )
        did_flip = current_layer != resolved_target_layer

        return self._update_footprint(
            board,
            reference=reference,
            footprint_id=footprint_id,
            dry_run=dry_run,
            mutate=lambda updated_footprint: self._apply_footprint_side_flip(
                board,
                updated_footprint,
                target_layer=resolved_target_layer,
            ),
            details={
                "previous_layer": serialize_layer(current_layer, board),
                "target_layer": serialize_layer(resolved_target_layer, board),
                "mirrored": did_flip,
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
                "layer",
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
        has_layer = "layer" in update
        if not has_position and not has_orientation and not has_layer:
            raise KiCadLookupError(
                f"Item update {index} must include x_mm/y_mm, orientation_degrees, and/or layer."
            )

        footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
        previous_item = serialize_footprint(footprint, board)
        updated_footprint = self._clone_item(footprint)
        requested_changes: dict[str, Any] = {
            "position": None,
            "orientation_degrees": None,
            "layer": None,
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

        resolved_layer = None
        if has_layer:
            raw_layer = update.get("layer")
            if raw_layer is None:
                raise KiCadLookupError(
                    f"Item update {index} must include a non-empty layer for footprint layer changes."
                )
            resolved_layer = self._resolve_target_footprint_layer(
                board,
                current_layer=getattr(footprint, "layer", None),
                target_layer=raw_layer,
                item_label=f"Item update {index}",
            )
            requested_changes["layer"] = serialize_layer(resolved_layer, board)

        if resolved_layer is not None:
            self._apply_footprint_side_flip(
                board,
                updated_footprint,
                target_layer=resolved_layer,
            )

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

    def _add_to_selection(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        requested_item_ids = self._normalize_item_ids(item_ids)
        get_selection = getattr(board, "get_selection", None)
        add_to_selection = getattr(board, "add_to_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError("The active KiCad board does not expose get_selection().")
        if not callable(add_to_selection) and not dry_run:
            raise KiCadCapabilityError("The active KiCad board does not expose add_to_selection().")

        previous_selection = self._as_item_sequence(get_selection())
        requested_items = self._resolve_board_items_by_ids(board, requested_item_ids)
        preview_selection = self._merge_board_items(previous_selection, requested_items)

        if dry_run:
            applied_selection = preview_selection
        else:
            try:
                applied_selection = self._as_item_sequence(add_to_selection(requested_items))
            except TypeError:
                if len(requested_items) != 1:
                    raise
                applied_selection = self._as_item_sequence(add_to_selection(requested_items[0]))
            if not applied_selection:
                applied_selection = self._as_item_sequence(get_selection())

        return {
            "board": self._serialize_board(board),
            "requested_item_ids": requested_item_ids,
            "previous_count": len(previous_selection),
            "count": len(applied_selection),
            "selection": [serialize_item(item, board) for item in applied_selection],
        }

    def _remove_from_selection(
        self,
        board: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        requested_item_ids = self._normalize_item_ids(item_ids)
        get_selection = getattr(board, "get_selection", None)
        remove_from_selection = getattr(board, "remove_from_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError("The active KiCad board does not expose get_selection().")
        if not callable(remove_from_selection) and not dry_run:
            raise KiCadCapabilityError(
                "The active KiCad board does not expose remove_from_selection()."
            )

        previous_selection = self._as_item_sequence(get_selection())
        requested_id_set = {item_id.lower() for item_id in requested_item_ids}
        preview_selection = [
            item
            for item in previous_selection
            if serialize_identifier(getattr(item, "id", "")).lower() not in requested_id_set
        ]

        if dry_run:
            applied_selection = preview_selection
        else:
            requested_items = self._resolve_board_items_by_ids(board, requested_item_ids)
            try:
                applied_selection = self._as_item_sequence(remove_from_selection(requested_items))
            except TypeError:
                if len(requested_items) != 1:
                    raise
                applied_selection = self._as_item_sequence(remove_from_selection(requested_items[0]))
            if not applied_selection and preview_selection:
                applied_selection = self._as_item_sequence(get_selection())

        return {
            "board": self._serialize_board(board),
            "requested_item_ids": requested_item_ids,
            "previous_count": len(previous_selection),
            "count": len(applied_selection),
            "selection": [serialize_item(item, board) for item in applied_selection],
        }

    def _clear_selection(self, board: Any, dry_run: bool) -> dict[str, Any]:
        get_selection = getattr(board, "get_selection", None)
        clear_selection = getattr(board, "clear_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError("The active KiCad board does not expose get_selection().")
        if not callable(clear_selection) and not dry_run:
            raise KiCadCapabilityError("The active KiCad board does not expose clear_selection().")

        previous_selection = self._as_item_sequence(get_selection())
        if not dry_run:
            clear_selection()

        return {
            "board": self._serialize_board(board),
            "previous_count": len(previous_selection),
            "count": 0,
            "selection": [],
        }

    def _set_editor_appearance_settings(
        self,
        board: Any,
        *,
        inactive_layer_display: int | str | None,
        net_color_display: int | str | None,
        board_flip: int | str | None,
        ratsnest_display: int | str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        get_editor_appearance_settings = getattr(board, "get_editor_appearance_settings", None)
        set_editor_appearance_settings = getattr(board, "set_editor_appearance_settings", None)
        if not callable(get_editor_appearance_settings):
            raise KiCadCapabilityError(
                "The active KiCad board does not expose get_editor_appearance_settings()."
            )
        if not callable(set_editor_appearance_settings) and not dry_run:
            raise KiCadCapabilityError(
                "The active KiCad board does not expose set_editor_appearance_settings()."
            )

        requested_changes = {
            key: value
            for key, value in {
                "inactive_layer_display": self._coerce_enum_value(
                    inactive_layer_display,
                    field_name="inactive_layer_display",
                ),
                "net_color_display": self._coerce_enum_value(
                    net_color_display,
                    field_name="net_color_display",
                ),
                "board_flip": self._coerce_enum_value(board_flip, field_name="board_flip"),
                "ratsnest_display": self._coerce_enum_value(
                    ratsnest_display,
                    field_name="ratsnest_display",
                ),
            }.items()
            if value is not None
        }
        if not requested_changes:
            raise KiCadLookupError("At least one editor appearance setting must be provided.")

        previous_settings = get_editor_appearance_settings()
        updated_settings = self._clone_settings_like(
            previous_settings,
            (
                "inactive_layer_display",
                "net_color_display",
                "board_flip",
                "ratsnest_display",
            ),
        )
        for key, value in requested_changes.items():
            setattr(updated_settings, key, value)

        if not dry_run:
            set_editor_appearance_settings(updated_settings)

        applied_settings = updated_settings if dry_run else get_editor_appearance_settings()
        return {
            "board": self._serialize_board(board),
            "previous_appearance_settings": serialize_editor_appearance_settings(previous_settings),
            "appearance_settings": serialize_editor_appearance_settings(applied_settings),
            "requested_changes": requested_changes,
        }

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

    def _save_board_as(
        self,
        board: Any,
        *,
        filename: str,
        overwrite: bool,
        include_project: bool,
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_filename = str(filename).strip()
        if not normalized_filename:
            raise KiCadLookupError("filename must be a non-empty path.")

        if not dry_run:
            save_as = getattr(board, "save_as", None)
            if not callable(save_as):
                raise KiCadCapabilityError("The active KiCad board does not expose save_as().")
            try:
                save_as(normalized_filename, overwrite=overwrite, include_project=include_project)
            except TypeError:
                save_as(normalized_filename, overwrite, include_project)

        return {
            "board": self._serialize_board(board),
            "saved_filename": normalized_filename,
            "overwrite": overwrite,
            "include_project": include_project,
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
        previous_footprint = serialize_footprint(footprint, board)
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
            "footprint": serialize_footprint(applied_footprint, board),
            **details,
        }

    def _update_footprint_pad_net(
        self,
        board: Any,
        *,
        reference: str | None,
        footprint_id: str | None,
        pad_number: str | None,
        pad_id: str | None,
        net_name: str,
        expected_current_net_name: str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        footprint = resolve_footprint(board, reference=reference, footprint_id=footprint_id)
        previous_footprint = serialize_footprint(footprint, board)
        previous_pad = self._resolve_footprint_pad(
            footprint,
            pad_number=pad_number,
            pad_id=pad_id,
            item_label="Footprint pad",
        )
        current_net_name = str(getattr(getattr(previous_pad, "net", None), "name", "")).strip()
        if (
            expected_current_net_name is not None
            and current_net_name.strip().lower() != expected_current_net_name.strip().lower()
        ):
            raise KiCadLookupError(
                "Footprint pad current net did not match the expected value. "
                f"Expected {expected_current_net_name!r}, got {current_net_name!r}."
            )

        resolved_net = resolve_net(board, net_name)
        updated_footprint = self._clone_item(footprint)
        updated_pad = self._resolve_footprint_pad(
            updated_footprint,
            pad_number=pad_number,
            pad_id=pad_id,
            item_label="Updated footprint pad",
        )
        self._set_pad_net(updated_pad, resolved_net)

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

        applied_pad = self._resolve_footprint_pad(
            applied_footprint,
            pad_number=pad_number,
            pad_id=pad_id,
            item_label="Applied footprint pad",
        )
        return {
            "board": {
                "name": getattr(board, "name", None),
                "document": serialize_document(getattr(board, "document", None)),
            },
            "target": {
                "reference": reference,
                "footprint_id": footprint_id,
                "pad_number": pad_number,
                "pad_id": pad_id,
            },
            "previous_footprint": previous_footprint,
            "footprint": serialize_footprint(applied_footprint, board),
            "previous_pad": serialize_pad(previous_pad, board, parent_footprint=footprint),
            "pad": serialize_pad(applied_pad, board, parent_footprint=applied_footprint),
            "requested_changes": {
                "net": serialize_net(resolved_net),
                "expected_current_net_name": expected_current_net_name,
            },
        }

    def _resolve_footprint_pad(
        self,
        footprint: Any,
        *,
        pad_number: str | None,
        pad_id: str | None,
        item_label: str,
    ) -> Any:
        normalized_number = str(pad_number).strip() if pad_number is not None else ""
        normalized_id = str(pad_id).strip().lower() if pad_id is not None else ""
        if not normalized_number and not normalized_id:
            raise KiCadLookupError(
                f"{item_label} lookup requires either pad_number or pad_id."
            )

        definition = getattr(footprint, "definition", None)
        if definition is None:
            raise KiCadLookupError(
                f"{item_label} lookup is unavailable because the target footprint has no definition."
            )

        matches = []
        for item in self._iter_footprint_pads(footprint):
            current_id = serialize_identifier(getattr(item, "id", "")).strip().lower()
            current_number = str(getattr(item, "number", "")).strip()
            if normalized_id and current_id != normalized_id:
                continue
            if normalized_number and current_number != normalized_number:
                continue
            matches.append(item)

        if not matches:
            target = pad_id if normalized_id else pad_number
            raise KiCadLookupError(
                f"{item_label} {target!r} was not found on the target footprint."
            )
        if len(matches) > 1:
            target = pad_id if normalized_id else pad_number
            raise KiCadLookupError(
                f"{item_label} lookup for {target!r} matched multiple pads; use pad_id to disambiguate."
            )
        return matches[0]

    def _iter_footprint_pads(self, footprint: Any) -> list[Any]:
        definition = getattr(footprint, "definition", None)
        if definition is None:
            return []

        return [
            item
            for item in list(getattr(definition, "items", ()) or ())
            if self._is_pad_like(item)
        ]

    def _set_pad_net(self, pad: Any, net: Any) -> None:
        try:
            pad.net = net
            return
        except Exception:  # noqa: BLE001
            pass

        proto = getattr(pad, "_proto", None)
        if proto is None:
            proto = getattr(pad, "proto", None)
        proto_net = getattr(proto, "net", None) if proto is not None else None
        net_proto = getattr(net, "proto", None)
        copy_from = getattr(proto_net, "CopyFrom", None)
        if callable(copy_from) and net_proto is not None:
            copy_from(net_proto)
            return

        raise KiCadCapabilityError("Footprint pad items must expose a mutable net.")

    def _resolve_target_footprint_layer(
        self,
        board: Any,
        *,
        current_layer: int | None,
        target_layer: int | str | None,
        item_label: str,
    ) -> int:
        front_layer = resolve_layer_id(board, "F.Cu")
        back_layer = resolve_layer_id(board, "B.Cu")
        valid_layers = {front_layer, back_layer}

        if current_layer not in valid_layers:
            current_layer_info = serialize_layer(current_layer, board)
            raise KiCadLookupError(
                f"{item_label} must be on F.Cu or B.Cu to change board side. "
                f"Current layer: {current_layer_info or current_layer!r}."
            )

        if target_layer is None:
            return back_layer if current_layer == front_layer else front_layer

        resolved_layer = resolve_layer_id(board, target_layer)
        if resolved_layer not in valid_layers:
            raise KiCadLookupError(
                f"{item_label} layer changes only support F.Cu or B.Cu. "
                f"Got {target_layer!r}."
            )

        return resolved_layer

    def _apply_footprint_side_flip(
        self,
        board: Any,
        footprint: Any,
        *,
        target_layer: int,
    ) -> bool:
        current_layer = getattr(footprint, "layer", None)
        if current_layer == target_layer:
            return False

        anchor = getattr(footprint, "position", None)
        if anchor is None or getattr(anchor, "x", None) is None or getattr(anchor, "y", None) is None:
            raise KiCadCapabilityError(
                "The target footprint does not expose a mutable anchor position."
            )

        current_orientation = getattr(footprint, "orientation", None)
        if current_orientation is not None:
            flipped_orientation = self._make_angle_like(
                current_orientation,
                -self._read_angle_degrees(current_orientation, item_label="Footprint orientation"),
                normalize_180=True,
            )
            self._set_footprint_orientation_direct(footprint, flipped_orientation)

        footprint.layer = target_layer
        self._flip_footprint_fields(board, footprint, anchor)

        definition = getattr(footprint, "definition", None)
        if definition is None:
            return True

        for item in list(getattr(definition, "items", ()) or ()):
            self._flip_footprint_child_item(board, item, anchor)

        return True

    def _flip_footprint_fields(self, board: Any, footprint: Any, anchor: Any) -> None:
        for field_name in (
            "reference_field",
            "value_field",
            "datasheet_field",
            "description_field",
        ):
            field = getattr(footprint, field_name, None)
            text_item = getattr(field, "text", None)
            if text_item is None:
                continue
            self._flip_board_text_item(board, text_item, anchor)

    def _flip_footprint_child_item(self, board: Any, item: Any, anchor: Any) -> None:
        item_type_name = type(item).__name__

        if item_type_name == "Field":
            self._flip_board_text_item(board, getattr(item, "text", None), anchor)
            return

        if self._is_board_text_box_like(item):
            self._flip_board_text_box_item(board, item, anchor)
            return

        if self._is_board_text_like(item):
            self._flip_board_text_item(board, item, anchor)
            return

        if self._is_board_shape_like(item):
            self._flip_board_shape(board, item, anchor)
            return

        if item_type_name == "BoardShape":
            self._flip_board_shape(board, item, anchor)
            return

        if item_type_name == "Zone":
            self._flip_zone(board, item, anchor)
            return

        if self._is_pad_like(item):
            self._flip_pad(board, item, anchor)
            return

        if item_type_name == "Barcode":
            self._flip_barcode(board, item, anchor)
            return

        if item_type_name == "ReferenceImage":
            self._flip_reference_image(board, item, anchor)
            return

        if item_type_name == "Footprint3DModel":
            return

        raise KiCadCapabilityError(
            "Footprint flipping is not implemented for "
            f"{item_type_name}."
        )

    def _flip_pad(self, board: Any, pad: Any, anchor: Any) -> None:
        position = getattr(pad, "position", None)
        if position is None:
            raise KiCadCapabilityError("Footprint pad items must expose a mutable position.")

        pad.position = self._mirror_vector_horizontally(position, anchor)

        padstack = getattr(pad, "padstack", None)
        if padstack is None:
            raise KiCadCapabilityError("Footprint pad items must expose a mutable padstack.")

        self._flip_padstack(
            board,
            padstack,
            local_origin=self._make_vector_like(position, 0, 0),
        )

    def _flip_padstack(self, board: Any, padstack: Any, *, local_origin: Any) -> None:
        layers = list(getattr(padstack, "layers", ()) or ())
        if layers:
            padstack.layers = [self._flip_layer_id(board, layer) for layer in layers]

        drill = getattr(padstack, "drill", None)
        if drill is not None:
            start_layer = getattr(drill, "start_layer", None)
            if start_layer is not None:
                drill.start_layer = self._flip_layer_id(board, start_layer)

            end_layer = getattr(drill, "end_layer", None)
            if end_layer is not None:
                drill.end_layer = self._flip_layer_id(board, end_layer)

        current_angle = getattr(padstack, "angle", None)
        if current_angle is not None:
            padstack.angle = self._make_angle_like(
                current_angle,
                180.0 - self._read_angle_degrees(current_angle, item_label="Pad orientation"),
            )

        for copper_layer in list(getattr(padstack, "copper_layers", ()) or ()):
            copper_layer.layer = self._flip_layer_id(board, getattr(copper_layer, "layer", None))

            offset = getattr(copper_layer, "offset", None)
            if offset is not None:
                copper_layer.offset = self._make_vector_like(offset, -int(offset.x), int(offset.y))

            trapezoid_delta = getattr(copper_layer, "trapezoid_delta", None)
            if trapezoid_delta is not None:
                copper_layer.trapezoid_delta = self._make_vector_like(
                    trapezoid_delta,
                    -int(trapezoid_delta.x),
                    int(trapezoid_delta.y),
                )

            chamfered_corners = getattr(copper_layer, "chamfered_corners", None)
            if chamfered_corners is not None:
                top_left = bool(getattr(chamfered_corners, "top_left", False))
                top_right = bool(getattr(chamfered_corners, "top_right", False))
                bottom_left = bool(getattr(chamfered_corners, "bottom_left", False))
                bottom_right = bool(getattr(chamfered_corners, "bottom_right", False))
                chamfered_corners.top_left = top_right
                chamfered_corners.top_right = top_left
                chamfered_corners.bottom_left = bottom_right
                chamfered_corners.bottom_right = bottom_left

            for custom_shape in list(getattr(copper_layer, "custom_shapes", ()) or ()):
                self._flip_board_shape(board, custom_shape, local_origin)

        self._swap_padstack_outer_layers(padstack)

    def _swap_padstack_outer_layers(self, padstack: Any) -> None:
        proto = getattr(padstack, "_proto", None)
        if proto is None:
            return

        front_outer_layers = getattr(proto, "front_outer_layers", None)
        back_outer_layers = getattr(proto, "back_outer_layers", None)
        if front_outer_layers is None or back_outer_layers is None:
            return

        front_copy = front_outer_layers.__class__()
        back_copy = back_outer_layers.__class__()
        front_copy.CopyFrom(front_outer_layers)
        back_copy.CopyFrom(back_outer_layers)
        front_outer_layers.CopyFrom(back_copy)
        back_outer_layers.CopyFrom(front_copy)

    def _flip_board_text_item(self, board: Any, text_item: Any, anchor: Any) -> None:
        if text_item is None:
            return

        position = getattr(text_item, "position", None)
        if position is not None:
            text_item.position = self._mirror_vector_horizontally(position, anchor)

        current_layer = getattr(text_item, "layer", None)
        flipped_layer = self._flip_layer_id(board, current_layer)
        if current_layer is not None:
            text_item.layer = flipped_layer

        attributes = getattr(text_item, "attributes", None)
        if attributes is None:
            return

        angle = getattr(attributes, "angle", None)
        if angle is not None:
            attributes.angle = self._normalize_degrees(-float(angle))

        if flipped_layer != current_layer and hasattr(attributes, "mirrored"):
            attributes.mirrored = not bool(getattr(attributes, "mirrored", False))

    def _flip_board_text_box_item(self, board: Any, text_box: Any, anchor: Any) -> None:
        top_left = getattr(text_box, "top_left", None)
        bottom_right = getattr(text_box, "bottom_right", None)
        if top_left is None or bottom_right is None:
            raise KiCadCapabilityError(
                "Footprint text boxes must expose mutable top_left and bottom_right corners."
            )

        mirrored_top_left = self._mirror_vector_horizontally(top_left, anchor)
        mirrored_bottom_right = self._mirror_vector_horizontally(bottom_right, anchor)
        left_x = min(int(mirrored_top_left.x), int(mirrored_bottom_right.x))
        right_x = max(int(mirrored_top_left.x), int(mirrored_bottom_right.x))
        top_y = min(int(mirrored_top_left.y), int(mirrored_bottom_right.y))
        bottom_y = max(int(mirrored_top_left.y), int(mirrored_bottom_right.y))
        text_box.top_left = self._make_vector_like(top_left, left_x, top_y)
        text_box.bottom_right = self._make_vector_like(bottom_right, right_x, bottom_y)

        current_layer = getattr(text_box, "layer", None)
        flipped_layer = self._flip_layer_id(board, current_layer)
        if current_layer is not None:
            text_box.layer = flipped_layer

        attributes = getattr(text_box, "attributes", None)
        if attributes is None:
            return

        angle = getattr(attributes, "angle", None)
        if angle is not None:
            attributes.angle = self._normalize_degrees(-float(angle))

        if flipped_layer != current_layer and hasattr(attributes, "mirrored"):
            attributes.mirrored = not bool(getattr(attributes, "mirrored", False))

    def _flip_board_shape(self, board: Any, shape: Any, anchor: Any) -> None:
        shape = self._coerce_concrete_board_shape(shape)
        current_layer = getattr(shape, "layer", None)
        if current_layer is not None:
            shape.layer = self._flip_layer_id(board, current_layer)

        if hasattr(shape, "polygons"):
            for polygon in list(getattr(shape, "polygons", ()) or ()):
                self._flip_polygon_with_holes(polygon, anchor)
            return

        if hasattr(shape, "control1") and hasattr(shape, "control2"):
            shape.start = self._mirror_vector_horizontally(shape.start, anchor)
            shape.control1 = self._mirror_vector_horizontally(shape.control1, anchor)
            shape.control2 = self._mirror_vector_horizontally(shape.control2, anchor)
            shape.end = self._mirror_vector_horizontally(shape.end, anchor)
            return

        if hasattr(shape, "mid"):
            shape.start = self._mirror_vector_horizontally(shape.start, anchor)
            shape.mid = self._mirror_vector_horizontally(shape.mid, anchor)
            shape.end = self._mirror_vector_horizontally(shape.end, anchor)
            return

        if hasattr(shape, "center") and hasattr(shape, "radius_point"):
            shape.center = self._mirror_vector_horizontally(shape.center, anchor)
            shape.radius_point = self._mirror_vector_horizontally(shape.radius_point, anchor)
            return

        if hasattr(shape, "top_left") and hasattr(shape, "bottom_right"):
            mirrored_top_left = self._mirror_vector_horizontally(shape.top_left, anchor)
            mirrored_bottom_right = self._mirror_vector_horizontally(shape.bottom_right, anchor)
            left_x = min(int(mirrored_top_left.x), int(mirrored_bottom_right.x))
            right_x = max(int(mirrored_top_left.x), int(mirrored_bottom_right.x))
            top_y = min(int(mirrored_top_left.y), int(mirrored_bottom_right.y))
            bottom_y = max(int(mirrored_top_left.y), int(mirrored_bottom_right.y))
            shape.top_left = self._make_vector_like(shape.top_left, left_x, top_y)
            shape.bottom_right = self._make_vector_like(shape.bottom_right, right_x, bottom_y)
            return

        if hasattr(shape, "start") and hasattr(shape, "end"):
            shape.start = self._mirror_vector_horizontally(shape.start, anchor)
            shape.end = self._mirror_vector_horizontally(shape.end, anchor)
            return

        raise KiCadCapabilityError(
            f"Footprint graphic shape flipping is not implemented for {type(shape).__name__}."
        )

    def _coerce_concrete_board_shape(self, shape: Any) -> Any:
        if callable(kipy_to_concrete_board_shape):
            try:
                concrete_shape = kipy_to_concrete_board_shape(shape)
            except Exception:  # noqa: BLE001
                concrete_shape = None
            if concrete_shape is not None:
                return concrete_shape

        return shape

    def _flip_zone(self, board: Any, zone: Any, anchor: Any) -> None:
        layers = list(getattr(zone, "layers", ()) or ())
        if layers:
            zone.layers = [self._flip_layer_id(board, layer) for layer in layers]

        outline = getattr(zone, "outline", None)
        if outline is not None:
            self._flip_polygon_with_holes(outline, anchor)

        proto = getattr(zone, "_proto", None)
        if proto is None:
            return

        for filled_polygon in getattr(proto, "filled_polygons", ()):
            filled_polygon.layer = self._flip_layer_id(board, filled_polygon.layer)
            if KiCadPolygonWithHoles is None:
                continue
            for polygon_proto in getattr(getattr(filled_polygon, "shapes", None), "polygons", ()):
                self._flip_polygon_with_holes(
                    KiCadPolygonWithHoles(proto_ref=polygon_proto),
                    anchor,
                )

        for layer_properties in getattr(proto, "layer_properties", ()):
            layer_properties.layer = self._flip_layer_id(board, layer_properties.layer)

    def _flip_barcode(self, board: Any, barcode: Any, anchor: Any) -> None:
        position = getattr(barcode, "position", None)
        if position is not None:
            barcode.position = self._mirror_vector_horizontally(position, anchor)

        current_layer = getattr(barcode, "layer", None)
        if current_layer is not None:
            barcode.layer = self._flip_layer_id(board, current_layer)

        current_orientation = getattr(barcode, "orientation", None)
        if current_orientation is not None:
            barcode.orientation = self._make_angle_like(
                current_orientation,
                -self._read_angle_degrees(current_orientation, item_label="Barcode orientation"),
            )

    def _flip_reference_image(self, board: Any, image: Any, anchor: Any) -> None:
        position = getattr(image, "position", None)
        if position is not None:
            image.position = self._mirror_vector_horizontally(position, anchor)

        current_layer = getattr(image, "layer", None)
        if current_layer is not None:
            image.layer = self._flip_layer_id(board, current_layer)

        transform_origin_offset = getattr(image, "transform_origin_offset", None)
        if transform_origin_offset is not None:
            image.transform_origin_offset = self._make_vector_like(
                transform_origin_offset,
                -int(transform_origin_offset.x),
                int(transform_origin_offset.y),
            )

    def _flip_polygon_with_holes(self, polygon: Any, anchor: Any) -> None:
        outline = getattr(polygon, "outline", None)
        if outline is not None:
            self._flip_polyline_like(outline, anchor)

        for hole in list(getattr(polygon, "holes", ()) or ()):
            self._flip_polyline_like(hole, anchor)

    def _flip_polyline_like(self, polyline: Any, anchor: Any) -> None:
        nodes = getattr(polyline, "nodes", None)
        if nodes is not None:
            for node in list(nodes):
                self._flip_polyline_node_like(node, anchor)
            return

        if isinstance(polyline, list):
            for index, node in enumerate(list(polyline)):
                if self._is_polyline_node_like(node):
                    self._flip_polyline_node_like(node, anchor)
                else:
                    polyline[index] = self._mirror_vector_horizontally(node, anchor)
            return

        raise KiCadCapabilityError(
            f"Footprint polygon flipping is not implemented for {type(polyline).__name__}."
        )

    def _flip_polyline_node_like(self, node: Any, anchor: Any) -> None:
        has_point = bool(getattr(node, "has_point", False)) or hasattr(node, "point")
        if has_point and getattr(node, "point", None) is not None:
            node.point = self._mirror_vector_horizontally(node.point, anchor)
            return

        has_arc = bool(getattr(node, "has_arc", False)) or hasattr(node, "arc")
        arc = getattr(node, "arc", None)
        if has_arc and arc is not None:
            arc.start = self._mirror_vector_horizontally(arc.start, anchor)
            arc.mid = self._mirror_vector_horizontally(arc.mid, anchor)
            arc.end = self._mirror_vector_horizontally(arc.end, anchor)
            return

        raise KiCadCapabilityError(
            f"Footprint polygon node flipping is not implemented for {type(node).__name__}."
        )

    def _is_polyline_node_like(self, value: Any) -> bool:
        return hasattr(value, "point") or hasattr(value, "arc") or hasattr(value, "has_point")

    def _is_board_text_like(self, value: Any) -> bool:
        return hasattr(value, "position") and hasattr(value, "attributes") and hasattr(value, "value")

    def _is_board_text_box_like(self, value: Any) -> bool:
        return hasattr(value, "top_left") and hasattr(value, "bottom_right") and hasattr(value, "attributes")

    def _is_board_shape_like(self, value: Any) -> bool:
        return any(
            hasattr(value, attribute)
            for attribute in ("polygons", "control1", "mid", "center", "top_left", "start")
        ) and hasattr(value, "layer")

    def _is_pad_like(self, value: Any) -> bool:
        return hasattr(value, "padstack") and hasattr(value, "number") and hasattr(value, "position")

    def _set_footprint_orientation_direct(self, footprint: Any, angle: Any) -> None:
        proto = getattr(footprint, "_proto", None)
        proto_orientation = getattr(proto, "orientation", None) if proto is not None else None
        angle_proto = getattr(angle, "proto", None)
        if proto_orientation is not None and angle_proto is not None:
            proto_orientation.CopyFrom(angle_proto)
            return

        footprint.orientation = angle

    def _flip_layer_id(self, board: Any, layer: Any) -> Any:
        if layer is None:
            return None

        layer_info = serialize_layer(layer, board) or {}
        layer_name = str(layer_info.get("name") or "").strip()
        if not layer_name:
            return layer

        if layer_name.startswith("F."):
            resolved_layer = self._resolve_layer_name_with_fallback(board, f"B.{layer_name[2:]}")
            return layer if resolved_layer is None else resolved_layer

        if layer_name.startswith("B."):
            resolved_layer = self._resolve_layer_name_with_fallback(board, f"F.{layer_name[2:]}")
            return layer if resolved_layer is None else resolved_layer

        return layer

    def _resolve_layer_name_with_fallback(self, board: Any, layer_name: str) -> int | None:
        try:
            return resolve_layer_id(board, layer_name)
        except KiCadLookupError:
            pass

        get_layer_name = getattr(board, "get_layer_name", None)
        if not callable(get_layer_name):
            return None

        normalized_layer_name = layer_name.strip().lower()
        for layer_id in range(512):
            try:
                candidate_name = get_layer_name(layer_id)
            except Exception:  # noqa: BLE001
                continue

            if str(candidate_name).strip().lower() == normalized_layer_name:
                return layer_id

        return None

    def _mirror_vector_horizontally(self, current: Any, anchor: Any) -> Any:
        if current is None:
            raise KiCadCapabilityError("The target item does not expose a mutable position vector.")

        anchor_x = getattr(anchor, "x", None)
        current_x = getattr(current, "x", None)
        current_y = getattr(current, "y", None)
        if anchor_x is None or current_x is None or current_y is None:
            raise KiCadCapabilityError(
                "The target item does not expose the coordinates needed for mirroring."
            )

        mirrored_x = (2 * int(anchor_x)) - int(current_x)
        return self._make_vector_like(current, mirrored_x, int(current_y))

    def _read_angle_degrees(self, angle: Any, *, item_label: str) -> float:
        degrees = getattr(angle, "degrees", None)
        if degrees is None:
            try:
                return float(angle)
            except Exception as exc:  # noqa: BLE001
                raise KiCadCapabilityError(
                    f"{item_label} does not expose a readable angle in degrees."
                ) from exc

        return float(degrees)

    def _normalize_degrees(self, degrees: float) -> float:
        while degrees < 0.0:
            degrees += 360.0

        while degrees >= 360.0:
            degrees -= 360.0

        return degrees

    def _clone_item(self, item: Any) -> Any:
        return self._clone_proto_wrapper(item)

    def _coerce_text_item_for_kicad(self, text_item: Any) -> Any:
        as_text = getattr(text_item, "as_text", None)
        if callable(as_text):
            return as_text()

        as_textbox = getattr(text_item, "as_textbox", None)
        if callable(as_textbox):
            return as_textbox()

        return text_item

    def _extract_graphic_shapes(self, value: Any) -> list[Any]:
        shapes = getattr(value, "shapes", None)
        if shapes is not None:
            return list(shapes)
        return self._as_item_sequence(value)

    def _get_text_item_value(self, item: Any) -> str:
        value = getattr(item, "value", None)
        if value is None:
            value = getattr(item, "text", None)
        if value is None:
            return ""
        return str(value)

    def _resolve_board_items_by_ids(self, board: Any, item_ids: Sequence[str]) -> list[Any]:
        normalized_item_ids = self._normalize_item_ids(item_ids)
        item_map: dict[str, Any] = {}

        for getter_name in BOARD_ITEM_GETTER_NAMES:
            getter = getattr(board, getter_name, None)
            if not callable(getter):
                continue

            for item in getter():
                item_id = serialize_identifier(getattr(item, "id", "")).strip()
                if not item_id:
                    continue
                item_map.setdefault(item_id.lower(), item)

        missing_item_ids = [
            item_id for item_id in normalized_item_ids if item_id.lower() not in item_map
        ]
        if missing_item_ids:
            raise KiCadLookupError(
                "Unable to find board item(s) with id(s): "
                + ", ".join(repr(item_id) for item_id in missing_item_ids)
            )

        return [item_map[item_id.lower()] for item_id in normalized_item_ids]

    def _resolve_board_item_getter_names(self, item_kinds: Sequence[str] | None) -> list[str]:
        if item_kinds is None:
            return list(BOARD_ITEM_GETTER_NAMES)

        resolved_getter_names: list[str] = []
        for item_kind in item_kinds:
            normalized_kind = str(item_kind).strip().lower()
            getter_name = BOARD_ITEM_KIND_GETTERS.get(normalized_kind)
            if getter_name is None:
                raise KiCadLookupError(
                    f"Unsupported item kind {item_kind!r}. Supported kinds: "
                    + ", ".join(sorted(BOARD_ITEM_KIND_GETTERS))
                )
            if getter_name not in resolved_getter_names:
                resolved_getter_names.append(getter_name)

        return resolved_getter_names

    def _collect_board_items(self, board: Any, getter_names: Sequence[str]) -> list[Any]:
        items: list[Any] = []
        seen_item_ids: set[str] = set()

        for getter_name in getter_names:
            getter = getattr(board, getter_name, None)
            if not callable(getter):
                continue

            for item in getter():
                item_id = serialize_identifier(getattr(item, "id", "")).strip().lower()
                if item_id and item_id in seen_item_ids:
                    continue
                if item_id:
                    seen_item_ids.add(item_id)
                items.append(item)

        return items

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

    def _is_copper_layer(self, board: Any, layer_id: int) -> bool:
        layer_info = serialize_layer(layer_id, board) or {}
        layer_name = str(layer_info.get("name", ""))
        return layer_name.lower().endswith(".cu")

    def _get_optional_layers(self, board: Any, method_name: str) -> list[dict[str, Any]] | None:
        method = getattr(board, method_name, None)
        if not callable(method):
            return None

        return [serialize_layer(layer, board) for layer in method()]

