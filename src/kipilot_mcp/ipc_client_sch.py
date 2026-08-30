"""Schematic-specific KiCad IPC client mixin."""

from __future__ import annotations

from pathlib import Path

from .ipc_client_core import *  # noqa: F401,F403
from .serializers import (
    serialize_schematic_bom_field_settings,
    serialize_schematic_bom_format_settings,
)

DEFAULT_SCHEMATIC_NETLIST_FORMAT = 2


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
            current_page_settings = set_page_settings(updated_page_settings) or updated_page_settings
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
                "Schematic hit-test MCP tools require a newer binding build with schematic item lookup support."
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

