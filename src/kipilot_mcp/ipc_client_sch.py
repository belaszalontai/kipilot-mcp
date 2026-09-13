"""Schematic-specific KiCad IPC client mixin."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .ipc_client_core import *  # noqa: F401,F403
from .serializers import (
    serialize_schematic_bom_field_settings,
    serialize_schematic_bom_format_settings,
)

try:
    from kipy.common_types import (  # type: ignore[import-not-found]
        LibraryIdentifier as KiCadLibraryIdentifier,
    )
    from kipy.common_types import Text as KiCadText  # type: ignore[import-not-found]
    from kipy.proto.schematic import (  # type: ignore[import-not-found]
        schematic_types_pb2 as KiCadSchematicProto,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        GlobalLabel as KiCadGlobalLabel,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        HierarchicalLabel as KiCadHierarchicalLabel,
    )
    from kipy.schematic_types import Junction as KiCadJunction  # type: ignore[import-not-found]
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        LocalLabel as KiCadLocalLabel,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        NoConnectMarker as KiCadNoConnectMarker,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        SchematicLine as KiCadSchematicLine,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        SchematicSymbol as KiCadSchematicSymbol,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        SchematicSymbolInstance as KiCadSchematicSymbolInstance,
    )
    from kipy.schematic_types import (  # type: ignore[import-not-found]
        SchematicText as KiCadSchematicText,
    )
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    KiCadLibraryIdentifier = None
    KiCadText = None
    KiCadSchematicProto = None
    KiCadGlobalLabel = None
    KiCadHierarchicalLabel = None
    KiCadJunction = None
    KiCadLocalLabel = None
    KiCadNoConnectMarker = None
    KiCadSchematicLine = None
    KiCadSchematicSymbol = None
    KiCadSchematicSymbolInstance = None
    KiCadSchematicText = None

DEFAULT_SCHEMATIC_NETLIST_FORMAT = 2

DEFAULT_SCHEMATIC_ITEM_LIMIT = 200
SCH_CREATE_ITEM_KINDS = (
    "wire",
    "bus",
    "junction",
    "no_connect",
    "label",
    "global_label",
    "hierarchical_label",
    "text",
    "symbol",
)
SCH_LABEL_KINDS = ("label", "global_label", "hierarchical_label")
SCH_LABEL_SPIN_STYLE_NAMES = {
    "left": "SLSS_LEFT",
    "up": "SLSS_UP",
    "right": "SLSS_RIGHT",
    "bottom": "SLSS_BOTTOM",
    "unknown": "SLSS_UNKNOWN",
}
SCH_LABEL_SPIN_STYLE_FALLBACK = {
    "SLSS_UNKNOWN": 0,
    "SLSS_LEFT": 1,
    "SLSS_UP": 2,
    "SLSS_RIGHT": 3,
    "SLSS_BOTTOM": 4,
}
SCH_LABEL_SHAPE_NAMES = {
    "input": "SLSH_INPUT",
    "output": "SLSH_OUTPUT",
    "bidirectional": "SLSH_BIDI",
    "bidi": "SLSH_BIDI",
    "tri_state": "SLSH_TRISTATE",
    "tristate": "SLSH_TRISTATE",
    "passive": "SLSH_PASSIVE",
    "dot": "SLSH_DOT",
    "circle": "SLSH_CIRCLE",
    "diamond": "SLSH_DIAMOND",
    "rectangle": "SLSH_RECTANGLE",
}
SCH_LABEL_SHAPE_FALLBACK = {
    "SLSH_UNKNOWN": 0,
    "SLSH_INPUT": 1,
    "SLSH_OUTPUT": 2,
    "SLSH_BIDI": 3,
    "SLSH_TRISTATE": 4,
    "SLSH_PASSIVE": 5,
    "SLSH_DOT": 6,
    "SLSH_CIRCLE": 7,
    "SLSH_DIAMOND": 8,
    "SLSH_RECTANGLE": 9,
}
SCH_CREATABLE_ITEM_TYPES = {
    "wire": KiCadSchematicLine,
    "bus": KiCadSchematicLine,
    "junction": KiCadJunction,
    "no_connect": KiCadNoConnectMarker,
    "label": KiCadLocalLabel,
    "global_label": KiCadGlobalLabel,
    "hierarchical_label": KiCadHierarchicalLabel,
    "text": KiCadSchematicText,
    "symbol": KiCadSchematicSymbolInstance,
}
SCH_UPDATABLE_FIELDS = (
    "x_mm",
    "y_mm",
    "text",
    "reference",
    "value",
    "unit",
    "spin_style",
    "shape",
    "diameter_mm",
    "locked",
)


class KiCadSchematicClientMixin:
    """Schematic-specific KiCad IPC client behavior."""

    async def get_schematic_hierarchy(self) -> dict[str, Any]:
        """Return the top-level schematic hierarchy tree."""

        return await self._run_schematic_read(
            self._get_schematic_hierarchy,
            default_message="Unable to read the current schematic hierarchy through the IPC API.",
        )

    async def get_schematic_netlist(
        self,
        item_types: Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Return the current schematic netlist with optional item-type filtering."""

        return await self._run_schematic_read(
            lambda schematic: self._get_schematic_netlist(schematic, item_types=item_types),
            default_message="Unable to read the current schematic netlist through the IPC API.",
        )

    async def hit_test_schematic(
        self,
        *,
        item_id: str,
        x_mm: float,
        y_mm: float,
        tolerance_mm: float = 0.0,
    ) -> dict[str, Any]:
        """Run a hit test against one schematic item at a schematic-space position."""

        return await self._run_schematic_read(
            lambda schematic: self._hit_test_schematic(
                schematic,
                item_id=item_id,
                x_mm=x_mm,
                y_mm=y_mm,
                tolerance_mm=tolerance_mm,
            ),
            default_message=(
                "Unable to perform the requested schematic hit test through the IPC API."
            ),
        )

    async def get_schematic_page_settings(self) -> dict[str, Any]:
        """Return the current schematic page settings."""

        return await self._run_schematic_read(
            self._get_schematic_page_settings,
            default_message="Unable to read schematic page settings through the IPC API.",
        )

    async def set_schematic_page_settings(
        self,
        *,
        page_size: int | str | None = None,
        orientation: int | str | None = None,
        drawing_sheet: str | None = None,
        user_page_size_mm: dict[str, float | int] | None = None,
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Update one or more page settings fields on the current schematic."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._set_schematic_page_settings(
                schematic,
                page_size=page_size,
                orientation=orientation,
                drawing_sheet=drawing_sheet,
                user_page_size_mm=user_page_size_mm,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update schematic page settings through the IPC API.",
            mutation_name="sch_set_page_settings",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def get_schematic_title_block(self) -> dict[str, Any]:
        """Return the current schematic title block information."""

        return await self._run_schematic_read(
            self._get_schematic_title_block,
            default_message="Unable to read schematic title block information through the IPC API.",
        )

    async def set_schematic_title_block(
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
        """Update one or more title block fields on the current schematic."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._set_schematic_title_block(
                schematic,
                title=title,
                revision=revision,
                date=date,
                company=company,
                comments=comments,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update the schematic title block through the IPC API.",
            mutation_name="sch_set_title_block",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def export_schematic_svg(
        self,
        output_dir: str,
        plot_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Export the current schematic to SVG."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_plot_job(
                schematic,
                method_name="export_svg",
                format_name="svg",
                output_path=output_dir,
                output_kind="directory",
                path_argument_name="output_dir",
                plot_settings=plot_settings,
            ),
            default_message="Unable to export the current schematic to SVG through the IPC API.",
        )

    async def export_schematic_dxf(
        self,
        output_dir: str,
        plot_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Export the current schematic to DXF."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_plot_job(
                schematic,
                method_name="export_dxf",
                format_name="dxf",
                output_path=output_dir,
                output_kind="directory",
                path_argument_name="output_dir",
                plot_settings=plot_settings,
            ),
            default_message="Unable to export the current schematic to DXF through the IPC API.",
        )

    async def export_schematic_pdf(
        self,
        output_file: str,
        plot_settings: dict[str, Any] | None = None,
        *,
        property_popups: bool = False,
        hierarchical_links: bool = False,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Export the current schematic to PDF."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_plot_job(
                schematic,
                method_name="export_pdf",
                format_name="pdf",
                output_path=output_file,
                output_kind="file",
                path_argument_name="output_file",
                plot_settings=plot_settings,
                property_popups=property_popups,
                hierarchical_links=hierarchical_links,
                include_metadata=include_metadata,
            ),
            default_message="Unable to export the current schematic to PDF through the IPC API.",
        )

    async def export_schematic_ps(
        self,
        output_dir: str,
        plot_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Export the current schematic to PostScript."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_plot_job(
                schematic,
                method_name="export_ps",
                format_name="ps",
                output_path=output_dir,
                output_kind="directory",
                path_argument_name="output_dir",
                plot_settings=plot_settings,
            ),
            default_message=(
                "Unable to export the current schematic to PostScript through the IPC API."
            ),
        )

    async def export_schematic_netlist(
        self,
        output_file: str,
        netlist_format: int | str = DEFAULT_SCHEMATIC_NETLIST_FORMAT,
        variant_name: str = "",
    ) -> dict[str, Any]:
        """Export the current schematic netlist to one output file."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_netlist_job(
                schematic,
                output_file=output_file,
                netlist_format=netlist_format,
                variant_name=variant_name,
            ),
            default_message=(
                "Unable to export the current schematic netlist through the IPC API."
            ),
        )

    async def export_schematic_bom(
        self,
        output_file: str,
        format_settings: dict[str, Any] | None = None,
        field_settings: dict[str, Any] | None = None,
        *,
        exclude_dnp: bool = False,
        group_symbols: bool = False,
        variant_name: str = "",
    ) -> dict[str, Any]:
        """Export the current schematic BOM to one output file."""

        return await self._run_schematic_read(
            lambda schematic: self._export_schematic_bom_job(
                schematic,
                output_file=output_file,
                format_settings=format_settings,
                field_settings=field_settings,
                exclude_dnp=exclude_dnp,
                group_symbols=group_symbols,
                variant_name=variant_name,
            ),
            default_message="Unable to export the current schematic BOM through the IPC API.",
        )

    async def get_schematic_selection(self, limit: int = 200) -> dict[str, Any]:
        """Return the current schematic selection."""

        return await self._run_schematic_read(
            lambda schematic: self._get_schematic_selection(schematic, limit=limit),
            default_message=(
                "Unable to read the current schematic selection through the IPC API."
            ),
        )

    async def add_to_schematic_selection(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Add one or more items to the current schematic selection."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._add_to_schematic_selection(
                schematic,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message=(
                "Unable to add the requested items to the schematic selection "
                "through the IPC API."
            ),
            mutation_name="sch_add_to_selection",
            dry_run=dry_run,
        )

    async def remove_from_schematic_selection(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Remove one or more items from the current schematic selection."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._remove_from_schematic_selection(
                schematic,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message=(
                "Unable to remove the requested items from the schematic selection "
                "through the IPC API."
            ),
            mutation_name="sch_remove_from_selection",
            dry_run=dry_run,
        )

    async def clear_schematic_selection(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Clear the current schematic selection."""

        return await self._run_schematic_write(
            self._clear_schematic_selection,
            default_message=(
                "Unable to clear the schematic selection through the IPC API."
            ),
            mutation_name="sch_clear_selection",
            dry_run=dry_run,
        )

    async def create_schematic_items(
        self,
        *,
        items: Sequence[dict[str, Any]],
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Create schematic items from declarative item specifications."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._create_schematic_items(
                schematic,
                items=items,
                dry_run=is_dry_run,
            ),
            default_message="Unable to create schematic items through the IPC API.",
            mutation_name="sch_create_items",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def update_schematic_items(
        self,
        *,
        updates: Sequence[dict[str, Any]],
        dry_run: bool = False,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Update existing schematic items by item ID."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._update_schematic_items(
                schematic,
                updates=updates,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update schematic items through the IPC API.",
            mutation_name="sch_update_items",
            dry_run=dry_run,
            commit_message=commit_message,
        )

    async def remove_schematic_items(
        self,
        *,
        item_ids: Sequence[str],
        dry_run: bool = False,
        commit_message: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete schematic items by item ID."""

        return await self._run_schematic_write(
            lambda schematic, is_dry_run: self._remove_schematic_items(
                schematic,
                item_ids=item_ids,
                dry_run=is_dry_run,
            ),
            default_message="Unable to delete schematic items through the IPC API.",
            mutation_name="sch_remove_items",
            dry_run=dry_run,
            commit_message=commit_message,
            dangerous=True,
            force=force,
        )

    async def save_schematic(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Save the current schematic document to disk."""

        return await self._run_schematic_command(
            self._save_schematic,
            default_message="Unable to save the current schematic through the IPC API.",
            mutation_name="sch_save",
            dry_run=dry_run,
        )

    async def get_schematic_items(
        self,
        *,
        limit: int = DEFAULT_SCHEMATIC_ITEM_LIMIT,
        kinds: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Return schematic items, optionally filtered to a set of item kinds."""

        return await self._run_schematic_read(
            lambda schematic: self._get_schematic_items(
                schematic,
                limit=limit,
                kinds=kinds,
            ),
            default_message="Unable to read schematic items through the IPC API.",
        )

    async def get_schematic_symbols(
        self,
        *,
        limit: int = DEFAULT_SCHEMATIC_ITEM_LIMIT,
    ) -> dict[str, Any]:
        """Return the symbol instances placed in the current schematic."""

        return await self._run_schematic_read(
            lambda schematic: self._get_schematic_symbols(schematic, limit=limit),
            default_message="Unable to read schematic symbols through the IPC API.",
        )

    async def get_schematic_labels(
        self,
        *,
        limit: int = DEFAULT_SCHEMATIC_ITEM_LIMIT,
    ) -> dict[str, Any]:
        """Return the labels placed in the current schematic."""

        return await self._run_schematic_read(
            lambda schematic: self._get_schematic_labels(schematic, limit=limit),
            default_message="Unable to read schematic labels through the IPC API.",
        )

    async def get_schematic_as_string(self) -> dict[str, Any]:
        """Return the whole schematic document as native KiCad s-expression text."""

        return await self._run_schematic_read(
            self._get_schematic_as_string,
            default_message="Unable to read the schematic document text through the IPC API.",
        )

    async def get_schematic_selection_as_string(self) -> dict[str, Any]:
        """Return the current selection as native KiCad s-expression text."""

        return await self._run_schematic_read(
            self._get_schematic_selection_as_string,
            default_message=(
                "Unable to read the schematic selection text through the IPC API."
            ),
        )

    async def is_schematic_document_modified(self) -> dict[str, Any]:
        """Report whether the schematic has unsaved modifications."""

        return await self._run_schematic_read(
            self._is_schematic_document_modified,
            default_message=(
                "Unable to read the schematic modified state through the IPC API."
            ),
        )

    async def get_schematic_variants(self) -> dict[str, Any]:
        """Return the design variants defined in the current schematic."""

        return await self._run_schematic_read(
            self._get_schematic_variants,
            default_message="Unable to read schematic variants through the IPC API.",
        )

    async def get_current_schematic_variant(self) -> dict[str, Any]:
        """Return the currently applied schematic variant."""

        return await self._run_schematic_read(
            self._get_current_schematic_variant,
            default_message=(
                "Unable to read the current schematic variant through the IPC API."
            ),
        )

    async def add_schematic_variant(
        self,
        *,
        name: str,
        description: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Add a design variant to the current schematic."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._add_schematic_variant(
                schematic,
                name=name,
                description=description,
                dry_run=is_dry_run,
            ),
            default_message="Unable to add the schematic variant through the IPC API.",
            mutation_name="sch_add_variant",
            dry_run=dry_run,
        )

    async def delete_schematic_variant(self, *, name: str, dry_run: bool = False) -> dict[str, Any]:
        """Delete a design variant from the current schematic."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._delete_schematic_variant(
                schematic,
                name=name,
                dry_run=is_dry_run,
            ),
            default_message="Unable to delete the schematic variant through the IPC API.",
            mutation_name="sch_delete_variant",
            dry_run=dry_run,
        )

    async def rename_schematic_variant(
        self,
        *,
        old_name: str,
        new_name: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Rename a design variant in the current schematic."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._rename_schematic_variant(
                schematic,
                old_name=old_name,
                new_name=new_name,
                dry_run=is_dry_run,
            ),
            default_message="Unable to rename the schematic variant through the IPC API.",
            mutation_name="sch_rename_variant",
            dry_run=dry_run,
        )

    async def copy_schematic_variant(
        self,
        *,
        old_name: str,
        new_name: str,
        new_description: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Copy a design variant, including its item overrides."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._copy_schematic_variant(
                schematic,
                old_name=old_name,
                new_name=new_name,
                new_description=new_description,
                dry_run=is_dry_run,
            ),
            default_message="Unable to copy the schematic variant through the IPC API.",
            mutation_name="sch_copy_variant",
            dry_run=dry_run,
        )

    async def set_schematic_variant_description(
        self,
        *,
        name: str,
        description: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Set the description of a design variant."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._set_schematic_variant_description(
                schematic,
                name=name,
                description=description,
                dry_run=is_dry_run,
            ),
            default_message=(
                "Unable to update the schematic variant description through the IPC API."
            ),
            mutation_name="sch_set_variant_description",
            dry_run=dry_run,
        )

    async def set_current_schematic_variant(
        self,
        *,
        name: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Select the active schematic variant, or the default variant when name is omitted."""

        return await self._run_schematic_command(
            lambda schematic, is_dry_run: self._set_current_schematic_variant(
                schematic,
                name=name,
                dry_run=is_dry_run,
            ),
            default_message=(
                "Unable to select the schematic variant through the IPC API."
            ),
            mutation_name="sch_set_current_variant",
            dry_run=dry_run,
        )

    async def _run_schematic_read(
        self,
        operation: Callable[[Any], dict[str, Any]],
        *,
        default_message: str,
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(self._with_schematic, operation)
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    async def _run_schematic_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        *,
        default_message: str,
        mutation_name: str,
        dry_run: bool = False,
        commit_message: str | None = None,
        dangerous: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            self._assert_mutation_allowed(dry_run=dry_run, dangerous=dangerous, force=force)
            return await asyncio.to_thread(
                self._with_schematic_write,
                operation,
                mutation_name,
                dry_run,
                commit_message,
            )
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    def _with_schematic(self, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
        return self._with_kicad(lambda kicad: operation(self._resolve_schematic(kicad)))

    def _with_schematic_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
        commit_message: str | None,
    ) -> dict[str, Any]:
        resolved_commit_message = self._resolve_commit_message(mutation_name, commit_message)
        result = self._with_kicad(
            lambda kicad: self._execute_schematic_write(
                self._resolve_schematic(kicad),
                operation,
                mutation_name,
                dry_run,
                resolved_commit_message,
            )
        )
        return result

    def _execute_schematic_write(
        self,
        schematic: Any,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
        resolved_commit_message: str,
    ) -> dict[str, Any]:
        commit = None

        if not dry_run:
            begin_commit = getattr(schematic, "begin_commit", None)
            if callable(begin_commit):
                commit = begin_commit()

        try:
            result = operation(schematic, dry_run)
            if commit is not None:
                push_commit = getattr(schematic, "push_commit", None)
                if not callable(push_commit):
                    raise KiCadCapabilityError(
                        "The active KiCad schematic does not expose push_commit(), "
                        "so atomic writes are unavailable."
                    )
                push_commit(commit, resolved_commit_message)
        except Exception:
            if commit is not None:
                drop_commit = getattr(schematic, "drop_commit", None)
                if callable(drop_commit):
                    drop_commit(commit)
            raise

        return {
            "ok": True,
            "mutation": mutation_name,
            "dry_run": dry_run,
            "commit_message": None if dry_run else resolved_commit_message,
            **result,
        }

    async def _run_schematic_command(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        *,
        default_message: str,
        mutation_name: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        try:
            self._assert_mutation_allowed(dry_run=dry_run, dangerous=False, force=False)
            return await asyncio.to_thread(
                self._execute_schematic_command,
                operation,
                mutation_name,
                dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    def _execute_schematic_command(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Run a schematic mutation that is not part of an item commit transaction."""

        result = self._with_schematic(lambda schematic: operation(schematic, dry_run))
        return {
            "ok": True,
            "mutation": mutation_name,
            "dry_run": dry_run,
            "commit_message": None,
            **result,
        }

    def _resolve_schematic(self, kicad: Any) -> Any:
        get_schematic = getattr(kicad, "get_schematic", None)
        if not callable(get_schematic):
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose KiCad.get_schematic(). "
                "Schematic MCP tools require a newer binding build with schematic IPC support."
            )

        if callable(get_schematic):
            schematic = get_schematic()
            if schematic is not None:
                return schematic

        raise KiCadCapabilityError(
            "Unable to resolve the current KiCad schematic from the active session. "
            "Ensure the target schematic is open in the connected KiCad instance."
        )

    def _get_schematic_hierarchy(self, schematic: Any) -> dict[str, Any]:
        get_hierarchy = getattr(schematic, "get_hierarchy", None)
        if not callable(get_hierarchy):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_hierarchy()."
            )

        hierarchy = list(get_hierarchy())
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "count": len(hierarchy),
            "hierarchy": [serialize_sheet_instance(sheet) for sheet in hierarchy],
        }

    def _get_schematic_netlist(
        self,
        schematic: Any,
        *,
        item_types: Sequence[int] | None,
    ) -> dict[str, Any]:
        get_netlist = getattr(schematic, "get_netlist", None)
        if not callable(get_netlist):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_netlist()."
            )

        nets = list(get_netlist(item_types) if item_types is not None else get_netlist())
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "count": len(nets),
            "item_types": list(item_types) if item_types is not None else None,
            "nets": [serialize_schematic_net(net) for net in nets],
        }

    def _hit_test_schematic(
        self,
        schematic: Any,
        *,
        item_id: str,
        x_mm: float,
        y_mm: float,
        tolerance_mm: float,
    ) -> dict[str, Any]:
        hit_test = getattr(schematic, "hit_test", None)
        if not callable(hit_test):
            raise KiCadCapabilityError("The active KiCad schematic does not expose hit_test().")

        item = self._resolve_schematic_items_by_ids(schematic, [item_id])[0]
        x_nm = self._millimeters_to_nanometers(x_mm)
        y_nm = self._millimeters_to_nanometers(y_mm)
        tolerance_nm = max(0, self._millimeters_to_nanometers(tolerance_mm))
        position = self._construct_vector(schematic, x_nm, y_nm)
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "item_id": serialize_identifier(getattr(item, "id", item_id)),
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

    def _get_schematic_selection(
        self,
        schematic: Any,
        *,
        limit: int,
    ) -> dict[str, Any]:
        get_selection = getattr(schematic, "get_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_selection()."
            )

        selection = list(get_selection())
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "count": len(selection),
            "selection": [serialize_schematic_item(item) for item in selection[:limit]],
        }

    def _schematic_selection_without_ids(
        self,
        items: Sequence[Any],
        requested_item_ids: Sequence[str],
    ) -> list[Any]:
        requested_id_set = {item_id.lower() for item_id in requested_item_ids}
        return [
            item
            for item in items
            if serialize_identifier(getattr(item, "id", "")).lower() not in requested_id_set
        ]

    def _add_to_schematic_selection(
        self,
        schematic: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        requested_item_ids = self._normalize_item_ids(item_ids)
        get_selection = getattr(schematic, "get_selection", None)
        add_to_selection = getattr(schematic, "add_to_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_selection()."
            )
        if not callable(add_to_selection) and not dry_run:
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose add_to_selection()."
            )

        previous_selection = list(get_selection())
        requested_items = self._resolve_schematic_items_by_ids(schematic, requested_item_ids)

        if dry_run:
            previous_by_id = {
                serialize_identifier(getattr(item, "id", "")).lower(): item
                for item in previous_selection
            }
            applied_selection = list(previous_selection)
            for item in requested_items:
                item_id = serialize_identifier(getattr(item, "id", "")).lower()
                if item_id not in previous_by_id:
                    applied_selection.append(item)
                    previous_by_id[item_id] = item
        else:
            try:
                applied_selection = list(add_to_selection(requested_items))
            except TypeError:
                if len(requested_items) != 1:
                    raise
                applied_selection = list(add_to_selection(requested_items[0]))

        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "requested_item_ids": requested_item_ids,
            "previous_count": len(previous_selection),
            "count": len(applied_selection),
            "selection": [serialize_schematic_item(item) for item in applied_selection],
        }

    def _remove_from_schematic_selection(
        self,
        schematic: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        requested_item_ids = self._normalize_item_ids(item_ids)
        get_selection = getattr(schematic, "get_selection", None)
        remove_from_selection = getattr(schematic, "remove_from_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_selection()."
            )
        if not callable(remove_from_selection) and not dry_run:
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose remove_from_selection()."
            )

        previous_selection = list(get_selection())

        if dry_run:
            applied_selection = self._schematic_selection_without_ids(
                previous_selection, requested_item_ids
            )
        else:
            requested_items = self._resolve_schematic_items_by_ids(schematic, requested_item_ids)
            try:
                applied_selection = list(remove_from_selection(requested_items))
            except TypeError:
                if len(requested_items) != 1:
                    raise
                applied_selection = list(remove_from_selection(requested_items[0]))

        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "requested_item_ids": requested_item_ids,
            "previous_count": len(previous_selection),
            "count": len(applied_selection),
            "selection": [serialize_schematic_item(item) for item in applied_selection],
        }

    def _clear_schematic_selection(self, schematic: Any, dry_run: bool) -> dict[str, Any]:
        get_selection = getattr(schematic, "get_selection", None)
        clear_selection = getattr(schematic, "clear_selection", None)
        if not callable(get_selection):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_selection()."
            )
        if not callable(clear_selection) and not dry_run:
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose clear_selection()."
            )

        previous_selection = list(get_selection())
        if not dry_run:
            clear_selection()

        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "previous_count": len(previous_selection),
            "count": 0,
            "selection": [],
        }

    def _get_schematic_page_settings(self, schematic: Any) -> dict[str, Any]:
        page_settings = self._get_schematic_page_settings_info(schematic)
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "page_settings": serialize_page_settings(page_settings),
        }

    def _get_schematic_title_block(self, schematic: Any) -> dict[str, Any]:
        title_block = self._get_schematic_title_block_info(schematic)
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "title_block": serialize_title_block(title_block),
        }

    def _export_schematic_plot_job(
        self,
        schematic: Any,
        *,
        method_name: str,
        format_name: str,
        output_path: str,
        output_kind: str,
        path_argument_name: str,
        plot_settings: dict[str, Any] | None,
        **options: Any,
    ) -> dict[str, Any]:
        export_method = getattr(schematic, method_name, None)
        if not callable(export_method):
            raise KiCadCapabilityError(
                f"The active KiCad schematic does not expose {method_name}()."
            )

        validated_output_path = self._validate_schematic_export_target(
            output_path,
            format_name=format_name,
            output_kind=output_kind,
            path_argument_name=path_argument_name,
        )
        resolved_plot_settings = self._create_schematic_plot_settings(plot_settings)

        call_kwargs: dict[str, Any] = {}
        if resolved_plot_settings is not None:
            call_kwargs["plot_settings"] = resolved_plot_settings
        call_kwargs.update(options)

        job_result = export_method(validated_output_path, **call_kwargs)
        result = {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "format": format_name,
            "output_kind": output_kind,
            "output_path": validated_output_path,
            "requested_plot_settings": serialize_schematic_plot_settings(
                resolved_plot_settings
            ),
            "requested_options": options or None,
            "job": serialize_job_result(job_result),
        }
        result[path_argument_name] = validated_output_path
        return result

    def _export_schematic_netlist_job(
        self,
        schematic: Any,
        *,
        output_file: str,
        netlist_format: int | str,
        variant_name: str,
    ) -> dict[str, Any]:
        export_method = getattr(schematic, "export_netlist", None)
        if not callable(export_method):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose export_netlist()."
            )

        validated_output_file = self._validate_schematic_export_target(
            output_file,
            format_name="netlist",
            output_kind="file",
            path_argument_name="output_file",
        )
        resolved_netlist_format = self._coerce_enum_value(
            netlist_format,
            field_name="netlist_format",
        )
        if resolved_netlist_format is None:
            resolved_netlist_format = DEFAULT_SCHEMATIC_NETLIST_FORMAT

        resolved_variant_name = "" if variant_name is None else str(variant_name)
        job_result = export_method(
            validated_output_file,
            format=resolved_netlist_format,
            variant_name=resolved_variant_name,
        )
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "job_type": "netlist",
            "netlist_format": resolved_netlist_format,
            "variant_name": resolved_variant_name,
            "output_kind": "file",
            "output_path": validated_output_file,
            "output_file": validated_output_file,
            "job": serialize_job_result(job_result),
        }

    def _export_schematic_bom_job(
        self,
        schematic: Any,
        *,
        output_file: str,
        format_settings: dict[str, Any] | None,
        field_settings: dict[str, Any] | None,
        exclude_dnp: bool,
        group_symbols: bool,
        variant_name: str,
    ) -> dict[str, Any]:
        export_method = getattr(schematic, "export_bom", None)
        if not callable(export_method):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose export_bom()."
            )

        validated_output_file = self._validate_schematic_export_target(
            output_file,
            format_name="bom",
            output_kind="file",
            path_argument_name="output_file",
        )
        resolved_format_settings = self._create_schematic_bom_format_settings(format_settings)
        resolved_field_settings = self._create_schematic_bom_field_settings(field_settings)

        if not isinstance(exclude_dnp, bool):
            raise KiCadLookupError("exclude_dnp must be a boolean.")
        if not isinstance(group_symbols, bool):
            raise KiCadLookupError("group_symbols must be a boolean.")

        resolved_variant_name = "" if variant_name is None else str(variant_name)
        job_result = export_method(
            validated_output_file,
            format_settings=resolved_format_settings,
            field_settings=resolved_field_settings,
            exclude_dnp=exclude_dnp,
            group_symbols=group_symbols,
            variant_name=resolved_variant_name,
        )
        return {
            "ok": True,
            "schematic": self._serialize_schematic(schematic),
            "job_type": "bom",
            "output_kind": "file",
            "output_path": validated_output_file,
            "output_file": validated_output_file,
            "requested_format_settings": serialize_schematic_bom_format_settings(
                resolved_format_settings
            ),
            "requested_field_settings": serialize_schematic_bom_field_settings(
                resolved_field_settings
            ),
            "requested_options": {
                "exclude_dnp": exclude_dnp,
                "group_symbols": group_symbols,
                "variant_name": resolved_variant_name,
            },
            "job": serialize_job_result(job_result),
        }

    def _validate_schematic_export_target(
        self,
        output_path: str,
        *,
        format_name: str,
        output_kind: str,
        path_argument_name: str,
    ) -> str:
        normalized_output_path = str(output_path).strip()
        if not normalized_output_path:
            raise KiCadLookupError(f"{path_argument_name} must be a non-empty path.")

        target = Path(normalized_output_path)
        if output_kind == "directory":
            expected_suffix = f".{format_name.lower()}"
            if target.exists() and not target.is_dir():
                raise KiCadLookupError(
                    f"{path_argument_name} must point to a directory for schematic "
                    f"{format_name.upper()} export, but the existing path is a file."
                )
            if target.suffix.lower() == expected_suffix:
                raise KiCadLookupError(
                    f"{path_argument_name} must point to an output directory for schematic "
                    f"{format_name.upper()} export, not a {expected_suffix} file path."
                )
            return normalized_output_path

        if output_kind == "file":
            if target.exists() and target.is_dir():
                raise KiCadLookupError(
                    f"{path_argument_name} must point to an output file for schematic "
                    f"{format_name.upper()} export, but the existing path is a directory."
                )
            if normalized_output_path.endswith(("/", "\\")):
                raise KiCadLookupError(
                    f"{path_argument_name} must point to an output file for schematic "
                    f"{format_name.upper()} export, not a directory path."
                )
            return normalized_output_path

        raise KiCadLookupError(f"Unsupported schematic export output kind: {output_kind!r}.")

    def _set_schematic_page_settings(
        self,
        schematic: Any,
        *,
        page_size: int | str | None,
        orientation: int | str | None,
        drawing_sheet: str | None,
        user_page_size_mm: dict[str, float | int] | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        if (
            page_size is None
            and orientation is None
            and drawing_sheet is None
            and user_page_size_mm is None
        ):
            raise KiCadLookupError("At least one page settings field must be provided.")

        previous_page_settings = self._get_schematic_page_settings_info(schematic)
        updated_page_settings = self._clone_proto_wrapper(previous_page_settings)

        resolved_page_size = self._coerce_enum_value(page_size, field_name="page_size")
        resolved_orientation = self._coerce_enum_value(
            orientation,
            field_name="orientation",
        )
        normalized_user_page_size = None

        if resolved_page_size is not None:
            updated_page_settings.page_size = resolved_page_size
        if resolved_orientation is not None:
            updated_page_settings.orientation = resolved_orientation
        if drawing_sheet is not None:
            updated_page_settings.drawing_sheet = str(drawing_sheet)

        if user_page_size_mm is not None:
            if "x_mm" not in user_page_size_mm or "y_mm" not in user_page_size_mm:
                raise KiCadLookupError(
                    "user_page_size_mm must include both x_mm and y_mm."
                )

            normalized_user_page_size = {
                "x_nm": self._millimeters_to_nanometers(user_page_size_mm["x_mm"]),
                "y_nm": self._millimeters_to_nanometers(user_page_size_mm["y_mm"]),
                "x_mm": float(user_page_size_mm["x_mm"]),
                "y_mm": float(user_page_size_mm["y_mm"]),
            }
            updated_page_settings.user_page_size = self._make_vector_like(
                getattr(previous_page_settings, "user_page_size", None),
                normalized_user_page_size["x_nm"],
                normalized_user_page_size["y_nm"],
            )

        if not dry_run:
            set_page_settings = getattr(schematic, "set_page_settings", None)
            if not callable(set_page_settings):
                raise KiCadCapabilityError(
                    "The active KiCad schematic does not expose set_page_settings()."
                )
            current_page_settings = (
                set_page_settings(updated_page_settings) or updated_page_settings
            )
        else:
            current_page_settings = updated_page_settings

        return {
            "schematic": self._serialize_schematic(schematic),
            "previous_page_settings": serialize_page_settings(previous_page_settings),
            "page_settings": serialize_page_settings(current_page_settings),
            "requested_changes": {
                "page_size": resolved_page_size,
                "orientation": resolved_orientation,
                "drawing_sheet": drawing_sheet,
                "user_page_size": normalized_user_page_size,
            },
        }

    def _set_schematic_title_block(
        self,
        schematic: Any,
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

        previous_title_block = self._get_schematic_title_block_info(schematic)
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
            updated_title_block.comments = merged_comments

        if not dry_run:
            set_title_block = getattr(schematic, "set_title_block", None)
            if not callable(set_title_block):
                raise KiCadCapabilityError(
                    "The active KiCad schematic does not expose set_title_block()."
                )
            set_title_block(updated_title_block)

        return {
            "schematic": self._serialize_schematic(schematic),
            "previous_title_block": serialize_title_block(previous_title_block),
            "title_block": serialize_title_block(updated_title_block),
            "requested_changes": {
                "title": title,
                "revision": revision,
                "date": date,
                "company": company,
                "comments": {str(key): value for key, value in normalized_comments.items()}
                if normalized_comments is not None
                else None,
            },
        }

    # ------------------------------------------------------------------
    # Item creation
    # ------------------------------------------------------------------
    def _create_schematic_items(
        self,
        schematic: Any,
        *,
        items: Sequence[dict[str, Any]],
        dry_run: bool,
    ) -> dict[str, Any]:
        specs = self._normalize_schematic_item_specs(items)
        preview = self._build_schematic_items(schematic, specs)

        applied = preview
        if not dry_run:
            applied = self._commit_new_schematic_items(schematic, preview)

        return {
            "schematic": self._serialize_schematic(schematic),
            "count": len(applied),
            "requested_specs": len(specs),
            "kinds": [spec["kind"] for spec in specs],
            "created": [serialize_schematic_item(item) for item in applied],
        }

    def _commit_new_schematic_items(self, schematic: Any, preview: Sequence[Any]) -> list[Any]:
        create_items = getattr(schematic, "create_items", None)
        if not callable(create_items):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose create_items(). "
                "Schematic editing requires KiCad 10.x with IPC API enabled."
            )

        try:
            created = create_items(list(preview))
        except TypeError:
            if len(preview) != 1:
                raise
            created = create_items(preview[0])

        resolved = list(self._as_item_sequence(created))
        return resolved or list(preview)

    def _normalize_schematic_item_specs(
        self, items: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not items:
            raise KiCadLookupError("At least one schematic item specification is required.")

        specs: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise KiCadLookupError(f"Schematic item specification {index} must be an object.")

            kind = str(item.get("kind", "")).strip().lower()
            if kind not in SCH_CREATE_ITEM_KINDS:
                raise KiCadLookupError(
                    f"Unsupported schematic item kind {item.get('kind')!r} at position {index}. "
                    f"Supported kinds: {', '.join(SCH_CREATE_ITEM_KINDS)}."
                )
            specs.append({**item, "kind": kind})

        return specs

    def _build_schematic_items(
        self, schematic: Any, specs: Sequence[dict[str, Any]]
    ) -> list[Any]:
        built: list[Any] = []
        for spec in specs:
            built.extend(self._build_schematic_items_from_spec(schematic, spec))

        if not built:
            raise KiCadLookupError("The provided schematic item specifications produced no items.")

        return built

    def _build_schematic_items_from_spec(
        self, schematic: Any, spec: dict[str, Any]
    ) -> list[Any]:
        kind = spec["kind"]
        if kind in ("wire", "bus"):
            return self._build_schematic_line_items(schematic, spec, kind)
        if kind == "junction":
            return [self._build_schematic_junction_item(schematic, spec)]
        if kind == "no_connect":
            return [self._build_schematic_no_connect_item(schematic, spec)]
        if kind in SCH_LABEL_KINDS:
            return [self._build_schematic_label_item(schematic, spec, kind)]
        if kind == "text":
            return [self._build_schematic_text_item(schematic, spec)]
        if kind == "symbol":
            return [self._build_schematic_symbol_item(schematic, spec)]

        raise KiCadLookupError(f"Unsupported schematic item kind {kind!r}.")

    def _build_schematic_line_items(
        self, schematic: Any, spec: dict[str, Any], kind: str
    ) -> list[Any]:
        label = "wire polyline" if kind == "wire" else "bus polyline"
        points = self._normalize_points(spec.get("points"), minimum=2, label=label)
        line_type = self._schematic_enum_value(
            "SchematicLineType",
            "SLT_WIRE" if kind == "wire" else "SLT_BUS",
            fallback=1 if kind == "wire" else 2,
        )
        locked = self._resolve_schematic_locked(spec)

        segments: list[Any] = []
        for start_point, end_point in zip(points, points[1:], strict=False):
            line = self._new_schematic_item(
                schematic,
                item_type=KiCadSchematicLine,
                getter_name="get_lines",
                kind_name="schematic line",
            )
            self._set_schematic_attribute(
                line, "start", self._point_vector(schematic, start_point), label
            )
            self._set_schematic_attribute(
                line, "end", self._point_vector(schematic, end_point), label
            )

            self._set_schematic_attribute(line, "type", line_type, label)
            if locked is not None:
                self._set_schematic_attribute(line, "locked", locked, label)
            segments.append(line)

        return segments

    def _build_schematic_junction_item(self, schematic: Any, spec: dict[str, Any]) -> Any:
        junction = self._new_schematic_item(
            schematic,
            item_type=KiCadJunction,
            getter_name="get_junctions",
            kind_name="junction",
        )
        position = self._required_schematic_point(schematic, spec, label="junction")
        self._set_schematic_attribute(junction, "position", position, "junction")

        diameter_mm = spec.get("diameter_mm")
        if diameter_mm is not None:
            self._set_schematic_attribute(
                junction,
                "diameter",
                self._validate_positive_measurement_mm(diameter_mm, field_name="diameter_mm"),
                "junction",
            )

        locked = self._resolve_schematic_locked(spec)
        if locked is not None:
            self._set_schematic_attribute(junction, "locked", locked, "junction")

        return junction

    def _build_schematic_no_connect_item(self, schematic: Any, spec: dict[str, Any]) -> Any:
        marker = self._new_schematic_item(
            schematic,
            item_type=KiCadNoConnectMarker,
            getter_name="get_no_connects",
            kind_name="no-connect marker",
        )
        self._set_schematic_attribute(
            marker,
            "position",
            self._required_schematic_point(schematic, spec, label="no-connect marker"),
            "no-connect marker",
        )

        locked = self._resolve_schematic_locked(spec)
        if locked is not None:
            self._set_schematic_attribute(marker, "locked", locked, "no-connect marker")

        return marker

    def _build_schematic_label_item(
        self, schematic: Any, spec: dict[str, Any], kind: str
    ) -> Any:
        item_type = SCH_CREATABLE_ITEM_TYPES[kind]
        label = self._new_schematic_item(
            schematic,
            item_type=item_type,
            getter_name="get_labels",
            kind_name=f"{kind.replace('_', ' ')}",
        )

        text = self._resolve_required_schematic_text(spec, label=kind)
        self._set_schematic_attribute(label, "text", self._create_schematic_text(text), kind)
        self._set_schematic_attribute(
            label,
            "position",
            self._required_schematic_point(schematic, spec, label=kind),
            kind,
        )

        spin_style = self._resolve_schematic_spin_style(spec.get("spin_style"), label=kind)
        if spin_style is not None:
            self._set_schematic_attribute(label, "spin_style", spin_style, kind)

        if kind in ("global_label", "hierarchical_label"):
            shape = self._resolve_schematic_label_shape(spec.get("shape"), label=kind)
            if shape is not None:
                self._set_schematic_attribute(label, "shape", shape, kind)

        locked = self._resolve_schematic_locked(spec)
        if locked is not None:
            self._set_schematic_attribute(label, "locked", locked, kind)

        return label

    def _build_schematic_text_item(self, schematic: Any, spec: dict[str, Any]) -> Any:
        text_item = self._new_schematic_item(
            schematic,
            item_type=KiCadSchematicText,
            getter_name="get_text",
            kind_name="text item",
        )

        text = self._resolve_required_schematic_text(spec, label="text item", key="text")
        self._set_schematic_attribute(text_item, "value", text, "text item")
        self._set_schematic_attribute(
            text_item,
            "position",
            self._required_schematic_point(schematic, spec, label="text item"),
            "text item",
        )

        locked = self._resolve_schematic_locked(spec)
        if locked is not None:
            self._set_schematic_attribute(text_item, "locked", locked, "text item")

        return text_item

    def _build_schematic_symbol_item(self, schematic: Any, spec: dict[str, Any]) -> Any:
        instance = self._new_schematic_item(
            schematic,
            item_type=KiCadSchematicSymbolInstance,
            getter_name="get_symbols",
            kind_name="symbol instance",
        )

        self._set_schematic_attribute(
            instance,
            "position",
            self._required_schematic_point(schematic, spec, label="symbol"),
            "symbol",
        )

        for field_name in ("reference", "value"):
            field_value = spec.get(field_name)
            if field_value is not None:
                self._set_schematic_attribute(instance, field_name, str(field_value), "symbol")

        unit = spec.get("unit")
        if unit is not None:
            self._set_schematic_attribute(instance, "unit", int(unit), "symbol")

        body_style = spec.get("body_style")
        if body_style is not None:
            self._set_schematic_attribute(instance, "body_style", int(body_style), "symbol")

        if spec.get("locked"):
            self._set_schematic_attribute(instance, "locked", True, "symbol")

        lib_id = spec.get("lib_id")
        if lib_id is not None:
            definition = self._create_schematic_symbol_definition(str(lib_id))
            if definition is not None:
                self._set_schematic_attribute(instance, "definition", definition, "symbol")

        return instance

    def _create_schematic_symbol_definition(self, lib_id: str) -> Any:
        if KiCadSchematicSymbol is None or KiCadLibraryIdentifier is None:
            return None
        if ":" not in lib_id:
            raise KiCadLookupError(
                f"Symbol library identifier {lib_id!r} must use the 'library:symbol' form."
            )

        library_nickname, entry_name = lib_id.split(":", 1)
        identifier = KiCadLibraryIdentifier()
        self._set_schematic_attribute(identifier, "library", library_nickname, "symbol")
        self._set_schematic_attribute(identifier, "name", entry_name, "symbol")

        definition = KiCadSchematicSymbol()
        self._set_schematic_attribute(definition, "id", identifier, "symbol")
        return definition

    def _new_schematic_item(
        self,
        schematic: Any,
        *,
        item_type: Any,
        getter_name: str,
        kind_name: str,
    ) -> Any:
        if item_type is None:
            raise KiCadCapabilityError(
                f"The installed kicad-python runtime does not expose a class for {kind_name} items."
            )

        try:
            return item_type()
        except Exception:  # noqa: BLE001 - fall back to cloning an existing item of the same type
            pass

        getter = getattr(schematic, getter_name, None)
        if callable(getter):
            try:
                existing = list(getter())
            except Exception:  # noqa: BLE001
                existing = []
            if existing:
                try:
                    return type(existing[0])()
                except Exception as exc:  # noqa: BLE001
                    raise KiCadCapabilityError(
                        f"Unable to construct a new {kind_name} for the active schematic."
                    ) from exc

        raise KiCadCapabilityError(
            f"Unable to construct a new {kind_name} for the active schematic."
        )

    def _set_schematic_attribute(self, item: Any, name: str, value: Any, label: str) -> None:
        if value is None:
            return
        try:
            setattr(item, name, value)
        except AttributeError as exc:
            raise KiCadCapabilityError(
                f"The installed kicad-python runtime cannot set {name!r} on {label} items; "
                "the KiCad version in use may not support this property."
            ) from exc

    def _create_schematic_text(self, value: str) -> Any:
        if KiCadText is None:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose kipy.common_types.Text."
            )

        text = KiCadText()
        self._set_schematic_attribute(text, "value", value, "text")
        return text

    def _apply_schematic_text_field(self, item: Any, value: str) -> None:
        """Set the text payload of a label or text item, honoring kipy's wrapper types."""
        if KiCadSchematicText is not None and isinstance(item, KiCadSchematicText):
            self._set_schematic_attribute(item, "value", value, "schematic item")
            return

        for label_type in (KiCadLocalLabel, KiCadGlobalLabel, KiCadHierarchicalLabel):
            if label_type is not None and isinstance(item, label_type):
                self._set_schematic_attribute(
                    item, "text", self._create_schematic_text(value), "schematic item"
                )
                return

        if hasattr(item, "value"):
            self._set_schematic_attribute(item, "value", value, "schematic item")
        else:
            self._set_schematic_attribute(item, "text", value, "schematic item")

    def _required_schematic_point(
        self, schematic: Any, spec: dict[str, Any], *, label: str
    ) -> Any:
        x_mm = spec.get("x_mm")
        y_mm = spec.get("y_mm")
        if x_mm is None or y_mm is None:
            raise KiCadLookupError(f"The {label} requires both x_mm and y_mm.")

        return self._schematic_vector(
            schematic,
            self._millimeters_to_nanometers(float(x_mm)),
            self._millimeters_to_nanometers(float(y_mm)),
        )

    def _point_vector(self, schematic: Any, point: dict[str, float | int]) -> Any:
        return self._schematic_vector(schematic, int(point["x_nm"]), int(point["y_nm"]))

    def _schematic_vector(self, schematic: Any, x_nm: int, y_nm: int) -> Any:
        sample_vector = self._find_schematic_sample_vector(schematic)
        if sample_vector is not None:
            return self._make_vector_like(sample_vector, x_nm, y_nm)

        return self._construct_vector(None, x_nm, y_nm)

    def _find_schematic_sample_vector(self, schematic: Any) -> Any | None:
        for getter_name, attribute_name in (
            ("get_symbols", "position"),
            ("get_junctions", "position"),
            ("get_labels", "position"),
            ("get_text", "position"),
            ("get_no_connects", "position"),
        ):
            getter = getattr(schematic, getter_name, None)
            if not callable(getter):
                continue
            try:
                existing = list(getter())
            except Exception:  # noqa: BLE001
                continue
            for item in existing:
                vector = getattr(item, attribute_name, None)
                if vector is not None:
                    return vector

        return None

    def _resolve_required_schematic_text(
        self, spec: dict[str, Any], *, label: str, key: str = "text"
    ) -> str:
        text = spec.get(key)
        if text is None or str(text) == "":
            raise KiCadLookupError(f"The {label} requires a non-empty {key} value.")
        return str(text)

    def _resolve_schematic_locked(self, spec: dict[str, Any]) -> bool | None:
        if "locked" not in spec or spec.get("locked") is None:
            return None
        return bool(spec.get("locked"))

    def _schematic_enum_value(self, enum_name: str, member_name: str, *, fallback: int) -> int:
        proto = KiCadSchematicProto
        if proto is None:
            return fallback

        enum_type = getattr(proto, enum_name, None)
        member = getattr(enum_type, member_name, None) if enum_type is not None else None
        if member is None:
            return fallback

        return int(member)

    def _resolve_schematic_spin_style(self, value: Any, *, label: str) -> int | None:
        if value is None:
            return None

        member = SCH_LABEL_SPIN_STYLE_NAMES.get(str(value).strip().lower())
        if member is None:
            raise KiCadLookupError(
                f"Unsupported spin_style {value!r} for {label}. "
                f"Supported values: {', '.join(sorted(SCH_LABEL_SPIN_STYLE_NAMES))}."
            )

        return self._schematic_enum_value(
            "SchematicLabelSpinStyle", member, fallback=SCH_LABEL_SPIN_STYLE_FALLBACK[member]
        )

    def _resolve_schematic_label_shape(self, value: Any, *, label: str) -> int | None:
        if value is None:
            return None

        member = SCH_LABEL_SHAPE_NAMES.get(str(value).strip().lower())
        if member is None:
            raise KiCadLookupError(
                f"Unsupported shape {value!r} for {label}. "
                f"Supported values: {', '.join(sorted(SCH_LABEL_SHAPE_NAMES))}."
            )

        return self._schematic_enum_value(
            "SchematicLabelShape", member, fallback=SCH_LABEL_SHAPE_FALLBACK[member]
        )

    # ------------------------------------------------------------------
    # Item update / deletion
    # ------------------------------------------------------------------
    def _update_schematic_items(
        self,
        schematic: Any,
        *,
        updates: Sequence[dict[str, Any]],
        dry_run: bool,
    ) -> dict[str, Any]:
        if not updates:
            raise KiCadLookupError("At least one schematic item update is required.")

        changed: list[Any] = []
        for index, update in enumerate(updates, start=1):
            if not isinstance(update, dict):
                raise KiCadLookupError(f"Schematic item update {index} must be an object.")

            item_id = self._extract_schematic_update_id(update, index=index)
            item = self._resolve_schematic_items_by_ids(schematic, [item_id])[0]

            applied_fields = self._apply_schematic_update(schematic, item, update)
            if not applied_fields:
                raise KiCadLookupError(
                    f"Schematic item update {index} does not change any supported field. "
                    f"Supported fields: {', '.join(SCH_UPDATABLE_FIELDS)}."
                )

            changed.append((item, applied_fields))

        if not dry_run:
            self._commit_schematic_updates(schematic, [item for item, _ in changed])

        return {
            "schematic": self._serialize_schematic(schematic),
            "count": len(changed),
            "updated": [
                {"fields": fields, **serialize_schematic_item(item)}
                for item, fields in changed
            ],
        }

    def _extract_schematic_update_id(self, update: dict[str, Any], *, index: int) -> str:
        item_id = update.get("item_id", update.get("id"))
        if item_id is None or str(item_id) == "":
            raise KiCadLookupError(
                f"Schematic item update {index} requires an item_id."
            )
        return str(item_id)

    def _apply_schematic_update(
        self, schematic: Any, item: Any, update: dict[str, Any]
    ) -> list[str]:
        applied_fields: list[str] = []

        position_requested = update.get("x_mm") is not None or update.get("y_mm") is not None
        if position_requested:
            x_mm = update.get("x_mm")
            y_mm = update.get("y_mm")
            if x_mm is None or y_mm is None:
                raise KiCadLookupError(
                    "Repositioning a schematic item requires both x_mm and y_mm."
                )

            self._set_schematic_attribute(
                item,
                "position",
                self._schematic_vector(
                    schematic,
                    self._millimeters_to_nanometers(float(x_mm)),
                    self._millimeters_to_nanometers(float(y_mm)),
                ),
                "schematic item",
            )
            applied_fields.extend(["x_mm", "y_mm"])

        if update.get("text") is not None:
            self._apply_schematic_text_field(item, str(update["text"]))
            applied_fields.append("text")

        for field_name in ("reference", "value"):
            if update.get(field_name) is not None:
                self._set_schematic_attribute(
                    item, field_name, str(update[field_name]), "schematic item"
                )
                applied_fields.append(field_name)

        for field_name in ("unit", "body_style"):
            if update.get(field_name) is not None:
                self._set_schematic_attribute(
                    item, field_name, int(update[field_name]), "schematic item"
                )
                applied_fields.append(field_name)

        spin_style = self._resolve_schematic_spin_style(
            update.get("spin_style"), label="schematic item"
        )
        if spin_style is not None:
            self._set_schematic_attribute(item, "spin_style", spin_style, "schematic item")
            applied_fields.append("spin_style")

        shape = self._resolve_schematic_label_shape(update.get("shape"), label="schematic item")
        if shape is not None:
            self._set_schematic_attribute(item, "shape", shape, "schematic item")
            applied_fields.append("shape")

        if update.get("diameter_mm") is not None:
            self._set_schematic_attribute(
                item,
                "diameter",
                self._validate_positive_measurement_mm(
                    update["diameter_mm"], field_name="diameter_mm"
                ),
                "schematic item",
            )
            applied_fields.append("diameter_mm")

        if update.get("locked") is not None:
            self._set_schematic_attribute(item, "locked", bool(update["locked"]), "schematic item")
            applied_fields.append("locked")

        return applied_fields

    def _commit_schematic_updates(self, schematic: Any, items: Sequence[Any]) -> None:
        update_items = getattr(schematic, "update_items", None)
        if not callable(update_items):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose update_items()."
            )

        try:
            update_items(list(items))
        except TypeError:
            if len(items) != 1:
                raise
            update_items(items[0])

    def _remove_schematic_items(
        self,
        schematic: Any,
        *,
        item_ids: Sequence[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        items = self._resolve_schematic_items_by_ids(schematic, item_ids)

        if not dry_run:
            remove_items = getattr(schematic, "remove_items", None)
            if not callable(remove_items):
                raise KiCadCapabilityError(
                    "The active KiCad schematic does not expose remove_items()."
                )
            try:
                remove_items(items)
            except TypeError:
                if len(items) != 1:
                    raise
                remove_items(items[0])

        return {
            "schematic": self._serialize_schematic(schematic),
            "count": len(items),
            "removed": [serialize_schematic_item(item) for item in items],
        }

    def _save_schematic(self, schematic: Any, dry_run: bool) -> dict[str, Any]:
        if not dry_run:
            save = getattr(schematic, "save", None)
            if not callable(save):
                raise KiCadCapabilityError("The active KiCad schematic does not expose save().")
            save()

        return {"schematic": self._serialize_schematic(schematic)}

    # ------------------------------------------------------------------
    # Additional read helpers
    # ------------------------------------------------------------------
    def _get_schematic_items(
        self,
        schematic: Any,
        *,
        limit: int,
        kinds: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        get_items = getattr(schematic, "get_items", None)
        if not callable(get_items):
            raise KiCadCapabilityError("The active KiCad schematic does not expose get_items().")

        items = list(get_items())
        requested_kinds = self._normalize_schematic_kind_filter(kinds)
        selected = [
            item
            for item in items
            if requested_kinds is None or self._schematic_item_kind(item) in requested_kinds
        ]

        return {
            "schematic": self._serialize_schematic(schematic),
            "total": len(items),
            "count": min(len(selected), limit),
            "truncated": len(selected) > limit,
            "kinds": sorted(requested_kinds) if requested_kinds is not None else None,
            "items": [serialize_schematic_item(item) for item in selected[:limit]],
        }

    def _get_schematic_symbols(self, schematic: Any, *, limit: int) -> dict[str, Any]:
        symbols = self._collect_schematic_items(schematic, "get_symbols", "symbols")
        return {
            "schematic": self._serialize_schematic(schematic),
            "total": len(symbols),
            "count": min(len(symbols), limit),
            "truncated": len(symbols) > limit,
            "symbols": [serialize_schematic_item(symbol) for symbol in symbols[:limit]],
        }

    def _get_schematic_labels(self, schematic: Any, *, limit: int) -> dict[str, Any]:
        labels = self._collect_schematic_items(schematic, "get_labels", "labels")
        return {
            "schematic": self._serialize_schematic(schematic),
            "total": len(labels),
            "count": min(len(labels), limit),
            "truncated": len(labels) > limit,
            "labels": [serialize_schematic_item(label) for label in labels[:limit]],
        }

    def _collect_schematic_items(self, schematic: Any, getter_name: str, label: str) -> list[Any]:
        getter = getattr(schematic, getter_name, None)
        if not callable(getter):
            raise KiCadCapabilityError(
                f"The active KiCad schematic does not expose {getter_name}() and cannot list "
                f"{label}."
            )
        return list(getter())

    def _normalize_schematic_kind_filter(
        self, kinds: Sequence[str] | None
    ) -> set[str] | None:
        if not kinds:
            return None

        normalized: set[str] = set()
        for kind in kinds:
            value = str(kind).strip().lower()
            if not value:
                continue
            if value not in SCH_CREATE_ITEM_KINDS:
                raise KiCadLookupError(
                    f"Unsupported schematic item kind {kind!r}. "
                    f"Supported kinds: {', '.join(SCH_CREATE_ITEM_KINDS)}."
                )
            normalized.add(value)

        return normalized or None

    def _schematic_item_kind(self, item: Any) -> str | None:
        for kind, item_type in SCH_CREATABLE_ITEM_TYPES.items():
            if item_type is not None and isinstance(item, item_type):
                return kind
        return None

    def _get_schematic_as_string(self, schematic: Any) -> dict[str, Any]:
        get_as_string = getattr(schematic, "get_as_string", None)
        if not callable(get_as_string):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_as_string()."
            )

        content = get_as_string()
        return {
            "schematic": self._serialize_schematic(schematic),
            "content": content,
            "length": len(content) if isinstance(content, str) else None,
        }

    def _get_schematic_selection_as_string(self, schematic: Any) -> dict[str, Any]:
        get_selection_as_string = getattr(schematic, "get_selection_as_string", None)
        if not callable(get_selection_as_string):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_selection_as_string()."
            )

        content = get_selection_as_string()
        return {
            "schematic": self._serialize_schematic(schematic),
            "content": content,
            "length": len(content) if isinstance(content, str) else None,
        }

    def _is_schematic_document_modified(self, schematic: Any) -> dict[str, Any]:
        is_modified = getattr(schematic, "is_document_modified", None)
        if not callable(is_modified):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose is_document_modified()."
            )

        return {
            "schematic": self._serialize_schematic(schematic),
            "modified": bool(is_modified()),
        }

    # ------------------------------------------------------------------
    # Design variants
    # ------------------------------------------------------------------
    def _variants_handler(self, schematic: Any) -> Any:
        for method_name in (
            "get_variants",
            "add_variant",
            "delete_variant",
            "rename_variant",
            "copy_variant",
            "set_variant_description",
            "get_current_variant",
            "set_current_variant",
        ):
            if not callable(getattr(schematic, method_name, None)):
                raise KiCadCapabilityError(
                    "The active KiCad schematic does not expose design variant commands. "
                    "Design variants require KiCad 11 or a KiCad build with variant IPC support."
                )
            return schematic
        return schematic

    def _schematic_variant_summary(self, schematic: Any) -> list[dict[str, Any]]:
        variants = self._variants_handler(schematic).get_variants()
        summary: list[dict[str, Any]] = []
        for variant in variants or []:
            summary.append(
                {
                    "name": getattr(variant, "name", None),
                    "description": getattr(variant, "description", None),
                }
            )
        return summary

    def _get_schematic_variants(self, schematic: Any) -> dict[str, Any]:
        return {
            "schematic": self._serialize_schematic(schematic),
            "count": len(self._schematic_variant_summary(schematic)),
            "variants": self._schematic_variant_summary(schematic),
            "current": self._variants_handler(schematic).get_current_variant(),
        }

    def _get_current_schematic_variant(self, schematic: Any) -> dict[str, Any]:
        return {
            "schematic": self._serialize_schematic(schematic),
            "current": self._variants_handler(schematic).get_current_variant(),
        }

    def _add_schematic_variant(
        self, schematic: Any, *, name: str, description: str | None, dry_run: bool
    ) -> dict[str, Any]:
        variant_name = self._require_variant_name(name)
        handler = self._variants_handler(schematic)

        if variant_name in {entry["name"] for entry in self._schematic_variant_summary(schematic)}:
            raise KiCadLookupError(f"A schematic variant named {variant_name!r} already exists.")

        if not dry_run:
            handler.add_variant(variant_name, description)

        return {
            "schematic": self._serialize_schematic(schematic),
            "variant": {"name": variant_name, "description": description},
            "variants": self._schematic_variant_summary(schematic) if not dry_run else None,
        }

    def _delete_schematic_variant(
        self, schematic: Any, *, name: str, dry_run: bool
    ) -> dict[str, Any]:
        variant_name = self._require_variant_name(name)
        handler = self._variants_handler(schematic)

        self._require_existing_variant(schematic, variant_name)

        if not dry_run:
            handler.delete_variant(variant_name)

        return {
            "schematic": self._serialize_schematic(schematic),
            "variant": variant_name,
            "variants": self._schematic_variant_summary(schematic) if not dry_run else None,
        }

    def _rename_schematic_variant(
        self, schematic: Any, *, old_name: str, new_name: str, dry_run: bool
    ) -> dict[str, Any]:
        source_name = self._require_variant_name(old_name, field_name="old_name")
        target_name = self._require_variant_name(new_name, field_name="new_name")
        handler = self._variants_handler(schematic)

        self._require_existing_variant(schematic, source_name, field_name="old_name")
        if target_name in {entry["name"] for entry in self._schematic_variant_summary(schematic)}:
            raise KiCadLookupError(f"A schematic variant named {target_name!r} already exists.")

        if not dry_run:
            handler.rename_variant(source_name, target_name)

        return {
            "schematic": self._serialize_schematic(schematic),
            "renamed": {"from": source_name, "to": target_name},
            "variants": self._schematic_variant_summary(schematic) if not dry_run else None,
        }

    def _copy_schematic_variant(
        self,
        schematic: Any,
        *,
        old_name: str,
        new_name: str,
        new_description: str | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        source_name = self._require_variant_name(old_name, field_name="old_name")
        target_name = self._require_variant_name(new_name, field_name="new_name")
        handler = self._variants_handler(schematic)

        self._require_existing_variant(schematic, source_name, field_name="old_name")
        if target_name in {entry["name"] for entry in self._schematic_variant_summary(schematic)}:
            raise KiCadLookupError(f"A schematic variant named {target_name!r} already exists.")

        if not dry_run:
            handler.copy_variant(source_name, target_name, new_description)

        return {
            "schematic": self._serialize_schematic(schematic),
            "copied": {"from": source_name, "to": target_name},
            "new_description": new_description,
            "variants": self._schematic_variant_summary(schematic) if not dry_run else None,
        }

    def _set_schematic_variant_description(
        self, schematic: Any, *, name: str, description: str, dry_run: bool
    ) -> dict[str, Any]:
        variant_name = self._require_variant_name(name)
        handler = self._variants_handler(schematic)

        previous = self._require_existing_variant(schematic, variant_name)

        if not dry_run:
            handler.set_variant_description(variant_name, description)

        return {
            "schematic": self._serialize_schematic(schematic),
            "variant": variant_name,
            "previous_description": previous,
            "description": description,
        }

    def _set_current_schematic_variant(
        self, schematic: Any, *, name: str | None, dry_run: bool
    ) -> dict[str, Any]:
        handler = self._variants_handler(schematic)

        # KiCad treats an empty variant name as "back to the default variant", so accept
        # both an omitted name and an explicitly empty string.
        variant_name: str | None = None
        if name is not None and str(name).strip() != "":
            variant_name = self._require_variant_name(name)
            self._require_existing_variant(schematic, variant_name)

        if not dry_run:
            handler.set_current_variant(variant_name)

        return {
            "schematic": self._serialize_schematic(schematic),
            "current": variant_name,
        }

    def _require_variant_name(self, name: Any, *, field_name: str = "name") -> str:
        if name is None or str(name).strip() == "":
            raise KiCadLookupError(f"A non-empty {field_name} is required for variant commands.")
        return str(name).strip()

    def _require_existing_variant(
        self, schematic: Any, name: str, *, field_name: str = "name"
    ) -> Any:
        for entry in self._schematic_variant_summary(schematic):
            if entry["name"] == name:
                return entry.get("description")

        known = sorted(
            entry["name"] for entry in self._schematic_variant_summary(schematic) if entry["name"]
        )
        raise KiCadLookupError(
            f"No schematic variant named {name!r} exists ({field_name}). "
            f"Known variants: {', '.join(known) if known else 'none'}."
        )

    def _serialize_schematic(self, schematic: Any) -> dict[str, Any]:
        return {
            "name": getattr(schematic, "name", None),
            "document": serialize_document(getattr(schematic, "document", None)),
        }

    def _get_schematic_page_settings_info(self, schematic: Any) -> Any:
        get_page_settings = getattr(schematic, "get_page_settings", None)
        if not callable(get_page_settings):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_page_settings()."
            )
        return get_page_settings()

    def _resolve_schematic_items_by_ids(self, schematic: Any, item_ids: Sequence[str]) -> list[Any]:
        normalized_item_ids = self._normalize_item_ids(item_ids)
        get_items_by_id = getattr(schematic, "get_items_by_id", None)
        if not callable(get_items_by_id):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_items_by_id()."
            )

        try:
            from kipy.proto.common.types import KIID as KiCadKIID
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose kipy.proto.common.types.KIID. "
                "Schematic hit-test MCP tools require a newer binding build with schematic "
                "item lookup support."
            ) from exc

        lookup_ids = []
        for normalized_item_id in normalized_item_ids:
            lookup_id = KiCadKIID()
            lookup_id.value = normalized_item_id
            lookup_ids.append(lookup_id)

        resolved_items = list(get_items_by_id(lookup_ids))
        resolved_map = {
            serialize_identifier(getattr(item, "id", "")).strip().lower(): item
            for item in resolved_items
            if serialize_identifier(getattr(item, "id", "")).strip()
        }

        missing_item_ids = [
            item_id for item_id in normalized_item_ids if item_id.lower() not in resolved_map
        ]
        if missing_item_ids:
            raise KiCadLookupError(
                "Unable to find schematic item(s) with id(s): "
                + ", ".join(repr(item_id) for item_id in missing_item_ids)
            )

        return [resolved_map[item_id.lower()] for item_id in normalized_item_ids]

    def _get_schematic_title_block_info(self, schematic: Any) -> Any:
        get_title_block = getattr(schematic, "get_title_block", None)
        if not callable(get_title_block):
            raise KiCadCapabilityError(
                "The active KiCad schematic does not expose get_title_block()."
            )
        return get_title_block()

    def _create_schematic_plot_settings(
        self,
        plot_settings: dict[str, Any] | None,
    ) -> Any:
        if plot_settings is None:
            return None

        if not isinstance(plot_settings, dict):
            raise KiCadLookupError("plot_settings must be an object when provided.")

        try:
            from kipy.schematic_jobs import PlotSettings as KiCadSchematicPlotSettings
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose kipy.schematic_jobs."
                "PlotSettings(). Schematic export MCP tools require a newer binding build "
                "with schematic plot export wrapper support."
            ) from exc

        supported_fields = {
            "drawing_sheet",
            "default_font",
            "variant",
            "plot_all",
            "plot_drawing_sheet",
            "plot_pages",
            "show_hop_over",
            "black_and_white",
            "page_size",
            "use_background_color",
            "min_pen_width",
            "theme",
        }
        unknown_fields = sorted(set(plot_settings) - supported_fields)
        if unknown_fields:
            unknown_list = ", ".join(unknown_fields)
            raise KiCadLookupError(
                f"Unsupported plot_settings fields: {unknown_list}."
            )

        result = KiCadSchematicPlotSettings()

        for field_name in ("drawing_sheet", "default_font", "variant", "theme"):
            if field_name in plot_settings and plot_settings[field_name] is not None:
                setattr(result, field_name, str(plot_settings[field_name]))

        for field_name in (
            "plot_all",
            "plot_drawing_sheet",
            "show_hop_over",
            "black_and_white",
            "use_background_color",
        ):
            if field_name not in plot_settings or plot_settings[field_name] is None:
                continue

            field_value = plot_settings[field_name]
            if not isinstance(field_value, bool):
                raise KiCadLookupError(f"plot_settings.{field_name} must be a boolean.")
            setattr(result, field_name, field_value)

        if "page_size" in plot_settings and plot_settings["page_size"] is not None:
            result.page_size = self._coerce_enum_value(
                plot_settings["page_size"],
                field_name="plot_settings.page_size",
            )

        if "min_pen_width" in plot_settings and plot_settings["min_pen_width"] is not None:
            min_pen_width = plot_settings["min_pen_width"]
            if isinstance(min_pen_width, bool) or not isinstance(min_pen_width, int):
                raise KiCadLookupError("plot_settings.min_pen_width must be an integer.")
            result.min_pen_width = min_pen_width

        if "plot_pages" in plot_settings and plot_settings["plot_pages"] is not None:
            raw_plot_pages = plot_settings["plot_pages"]
            if isinstance(raw_plot_pages, (str, bytes)) or not isinstance(raw_plot_pages, Sequence):
                raise KiCadLookupError("plot_settings.plot_pages must be a list of strings.")
            result.plot_pages = self._normalize_non_empty_strings(
                list(raw_plot_pages),
                field_name="plot_pages",
            )

        return result

    def _create_schematic_bom_format_settings(
        self,
        format_settings: dict[str, Any] | None,
    ) -> Any:
        if format_settings is None:
            return None

        if not isinstance(format_settings, dict):
            raise KiCadLookupError("format_settings must be an object when provided.")

        try:
            from kipy.schematic_jobs import BOMFormatSettings as KiCadSchematicBOMFormatSettings
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose "
                "kipy.schematic_jobs.BOMFormatSettings(). Schematic BOM MCP tools require "
                "a newer binding build with BOM export wrapper support."
            ) from exc

        supported_fields = {
            "preset_name",
            "field_delimiter",
            "string_delimiter",
            "ref_delimiter",
            "ref_range_delimiter",
            "keep_tabs",
            "keep_line_breaks",
        }
        unknown_fields = sorted(set(format_settings) - supported_fields)
        if unknown_fields:
            unknown_list = ", ".join(unknown_fields)
            raise KiCadLookupError(
                f"Unsupported format_settings fields: {unknown_list}."
            )

        result = KiCadSchematicBOMFormatSettings()

        for field_name in (
            "preset_name",
            "field_delimiter",
            "string_delimiter",
            "ref_delimiter",
            "ref_range_delimiter",
        ):
            if field_name in format_settings and format_settings[field_name] is not None:
                setattr(result, field_name, str(format_settings[field_name]))

        for field_name in ("keep_tabs", "keep_line_breaks"):
            if field_name not in format_settings or format_settings[field_name] is None:
                continue

            field_value = format_settings[field_name]
            if not isinstance(field_value, bool):
                raise KiCadLookupError(f"format_settings.{field_name} must be a boolean.")
            setattr(result, field_name, field_value)

        return result

    def _create_schematic_bom_field_settings(
        self,
        field_settings: dict[str, Any] | None,
    ) -> Any:
        if field_settings is None:
            return None

        if not isinstance(field_settings, dict):
            raise KiCadLookupError("field_settings must be an object when provided.")

        try:
            from kipy.schematic_jobs import BOMField as KiCadSchematicBOMField
            from kipy.schematic_jobs import BOMFieldSettings as KiCadSchematicBOMFieldSettings
        except ModuleNotFoundError as exc:
            raise KiCadCapabilityError(
                "The installed kicad-python runtime does not expose "
                "kipy.schematic_jobs.BOMFieldSettings(). Schematic BOM MCP tools require "
                "a newer binding build with BOM export wrapper support."
            ) from exc

        supported_fields = {
            "preset_name",
            "fields",
            "sort_field",
            "sort_direction",
            "filter",
        }
        unknown_fields = sorted(set(field_settings) - supported_fields)
        if unknown_fields:
            unknown_list = ", ".join(unknown_fields)
            raise KiCadLookupError(
                f"Unsupported field_settings fields: {unknown_list}."
            )

        result = KiCadSchematicBOMFieldSettings()

        for field_name in ("preset_name", "sort_field", "filter"):
            if field_name in field_settings and field_settings[field_name] is not None:
                setattr(result, field_name, str(field_settings[field_name]))

        if "sort_direction" in field_settings and field_settings["sort_direction"] is not None:
            result.sort_direction = self._coerce_enum_value(
                field_settings["sort_direction"],
                field_name="field_settings.sort_direction",
            )

        if "fields" in field_settings and field_settings["fields"] is not None:
            raw_fields = field_settings["fields"]
            if isinstance(raw_fields, (str, bytes)) or not isinstance(raw_fields, Sequence):
                raise KiCadLookupError("field_settings.fields must be a list of objects.")

            resolved_fields = []
            for index, raw_field in enumerate(raw_fields):
                if not isinstance(raw_field, dict):
                    raise KiCadLookupError(
                        f"field_settings.fields[{index}] must be an object."
                    )

                supported_field_keys = {"name", "label", "group_by"}
                unknown_field_keys = sorted(set(raw_field) - supported_field_keys)
                if unknown_field_keys:
                    unknown_list = ", ".join(unknown_field_keys)
                    raise KiCadLookupError(
                        f"Unsupported field_settings.fields[{index}] fields: {unknown_list}."
                    )

                field_name = str(raw_field.get("name", "")).strip()
                if not field_name:
                    raise KiCadLookupError(
                        f"field_settings.fields[{index}].name must be a non-empty string."
                    )

                resolved_field = KiCadSchematicBOMField()
                resolved_field.name = field_name

                if "label" in raw_field and raw_field["label"] is not None:
                    resolved_field.label = str(raw_field["label"])

                if "group_by" in raw_field and raw_field["group_by"] is not None:
                    group_by = raw_field["group_by"]
                    if not isinstance(group_by, bool):
                        raise KiCadLookupError(
                            f"field_settings.fields[{index}].group_by must be a boolean."
                        )
                    resolved_field.group_by = group_by

                resolved_fields.append(resolved_field)

            result.fields = resolved_fields

        return result

