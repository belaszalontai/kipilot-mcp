"""Lookup and search helpers for KiCad board objects."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import KiCadLookupError
from .serializers import serialize_identifier

NANOMETERS_PER_MILLIMETER = 1_000_000


@dataclass(frozen=True)
class BoundingBoxFilter:
    """Normalized board-area filter in nanometers."""

    x_min_nm: int
    y_min_nm: int
    x_max_nm: int
    y_max_nm: int

    @classmethod
    def from_query(cls, area: dict[str, float | int] | None) -> BoundingBoxFilter | None:
        if area is None:
            return None

        required_keys = ("x_min_mm", "y_min_mm", "x_max_mm", "y_max_mm")
        missing_keys = [key for key in required_keys if area.get(key) is None]
        if missing_keys:
            missing_list = ", ".join(missing_keys)
            raise KiCadLookupError(
                "Area filter requires x_min_mm, y_min_mm, x_max_mm, and y_max_mm. "
                f"Missing: {missing_list}."
            )

        x_min_nm = _millimeters_to_nanometers(area["x_min_mm"])
        y_min_nm = _millimeters_to_nanometers(area["y_min_mm"])
        x_max_nm = _millimeters_to_nanometers(area["x_max_mm"])
        y_max_nm = _millimeters_to_nanometers(area["y_max_mm"])

        if x_min_nm > x_max_nm or y_min_nm > y_max_nm:
            raise KiCadLookupError(
                "Area filter bounds are invalid: min coordinates must be less "
                "than or equal to max coordinates."
            )

        return cls(
            x_min_nm=x_min_nm,
            y_min_nm=y_min_nm,
            x_max_nm=x_max_nm,
            y_max_nm=y_max_nm,
        )

    def to_query_dict(self) -> dict[str, float]:
        return {
            "x_min_mm": self.x_min_nm / NANOMETERS_PER_MILLIMETER,
            "y_min_mm": self.y_min_nm / NANOMETERS_PER_MILLIMETER,
            "x_max_mm": self.x_max_nm / NANOMETERS_PER_MILLIMETER,
            "y_max_mm": self.y_max_nm / NANOMETERS_PER_MILLIMETER,
        }


def resolve_layer_id(board: Any, layer: int | str | None) -> int | None:
    """Resolve a board layer from either a numeric ID or a user-visible layer name."""

    if layer is None:
        return None
    if isinstance(layer, int):
        return layer

    text = str(layer).strip()
    if not text:
        return None
    if text.lstrip("+-").isdigit():
        return int(text)

    normalized = text.lower()
    for layer_id in iter_known_layer_ids(board):
        layer_name = _get_layer_name(board, layer_id)
        if layer_name is not None and layer_name.lower() == normalized:
            return layer_id

    raise KiCadLookupError(f"Layer {layer!r} was not found on the current board.")


def resolve_net(board: Any, net_name: str) -> Any:
    """Resolve a net by case-insensitive exact name match."""

    target = net_name.strip().lower()
    for net in board.get_nets():
        if str(getattr(net, "name", "")).strip().lower() == target:
            return net

    raise KiCadLookupError(f"Net {net_name!r} was not found on the current board.")


def resolve_footprint(
    board: Any,
    *,
    reference: str | None = None,
    footprint_id: str | None = None,
) -> Any:
    """Resolve a single footprint by exact reference or UUID-like ID."""

    normalized_reference = (reference or "").strip().lower()
    normalized_id = (footprint_id or "").strip().lower()
    if not normalized_reference and not normalized_id:
        raise KiCadLookupError("Footprint lookup requires either reference or footprint_id.")

    matches = []

    for footprint in board.get_footprints():
        footprint_reference = (
            _field_text(getattr(footprint, "reference_field", None)).strip().lower()
        )
        current_id = serialize_identifier(getattr(footprint, "id", "")).strip().lower()

        if normalized_id and current_id != normalized_id:
            continue
        if normalized_reference and footprint_reference != normalized_reference:
            continue

        matches.append(footprint)

    if not matches:
        target_description = footprint_id or reference or "<unspecified>"
        raise KiCadLookupError(
            f"Footprint {target_description!r} was not found on the current board."
        )
    if len(matches) > 1:
        target_description = reference or footprint_id or "<unspecified>"
        raise KiCadLookupError(
            f"Footprint lookup for {target_description!r} matched multiple "
            "items; use the footprint ID to disambiguate."
        )

    return matches[0]


def item_matches_layer(item: Any, layer_id: int) -> bool:
    """Return whether an item belongs to the resolved layer."""

    return layer_id in set(iter_item_layer_ids(item))


def filter_items_by_area(
    board: Any, items: Sequence[Any], area: BoundingBoxFilter | None
) -> list[Any]:
    """Return only items whose point or bounding box intersects the given area."""

    if area is None:
        return list(items)

    return [item for item in items if item_intersects_area(board, item, area)]


def item_intersects_area(board: Any, item: Any, area: BoundingBoxFilter) -> bool:
    """Check whether an item intersects a query area using bounding boxes when available."""

    item_box = get_item_bounding_box(board, item)
    if item_box is not None:
        left, top, right, bottom = _box_edges(item_box)
    else:
        position = getattr(item, "position", None)
        if position is None:
            return False
        left = right = int(getattr(position, "x", 0))
        top = bottom = int(getattr(position, "y", 0))

    return not (
        right < area.x_min_nm
        or left > area.x_max_nm
        or bottom < area.y_min_nm
        or top > area.y_max_nm
    )


def get_item_bounding_box(board: Any, item: Any) -> Any | None:
    """Retrieve an item's bounding box from either the item or the board API."""

    item_bounding_box = getattr(item, "bounding_box", None)
    if callable(item_bounding_box):
        try:
            return item_bounding_box()
        except Exception:  # noqa: BLE001
            pass

    board_bounding_box = getattr(board, "get_item_bounding_box", None)
    if callable(board_bounding_box):
        try:
            return board_bounding_box(item)
        except TypeError:
            try:
                return board_bounding_box(item, include_text=False)
            except Exception:  # noqa: BLE001
                return None
        except Exception:  # noqa: BLE001
            return None

    return None


def iter_known_layer_ids(board: Any) -> list[int]:
    """Collect a stable set of layer IDs visible from board settings and items."""

    layer_ids: list[int] = []
    seen: set[int] = set()

    def add(layer_id: int | None) -> None:
        if layer_id is None or layer_id in seen:
            return
        seen.add(layer_id)
        layer_ids.append(layer_id)

    for method_name in ("get_enabled_layers", "get_visible_layers"):
        method = getattr(board, method_name, None)
        if not callable(method):
            continue
        for layer_id in _as_sequence(method()):
            if isinstance(layer_id, int):
                add(layer_id)

    for method_name in (
        "get_footprints",
        "get_tracks",
        "get_vias",
        "get_zones",
        "get_shapes",
        "get_text",
    ):
        method = getattr(board, method_name, None)
        if not callable(method):
            continue
        for item in method():
            for layer_id in iter_item_layer_ids(item):
                add(layer_id)

    return layer_ids


def iter_item_layer_ids(item: Any) -> list[int]:
    """Collect all board layers associated with an item."""

    layer_ids: list[int] = []

    layer = getattr(item, "layer", None)
    if isinstance(layer, int):
        layer_ids.append(layer)

    layers = getattr(item, "layers", None)
    for layer_id in _as_sequence(layers):
        if isinstance(layer_id, int) and layer_id not in layer_ids:
            layer_ids.append(layer_id)

    padstack = getattr(item, "padstack", None)
    padstack_layers = getattr(padstack, "layers", None)
    for layer_id in _as_sequence(padstack_layers):
        if isinstance(layer_id, int) and layer_id not in layer_ids:
            layer_ids.append(layer_id)

    return layer_ids


def _get_layer_name(board: Any, layer_id: int) -> str | None:
    method = getattr(board, "get_layer_name", None)
    if not callable(method):
        return None

    try:
        return method(layer_id)
    except Exception:  # noqa: BLE001
        return None


def _field_text(field: Any) -> str:
    text = getattr(field, "text", None)
    return str(getattr(text, "value", ""))


def _millimeters_to_nanometers(value: float | int) -> int:
    return int(round(float(value) * NANOMETERS_PER_MILLIMETER))


def _box_edges(box: Any) -> tuple[int, int, int, int]:
    top_left = getattr(box, "top_left", None)
    bottom_right = getattr(box, "bottom_right", None)
    if top_left is not None and bottom_right is not None:
        left = int(min(getattr(top_left, "x", 0), getattr(bottom_right, "x", 0)))
        right = int(max(getattr(top_left, "x", 0), getattr(bottom_right, "x", 0)))
        top = int(min(getattr(top_left, "y", 0), getattr(bottom_right, "y", 0)))
        bottom = int(max(getattr(top_left, "y", 0), getattr(bottom_right, "y", 0)))
        return left, top, right, bottom

    position = getattr(box, "position", None)
    if position is None:
        position = getattr(box, "pos", None)
    size = getattr(box, "size", None)
    if position is not None and size is not None:
        x0 = int(getattr(position, "x", 0))
        y0 = int(getattr(position, "y", 0))
        x1 = x0 + int(getattr(size, "x", 0))
        y1 = y0 + int(getattr(size, "y", 0))
        left = min(x0, x1)
        right = max(x0, x1)
        top = min(y0, y1)
        bottom = max(y0, y1)
        return left, top, right, bottom
    raise KiCadLookupError("Bounding box data is incomplete for area filtering.")


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    if isinstance(value, Iterable):
        return list(value)
    return [value]
