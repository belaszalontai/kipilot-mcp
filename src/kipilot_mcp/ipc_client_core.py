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
    serialize_editor_appearance_settings,
    serialize_job_result,
    merge_boxes,
    serialize_barcode,
    serialize_board_plot_settings,
    serialize_box,
    serialize_board_text,
    serialize_dimension,
    serialize_document,
    serialize_footprint,
    serialize_graphics_default,
    serialize_group,
    serialize_identifier,
    serialize_item,
    serialize_layer,
    serialize_net,
    serialize_net_class,
    serialize_pad,
    serialize_page_settings,
    serialize_polygon,
    serialize_project,
    serialize_reference_image,
    serialize_schematic_net,
    serialize_schematic_item,
    serialize_schematic_plot_settings,
    serialize_shape,
    serialize_sheet_instance,
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
BOARD_ITEM_GETTER_NAMES = (
    "get_footprints",
    "get_tracks",
    "get_vias",
    "get_pads",
    "get_shapes",
    "get_text",
    "get_zones",
    "get_dimensions",
    "get_barcodes",
    "get_reference_images",
    "get_groups",
)
BOARD_ITEM_KIND_GETTERS = {
    "footprint": "get_footprints",
    "footprints": "get_footprints",
    "track": "get_tracks",
    "tracks": "get_tracks",
    "via": "get_vias",
    "vias": "get_vias",
    "pad": "get_pads",
    "pads": "get_pads",
    "shape": "get_shapes",
    "shapes": "get_shapes",
    "text": "get_text",
    "texts": "get_text",
    "zone": "get_zones",
    "zones": "get_zones",
    "dimension": "get_dimensions",
    "dimensions": "get_dimensions",
    "barcode": "get_barcodes",
    "barcodes": "get_barcodes",
    "reference_image": "get_reference_images",
    "reference_images": "get_reference_images",
    "group": "get_groups",
    "groups": "get_groups",
}

logger = logging.getLogger(__name__)

try:
    from kipy import KiCad  # type: ignore[import-not-found]
    from kipy.board_types import to_concrete_board_shape as kipy_to_concrete_board_shape  # type: ignore[import-not-found]
    from kipy.board_types import Track as KiCadTrack  # type: ignore[import-not-found]
    from kipy.board_types import Via as KiCadVia  # type: ignore[import-not-found]
    from kipy.errors import ApiError  # type: ignore[import-not-found]
    from kipy.geometry import (
        PolygonWithHoles as KiCadPolygonWithHoles,
    )  # type: ignore[import-not-found]
    from kipy.geometry import PolyLine as KiCadPolyLine  # type: ignore[import-not-found]
    from kipy.geometry import PolyLineNode as KiCadPolyLineNode  # type: ignore[import-not-found]
    from kipy.geometry import Vector2 as KiCadVector2  # type: ignore[import-not-found]
    from kipy.proto.common.types import DocumentType as KiCadDocumentType  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local environment
    KiCad = None
    KiCadTrack = None
    KiCadVia = None
    kipy_to_concrete_board_shape = None
    KiCadPolyLine = None
    KiCadPolyLineNode = None
    KiCadPolygonWithHoles = None
    KiCadVector2 = None
    KiCadDocumentType = None

    class ApiError(RuntimeError):
        """Fallback API error used when kicad-python is unavailable."""

    _KIPY_IMPORT_ERROR = exc
else:
    _KIPY_IMPORT_ERROR = None


DOCUMENT_TYPE_SCHEMATIC = int(getattr(KiCadDocumentType, "DOCTYPE_SCHEMATIC", 1))
DOCUMENT_TYPE_PCB = int(getattr(KiCadDocumentType, "DOCTYPE_PCB", 3))
DOCUMENT_TYPE_PROJECT = int(getattr(KiCadDocumentType, "DOCTYPE_PROJECT", 6))


class KiCadIpcClientCore:
    """Shared KiCad IPC client behavior."""

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
                    "KiCad IPC is not reachable. Start KiCad 10 or newer, open the target "
                    "editor window (PCB or Schematic), and verify KICAD_API_SOCKET/"
                    "KICAD_API_TOKEN if you are not using the default platform IPC endpoint."
                ),
            )
            result["socket_path"] = self._config.socket_path
            result["client_name"] = self._config.client_name
            return result

    async def get_version_info(self) -> dict[str, Any]:
        """Return version information when the active endpoint exposes it."""

        try:
            return await asyncio.to_thread(self._probe_version_info)
        except Exception as exc:  # noqa: BLE001
            result = self._translate_error(
                exc,
                default_message=(
                    "Unable to query KiCad version metadata through the IPC API. Start KiCad "
                    "10 or newer, open the target editor window (PCB or Schematic), and verify "
                    "KICAD_API_SOCKET/KICAD_API_TOKEN if you are not using the default platform "
                    "IPC endpoint."
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

    async def set_project_text_variables(
        self,
        variables: dict[str, str],
        *,
        merge_mode: str = "merge",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Update project text variables behind the current PCB."""

        return await self._run_project_write(
            lambda project, is_dry_run: self._set_project_text_variables(
                project,
                variables=variables,
                merge_mode=merge_mode,
                dry_run=is_dry_run,
            ),
            default_message="Unable to update project text variables through the IPC API.",
            mutation_name="set_project_text_variables",
            dry_run=dry_run,
        )

    async def get_project_net_classes(self) -> dict[str, Any]:
        """Return project net classes from the active board project."""

        return await self._run_project(
            self._get_project_net_classes,
            default_message="Unable to read project net classes through the IPC API.",
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

    async def _run_project_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        *,
        default_message: str,
        mutation_name: str,
        dry_run: bool = False,
        dangerous: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        try:
            self._assert_mutation_allowed(dry_run=dry_run, dangerous=dangerous, force=force)
            return await asyncio.to_thread(
                self._with_project_write,
                operation,
                mutation_name,
                dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc, default_message=default_message)

    def _probe_connection(self) -> dict[str, Any]:
        return self._with_kicad(self._check_connection)

    def _probe_version_info(self) -> dict[str, Any]:
        return self._with_kicad(self._get_version_info)

    def _check_connection(self, kicad: Any) -> dict[str, Any]:
        ping = getattr(kicad, "ping", None)

        if callable(ping):
            try:
                ping()
            except Exception as exc:  # noqa: BLE001
                if not self._is_no_handler_available(exc):
                    raise

                fallback = self._build_editor_endpoint_status(
                    kicad,
                    version_requested=False,
                )
                if fallback is not None:
                    return fallback

                raise

        version_info = self._read_runtime_version_info(kicad, allow_unavailable=True)
        return {
            "ok": True,
            "socket_path": self._config.socket_path,
            "client_name": self._config.client_name,
            **version_info,
            "message": "KiCad IPC endpoint is reachable.",
        }

    def _get_version_info(self, kicad: Any) -> dict[str, Any]:
        try:
            version_info = self._read_runtime_version_info(kicad, allow_unavailable=False)
        except Exception as exc:  # noqa: BLE001
            if not self._is_no_handler_available(exc):
                raise

            fallback = self._build_editor_endpoint_status(
                kicad,
                version_requested=True,
            )
            if fallback is not None:
                return fallback

            raise

        return {
            "ok": True,
            "socket_path": self._config.socket_path,
            "client_name": self._config.client_name,
            **version_info,
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

    def _with_project_write(
        self,
        operation: Callable[[Any, bool], dict[str, Any]],
        mutation_name: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        result = self._with_project(lambda project: operation(project, dry_run))
        return {
            "ok": True,
            "mutation": mutation_name,
            "dry_run": dry_run,
            "commit_message": None,
            **result,
        }

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
        if document_types:
            documents, _successful_types = self._collect_explicit_documents(
                kicad,
                document_types,
                ignore_unsupported=False,
            )

            return {
                "ok": True,
                "count": len(documents),
                "document_types": list(document_types),
                "documents": documents,
                "source": "explicit_types",
            }

        documents: list[dict[str, Any]] = []
        seen: set[str] = set()
        board_error: Exception | None = None

        try:
            board = kicad.get_board()
        except Exception as exc:  # noqa: BLE001
            board_error = exc
        else:
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

        documents, successful_types = self._collect_explicit_documents(
            kicad,
            (DOCUMENT_TYPE_SCHEMATIC, DOCUMENT_TYPE_PCB, DOCUMENT_TYPE_PROJECT),
            ignore_unsupported=True,
        )

        if documents or successful_types:
            return {
                "ok": True,
                "count": len(documents),
                "documents": documents,
                "document_types": successful_types,
                "source": "explicit_types_fallback",
            }

        if board_error is not None:
            raise board_error

        raise KiCadCapabilityError(
            "Unable to list open KiCad documents from the active IPC endpoint."
        )

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

    def _set_project_text_variables(
        self,
        project: Any,
        *,
        variables: dict[str, str],
        merge_mode: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        get_text_variables = getattr(project, "get_text_variables", None)
        if not callable(get_text_variables):
            raise KiCadCapabilityError(
                "This KiCad binding does not expose project text variables on the active endpoint."
            )

        set_text_variables = getattr(project, "set_text_variables", None)
        if not callable(set_text_variables) and not dry_run:
            raise KiCadCapabilityError(
                "This KiCad binding does not expose project text-variable updates on the active endpoint."
            )

        previous_variables = get_text_variables()
        normalized_variables = {str(key): str(value) for key, value in dict(variables).items()}
        resolved_merge_mode, resolved_merge_mode_name = self._resolve_project_merge_mode(
            merge_mode
        )
        preview_variables = self._apply_project_text_variable_merge(
            previous_variables,
            normalized_variables,
            merge_mode=resolved_merge_mode_name,
        )

        if not dry_run:
            payload = self._coerce_project_text_variables(previous_variables, preview_variables)
            set_text_variables(payload, resolved_merge_mode)

        applied_variables = preview_variables if dry_run else get_text_variables()
        return {
            "project": serialize_project(project),
            "merge_mode": resolved_merge_mode_name,
            "previous_text_variables": serialize_text_variables(previous_variables),
            "requested_text_variables": serialize_text_variables(normalized_variables),
            "text_variables": serialize_text_variables(applied_variables),
        }

    def _resolve_project_merge_mode(self, merge_mode: str) -> tuple[int, str]:
        normalized = str(merge_mode).strip().lower()
        if normalized in {"", "merge", "mmm_merge", "1"}:
            return 1, "merge"
        if normalized in {"replace", "overwrite", "mmm_replace", "2"}:
            return 2, "replace"

        raise KiCadLookupError("merge_mode must be one of: merge, replace.")

    def _apply_project_text_variable_merge(
        self,
        previous_variables: Any,
        requested_variables: dict[str, str],
        *,
        merge_mode: str,
    ) -> dict[str, str]:
        current_values = serialize_text_variables(previous_variables).get("values", {})
        if merge_mode == "replace":
            return dict(requested_variables)

        merged_variables = dict(current_values)
        merged_variables.update(requested_variables)
        return merged_variables

    def _coerce_project_text_variables(self, previous_variables: Any, values: dict[str, str]) -> Any:
        if hasattr(previous_variables, "variables"):
            previous_variables.variables = dict(values)
            return previous_variables

        if isinstance(previous_variables, dict):
            return dict(values)

        return dict(values)

    def _get_project_net_classes(self, project: Any) -> dict[str, Any]:
        net_classes = self._get_project_net_class_items(project)

        return {
            "ok": True,
            "project": serialize_project(project),
            "count": len(net_classes),
            "net_classes": [serialize_net_class(net_class) for net_class in net_classes],
        }

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

    def _make_angle_like(self, current: Any, degrees: float, *, normalize_180: bool = False) -> Any:
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

        normalize_name = "normalize180" if normalize_180 else "normalize"
        normalize = getattr(angle, normalize_name, None)
        if callable(normalize):
            return normalize()

        if not normalize_180:
            fallback_normalize = getattr(angle, "normalize", None)
            if callable(fallback_normalize):
                return fallback_normalize()

        return angle

    def _as_item_sequence(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return list(value)
        return [value]

    def _merge_board_items(self, current_items: Sequence[Any], incoming_items: Sequence[Any]) -> list[Any]:
        merged_items: list[Any] = []
        seen_item_ids: set[str] = set()

        for item in [*current_items, *incoming_items]:
            item_id = serialize_identifier(getattr(item, "id", "")).strip().lower()
            if not item_id or item_id in seen_item_ids:
                continue
            seen_item_ids.add(item_id)
            merged_items.append(item)

        return merged_items

    def _clone_settings_like(self, settings: Any, field_names: Iterable[str]) -> Any:
        try:
            return self._clone_proto_wrapper(settings)
        except Exception:  # noqa: BLE001
            pass

        try:
            clone = type(settings)()
        except Exception:  # noqa: BLE001
            clone = type("GenericSettingsClone", (), {})()

        for field_name in field_names:
            if hasattr(settings, field_name):
                setattr(clone, field_name, getattr(settings, field_name))

        return clone

    def _coerce_enum_value(self, value: int | str | None, *, field_name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value

        normalized = str(value).strip()
        if normalized.lstrip("-").isdigit():
            return int(normalized)

        raise KiCadLookupError(f"{field_name} must be an integer enum value.")

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

    def _read_runtime_version_info(
        self,
        kicad: Any,
        *,
        allow_unavailable: bool,
    ) -> dict[str, Any]:
        get_version = getattr(kicad, "get_version", None)
        if not callable(get_version):
            if allow_unavailable:
                return self._binding_version_info_only(kicad)
            raise KiCadCapabilityError(
                "The active KiCad binding does not expose get_version()."
            )

        try:
            kicad_version = str(get_version())
        except Exception:
            if allow_unavailable:
                raise
            raise

        result = {
            "kicad_version": kicad_version,
            **self._binding_version_info_only(kicad),
        }

        check_version = getattr(kicad, "check_version", None)
        if callable(check_version):
            result["api_version_matches_binding"] = bool(check_version())

        return result

    def _binding_version_info_only(self, kicad: Any) -> dict[str, Any]:
        get_api_version = getattr(kicad, "get_api_version", None)
        if not callable(get_api_version):
            return {"api_version": None}

        return {"api_version": str(get_api_version())}

    def _build_editor_endpoint_status(
        self,
        kicad: Any,
        *,
        version_requested: bool,
    ) -> dict[str, Any] | None:
        endpoint_types = self._probe_editor_endpoint(kicad)
        if endpoint_types is None:
            return None

        endpoint_label = "/".join(endpoint_types) if endpoint_types else "editor"
        result = {
            "ok": True,
            "socket_path": self._config.socket_path,
            "client_name": self._config.client_name,
            "endpoint_types": endpoint_types,
            **self._binding_version_info_only(kicad),
        }

        if version_requested:
            result["kicad_version"] = None
            result["api_version_matches_binding"] = None
            result["message"] = (
                "KiCad IPC endpoint is reachable. The active "
                f"{endpoint_label} endpoint does not expose GetVersion(), so the runtime KiCad "
                "version could not be queried."
            )
            return result

        result["message"] = (
            "KiCad IPC endpoint is reachable. The active "
            f"{endpoint_label} endpoint does not expose common Ping/GetVersion requests."
        )
        return result

    def _probe_editor_endpoint(self, kicad: Any) -> list[str] | None:
        endpoint_types: list[str] = []

        if self._supports_editor_getter(
            kicad,
            getter_name="get_schematic",
            missing_document_fragment="at least one schematic",
        ):
            endpoint_types.append("schematic")

        if self._supports_editor_getter(
            kicad,
            getter_name="get_board",
            missing_document_fragment="at least one board",
        ):
            endpoint_types.append("pcb")

        documents, successful_types = self._collect_explicit_documents(
            kicad,
            (DOCUMENT_TYPE_SCHEMATIC, DOCUMENT_TYPE_PCB),
            ignore_unsupported=True,
        )

        inferred_types = self._infer_endpoint_types_from_documents(documents)
        for endpoint_type in inferred_types:
            if endpoint_type not in endpoint_types:
                endpoint_types.append(endpoint_type)

        if endpoint_types or successful_types:
            return endpoint_types

        return None

    def _supports_editor_getter(
        self,
        kicad: Any,
        *,
        getter_name: str,
        missing_document_fragment: str,
    ) -> bool:
        getter = getattr(kicad, getter_name, None)
        if not callable(getter):
            return False

        try:
            return getter() is not None
        except Exception as exc:  # noqa: BLE001
            if self._is_no_handler_available(exc):
                return False

            if missing_document_fragment in str(exc).lower():
                return True

            raise

    def _collect_explicit_documents(
        self,
        kicad: Any,
        document_types: Sequence[int],
        *,
        ignore_unsupported: bool,
    ) -> tuple[list[dict[str, Any]], list[int]]:
        get_open_documents = getattr(kicad, "get_open_documents", None)
        if not callable(get_open_documents):
            if ignore_unsupported:
                return [], []

            raise KiCadCapabilityError(
                "This KiCad binding does not expose get_open_documents() on the active endpoint."
            )

        documents: list[dict[str, Any]] = []
        seen: set[str] = set()
        successful_types: list[int] = []

        for document_type in document_types:
            try:
                resolved_documents = list(get_open_documents(document_type))
            except Exception as exc:  # noqa: BLE001
                if ignore_unsupported and self._is_no_handler_available(exc):
                    continue

                raise

            successful_types.append(int(document_type))

            for document in resolved_documents:
                self._append_document(documents, seen, document)

        return documents, successful_types

    def _infer_endpoint_types_from_documents(self, documents: Sequence[dict[str, Any]]) -> list[str]:
        endpoint_types: list[str] = []

        if any(doc.get("type") == str(DOCUMENT_TYPE_SCHEMATIC) for doc in documents):
            endpoint_types.append("schematic")

        if any(doc.get("type") == str(DOCUMENT_TYPE_PCB) for doc in documents):
            endpoint_types.append("pcb")

        return endpoint_types

    def _is_no_handler_available(self, exc: Exception) -> bool:
        return isinstance(exc, ApiError) and "no handler available" in str(exc).lower()

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

        if self._is_no_handler_available(exc):
            return {
                "ok": False,
                "message": (
                    "Connected to KiCad IPC, but the active endpoint does not expose this "
                    "request. Open the target editor that owns the API you want to use "
                    "(PCB Editor for board tools, Schematic Editor for schematic tools). If the "
                    "MCP server is launched outside KiCad, set KICAD_API_SOCKET and "
                    "KICAD_API_TOKEN from that editor/plugin environment."
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

