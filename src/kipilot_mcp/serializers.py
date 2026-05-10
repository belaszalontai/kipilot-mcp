"""Serialization helpers for KiCad IPC wrapper responses."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

NANOMETERS_PER_MILLIMETER = 1_000_000
PROTOBUF_VALUE_PATTERN = re.compile(r'^value:\s*"(?P<value>.+)"$', re.DOTALL)


def nanometers_to_millimeters(value: int | float | None) -> float | None:
    if value is None:
        return None

    return value / NANOMETERS_PER_MILLIMETER


def serialize_document(document: Any) -> dict[str, Any] | None:
    if document is None:
        return None

    project = getattr(document, "project", None)
    result: dict[str, Any] = {
        "type": str(getattr(document, "type", "")),
        "board_filename": getattr(document, "board_filename", ""),
        "project": {
            "name": getattr(project, "name", ""),
            "path": getattr(project, "path", ""),
        },
    }

    path = getattr(document, "path", "")
    if path:
        result["path"] = path

    return result


def serialize_project(project: Any) -> dict[str, Any] | None:
    if project is None:
        return None

    return {
        "name": getattr(project, "name", ""),
        "path": getattr(project, "path", ""),
        "document": serialize_document(getattr(project, "document", None)),
    }


def serialize_title_block(title_block: Any) -> dict[str, Any] | None:
    if title_block is None:
        return None

    comments = getattr(title_block, "comments", None)
    return {
        "title": getattr(title_block, "title", ""),
        "revision": getattr(title_block, "revision", ""),
        "date": getattr(title_block, "date", ""),
        "company": getattr(title_block, "company", ""),
        "comments": {str(key): value for key, value in dict(comments or {}).items()},
    }


def serialize_text_variables(variables: Any) -> dict[str, Any]:
    items: list[tuple[str, str]] = []

    if variables is None:
        pass
    elif isinstance(variables, dict):
        items = [(str(key), str(value)) for key, value in variables.items()]
    elif hasattr(variables, "items"):
        items = [(str(key), str(value)) for key, value in variables.items()]
    elif hasattr(variables, "variables"):
        nested = variables.variables
        if isinstance(nested, dict):
            items = [(str(key), str(value)) for key, value in nested.items()]
        elif hasattr(nested, "items"):
            items = [(str(key), str(value)) for key, value in nested.items()]
    else:
        items = [(str(index), str(value)) for index, value in enumerate(_as_sequence(variables))]

    items.sort(key=lambda item: item[0])

    return {
        "count": len(items),
        "values": {name: value for name, value in items},
        "variables": [
            {
                "name": name,
                "value": value,
            }
            for name, value in items
        ],
    }


def serialize_vector(vector: Any) -> dict[str, float | int] | None:
    if vector is None:
        return None

    x_nanometers = getattr(vector, "x", None)
    y_nanometers = getattr(vector, "y", None)
    if x_nanometers is None or y_nanometers is None:
        return None

    return {
        "x_nm": x_nanometers,
        "y_nm": y_nanometers,
        "x_mm": nanometers_to_millimeters(x_nanometers),
        "y_mm": nanometers_to_millimeters(y_nanometers),
    }


def serialize_box(box: Any) -> dict[str, Any] | None:
    if box is None:
        return None

    top_left = serialize_vector(getattr(box, "top_left", None))
    bottom_right = serialize_vector(getattr(box, "bottom_right", None))
    position = serialize_vector(getattr(box, "position", None))
    if position is None:
        position = serialize_vector(getattr(box, "pos", None))
    size = serialize_vector(getattr(box, "size", None))

    result: dict[str, Any] = {}
    if top_left is not None:
        result["top_left"] = top_left
    if bottom_right is not None:
        result["bottom_right"] = bottom_right
    if position is not None:
        result["position"] = position
    if size is not None:
        result["size"] = size

    return result or None


def merge_boxes(boxes: Sequence[dict[str, Any] | None]) -> dict[str, Any] | None:
    corners: list[dict[str, float | int]] = []
    for box in boxes:
        if box is None:
            continue
        top_left = box.get("top_left")
        bottom_right = box.get("bottom_right")
        if top_left is None or bottom_right is None:
            continue
        corners.extend([top_left, bottom_right])

    if not corners:
        return None

    x_values = [float(corner["x_nm"]) for corner in corners]
    y_values = [float(corner["y_nm"]) for corner in corners]

    return {
        "top_left": {
            "x_nm": min(x_values),
            "y_nm": min(y_values),
            "x_mm": nanometers_to_millimeters(min(x_values)),
            "y_mm": nanometers_to_millimeters(min(y_values)),
        },
        "bottom_right": {
            "x_nm": max(x_values),
            "y_nm": max(y_values),
            "x_mm": nanometers_to_millimeters(max(x_values)),
            "y_mm": nanometers_to_millimeters(max(y_values)),
        },
    }


def serialize_angle(angle: Any) -> dict[str, Any] | None:
    if angle is None:
        return None

    degrees = _coerce_float(getattr(angle, "degrees", None))
    if degrees is None:
        degrees = _coerce_float(_maybe_call(angle, "as_degrees"))
    if degrees is None:
        degrees = _coerce_float(angle)

    radians = _coerce_float(getattr(angle, "radians", None))
    if radians is None:
        radians = _coerce_float(_maybe_call(angle, "as_radians"))

    return {
        "text": str(angle),
        "degrees": degrees,
        "radians": radians,
    }


def serialize_layer(layer_id: Any, board: Any | None = None) -> dict[str, Any] | None:
    if layer_id is None:
        return None

    name = None
    get_layer_name = getattr(board, "get_layer_name", None)
    if callable(get_layer_name):
        try:
            name = get_layer_name(layer_id)
        except Exception:  # noqa: BLE001
            name = None

    return {
        "id": layer_id,
        "name": name,
    }


def serialize_net(net: Any) -> dict[str, Any] | None:
    if net is None:
        return None

    return {
        "name": getattr(net, "name", ""),
        "code": getattr(net, "code", None),
    }


def serialize_net_class(net_class: Any) -> dict[str, Any] | None:
    if net_class is None:
        return None

    result: dict[str, Any] = {
        "name": getattr(net_class, "name", ""),
        "description": getattr(net_class, "description", ""),
    }

    for field_name in (
        "clearance",
        "track_width",
        "via_diameter",
        "via_drill",
        "diff_pair_gap",
        "diff_pair_width",
        "diff_pair_via_gap",
    ):
        value = getattr(net_class, field_name, None)
        if value is None:
            continue
        result[f"{field_name}_nm"] = value
        result[f"{field_name}_mm"] = nanometers_to_millimeters(value)

    members = getattr(net_class, "nets", None)
    if members is None:
        members = getattr(net_class, "net_names", None)
    if members is not None:
        result["net_names"] = [str(getattr(net, "name", net)) for net in _as_sequence(members)]

    return result


def serialize_footprint(footprint: Any) -> dict[str, Any]:
    orientation = getattr(footprint, "orientation", None)
    return {
        "id": serialize_identifier(getattr(footprint, "id", "")),
        "reference": field_text(getattr(footprint, "reference_field", None)),
        "value": field_text(getattr(footprint, "value_field", None)),
        "position": serialize_vector(getattr(footprint, "position", None)),
        "orientation": _format_angle_text(orientation),
        "layer": getattr(footprint, "layer", None),
        "locked": getattr(footprint, "locked", None),
    }


def serialize_track(track: Any, board: Any | None = None) -> dict[str, Any]:
    length_nm = _coerce_float(_maybe_call(track, "length"))
    result = {
        "id": serialize_identifier(getattr(track, "id", "")),
        "kind": type(track).__name__,
        "start": serialize_vector(getattr(track, "start", None)),
        "end": serialize_vector(getattr(track, "end", None)),
        "layer": serialize_layer(getattr(track, "layer", None), board),
        "net": serialize_net(getattr(track, "net", None)),
        "locked": getattr(track, "locked", None),
        "width_nm": getattr(track, "width", None),
        "width_mm": nanometers_to_millimeters(getattr(track, "width", None)),
        "length_nm": length_nm,
        "length_mm": nanometers_to_millimeters(length_nm),
        "bounding_box": serialize_box(_maybe_call(track, "bounding_box")),
    }

    mid = serialize_vector(getattr(track, "mid", None))
    if mid is not None:
        result["mid"] = mid

    return result


def serialize_via(via: Any, board: Any | None = None) -> dict[str, Any]:
    return {
        "id": serialize_identifier(getattr(via, "id", "")),
        "kind": type(via).__name__,
        "position": serialize_vector(getattr(via, "position", None)),
        "layer": serialize_layer(getattr(via, "layer", None), board),
        "net": serialize_net(getattr(via, "net", None)),
        "locked": getattr(via, "locked", None),
        "diameter_nm": getattr(via, "diameter", None),
        "diameter_mm": nanometers_to_millimeters(getattr(via, "diameter", None)),
        "drill_diameter_nm": getattr(via, "drill_diameter", None),
        "drill_diameter_mm": nanometers_to_millimeters(getattr(via, "drill_diameter", None)),
        "type": getattr(via, "type", None),
    }


def serialize_zone(zone: Any, board: Any | None = None) -> dict[str, Any]:
    return {
        "id": serialize_identifier(getattr(zone, "id", "")),
        "kind": type(zone).__name__,
        "name": getattr(zone, "name", ""),
        "net": serialize_net(getattr(zone, "net", None)),
        "layers": [
            serialize_layer(layer, board) for layer in _as_sequence(getattr(zone, "layers", []))
        ],
        "locked": getattr(zone, "locked", None),
        "filled": getattr(zone, "filled", None),
        "priority": getattr(zone, "priority", None),
        "type": getattr(zone, "type", None),
        "bounding_box": serialize_box(_maybe_call(zone, "bounding_box")),
        "outline": serialize_polygon(getattr(zone, "outline", None)),
    }


def serialize_board_text(text_item: Any, board: Any | None = None) -> dict[str, Any]:
    result = {
        "id": serialize_identifier(getattr(text_item, "id", "")),
        "kind": type(text_item).__name__,
        "text": _serialize_text_value(text_item),
        "layer": serialize_layer(getattr(text_item, "layer", None), board),
        "locked": getattr(text_item, "locked", None),
    }

    for key in ("position", "top_left", "bottom_right"):
        vector = serialize_vector(getattr(text_item, key, None))
        if vector is not None:
            result[key] = vector

    return result


def serialize_stackup(stackup: Any, board: Any | None = None) -> dict[str, Any]:
    layers = [
        serialize_stackup_layer(layer, board)
        for layer in _as_sequence(getattr(stackup, "layers", []))
    ]
    return {
        "count": len(layers),
        "layers": layers,
    }


def serialize_stackup_layer(layer: Any, board: Any | None = None) -> dict[str, Any]:
    return {
        "layer": serialize_layer(getattr(layer, "layer", None), board),
        "user_name": getattr(layer, "user_name", ""),
        "enabled": getattr(layer, "enabled", None),
        "type": getattr(layer, "type", None),
        "material_name": getattr(layer, "material_name", ""),
        "thickness_nm": getattr(layer, "thickness", None),
        "thickness_mm": nanometers_to_millimeters(getattr(layer, "thickness", None)),
        "dielectric": serialize_dielectric(getattr(layer, "dielectric", None)),
    }


def serialize_dielectric(dielectric: Any) -> dict[str, Any] | None:
    if dielectric is None:
        return None

    layers = [
        {
            "material_name": getattr(entry, "material_name", ""),
            "epsilon_r": getattr(entry, "epsilon_r", None),
            "loss_tangent": getattr(entry, "loss_tangent", None),
            "thickness_nm": getattr(entry, "thickness", None),
            "thickness_mm": nanometers_to_millimeters(getattr(entry, "thickness", None)),
        }
        for entry in _as_sequence(getattr(dielectric, "layers", []))
    ]

    return {
        "layers": layers,
    }


def serialize_shape(shape: Any, board: Any | None = None) -> dict[str, Any]:
    result = {
        "id": serialize_identifier(getattr(shape, "id", "")),
        "kind": type(shape).__name__,
        "layer": serialize_layer(getattr(shape, "layer", None), board),
        "net": serialize_net(getattr(shape, "net", None)),
        "locked": getattr(shape, "locked", None),
        "bounding_box": serialize_box(_maybe_call(shape, "bounding_box")),
    }

    for key in (
        "start",
        "end",
        "mid",
        "center",
        "radius_point",
        "position",
        "top_left",
        "bottom_right",
        "control1",
        "control2",
    ):
        vector = serialize_vector(getattr(shape, key, None))
        if vector is not None:
            result[key] = vector

    value = getattr(shape, "value", None)
    if value is not None:
        result["value"] = value

    return result


def serialize_pad(pad: Any, board: Any | None = None) -> dict[str, Any]:
    padstack = getattr(pad, "padstack", None)
    layers = []
    if padstack is not None:
        layers = [
            serialize_layer(layer, board) for layer in _as_sequence(getattr(padstack, "layers", []))
        ]

    return {
        "id": serialize_identifier(getattr(pad, "id", "")),
        "kind": type(pad).__name__,
        "number": getattr(pad, "number", ""),
        "position": serialize_vector(getattr(pad, "position", None)),
        "net": serialize_net(getattr(pad, "net", None)),
        "pad_type": getattr(pad, "pad_type", None),
        "layers": layers,
    }


def serialize_identifier(value: Any) -> str:
    if value is None:
        return ""

    direct_value = getattr(value, "value", None)
    if isinstance(direct_value, str) and direct_value:
        return direct_value

    text = str(value).strip()
    match = PROTOBUF_VALUE_PATTERN.fullmatch(text)
    if match:
        return match.group("value")

    return text


def serialize_item(item: Any, board: Any | None = None) -> dict[str, Any]:
    if hasattr(item, "reference_field"):
        result = serialize_footprint(item)
        result["kind"] = type(item).__name__
        return result

    if hasattr(item, "number") and hasattr(item, "padstack"):
        return serialize_pad(item, board)

    if hasattr(item, "drill_diameter") and hasattr(item, "diameter"):
        return serialize_via(item, board)

    if hasattr(item, "outline") and hasattr(item, "filled"):
        return serialize_zone(item, board)

    if hasattr(item, "width") and hasattr(item, "start") and hasattr(item, "end"):
        return serialize_track(item, board)

    if hasattr(item, "attributes") and (
        hasattr(item, "position") or hasattr(item, "top_left") or hasattr(item, "bottom_right")
    ):
        return serialize_board_text(item, board)

    return serialize_shape(item, board)


def serialize_polygon(polygon: Any) -> dict[str, Any] | None:
    if polygon is None:
        return None

    outline = _serialize_point_collection(getattr(polygon, "outline", None))
    if not outline:
        outline = _serialize_point_collection(getattr(polygon, "points", None))

    holes = [
        _serialize_point_collection(hole) for hole in _as_sequence(getattr(polygon, "holes", []))
    ]

    result: dict[str, Any] = {}
    if outline:
        result["outline"] = outline
    if holes:
        result["holes"] = holes
    if not result:
        result["text"] = str(polygon)

    return result


def field_text(field: Any) -> str:
    text = getattr(field, "text", None)
    return str(getattr(text, "value", ""))


def _serialize_text_value(text_item: Any) -> str:
    value = getattr(text_item, "value", None)
    if value is None:
        value = getattr(text_item, "text", None)
    if value is None:
        return ""
    return str(value)


def _format_angle_text(angle: Any) -> str:
    if angle is None:
        return ""

    degrees = _coerce_float(getattr(angle, "degrees", None))
    if degrees is None:
        return str(angle)

    if degrees.is_integer():
        return f"{int(degrees)}deg"
    return f"{degrees}deg"


def _serialize_point_collection(points: Any) -> list[dict[str, float | int]]:
    if points is None:
        return []

    if hasattr(points, "nodes"):
        points = points.nodes
    elif hasattr(points, "points"):
        points = points.points

    serialized_points: list[dict[str, float | int]] = []
    for point in _as_sequence(points):
        serialized = serialize_vector(getattr(point, "point", point))
        if serialized is not None:
            serialized_points.append(serialized)

    return serialized_points


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


def _maybe_call(value: Any, method_name: str, *args: Any, **kwargs: Any) -> Any:
    method = getattr(value, method_name, None)
    if callable(method):
        return method(*args, **kwargs)
    return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
