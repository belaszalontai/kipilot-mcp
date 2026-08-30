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


def serialize_page_settings(page_settings: Any) -> dict[str, Any] | None:
    if page_settings is None:
        return None

    return {
        "page_size": getattr(page_settings, "page_size", None),
        "orientation": getattr(page_settings, "orientation", None),
        "drawing_sheet": getattr(page_settings, "drawing_sheet", ""),
        "user_page_size": serialize_vector(getattr(page_settings, "user_page_size", None)),
    }


def serialize_schematic_plot_settings(plot_settings: Any) -> dict[str, Any] | None:
    if plot_settings is None:
        return None

    return {
        "drawing_sheet": getattr(plot_settings, "drawing_sheet", ""),
        "default_font": getattr(plot_settings, "default_font", ""),
        "variant": getattr(plot_settings, "variant", ""),
        "plot_all": getattr(plot_settings, "plot_all", None),
        "plot_drawing_sheet": getattr(plot_settings, "plot_drawing_sheet", None),
        "plot_pages": list(getattr(plot_settings, "plot_pages", []) or []),
        "show_hop_over": getattr(plot_settings, "show_hop_over", None),
        "black_and_white": getattr(plot_settings, "black_and_white", None),
        "page_size": getattr(plot_settings, "page_size", None),
        "use_background_color": getattr(plot_settings, "use_background_color", None),
        "min_pen_width": getattr(plot_settings, "min_pen_width", None),
        "theme": getattr(plot_settings, "theme", ""),
    }


def serialize_board_plot_settings(plot_settings: Any) -> dict[str, Any] | None:
    if plot_settings is None:
        return None

    return {
        "layers": list(getattr(plot_settings, "layers", []) or []),
        "common_layers": list(getattr(plot_settings, "common_layers", []) or []),
        "color_theme": getattr(plot_settings, "color_theme", ""),
        "drawing_sheet": getattr(plot_settings, "drawing_sheet", ""),
        "variant": getattr(plot_settings, "variant", ""),
        "mirror": getattr(plot_settings, "mirror", None),
        "black_and_white": getattr(plot_settings, "black_and_white", None),
        "negative": getattr(plot_settings, "negative", None),
        "scale": getattr(plot_settings, "scale", None),
        "sketch_pads_on_fab_layers": getattr(
            plot_settings, "sketch_pads_on_fab_layers", None
        ),
        "hide_dnp_footprints_on_fab_layers": getattr(
            plot_settings, "hide_dnp_footprints_on_fab_layers", None
        ),
        "sketch_dnp_footprints_on_fab_layers": getattr(
            plot_settings, "sketch_dnp_footprints_on_fab_layers", None
        ),
        "crossout_dnp_footprints_on_fab_layers": getattr(
            plot_settings, "crossout_dnp_footprints_on_fab_layers", None
        ),
        "plot_footprint_values": getattr(plot_settings, "plot_footprint_values", None),
        "plot_reference_designators": getattr(
            plot_settings, "plot_reference_designators", None
        ),
        "plot_drawing_sheet": getattr(plot_settings, "plot_drawing_sheet", None),
        "subtract_solder_mask_from_silk": getattr(
            plot_settings, "subtract_solder_mask_from_silk", None
        ),
        "plot_pad_numbers": getattr(plot_settings, "plot_pad_numbers", None),
        "drill_marks": getattr(plot_settings, "drill_marks", None),
        "use_drill_origin": getattr(plot_settings, "use_drill_origin", None),
        "check_zones_before_plot": getattr(
            plot_settings, "check_zones_before_plot", None
        ),
    }


def serialize_schematic_item(item: Any) -> dict[str, Any] | None:
    """Serialize one schematic item to a compact MCP-friendly representation."""
    if item is None:
        return None

    return {
        "id": serialize_identifier(getattr(item, "id", "")),
        "type": getattr(item, "type", None),
        "reference": getattr(item, "reference", None),
        "value": getattr(item, "value", None),
        "text": getattr(item, "text", None),
        "position": serialize_vector(getattr(item, "position", None)),
    }


def serialize_schematic_bom_format_settings(format_settings: Any) -> dict[str, Any] | None:
    if format_settings is None:
        return None

    return {
        "preset_name": getattr(format_settings, "preset_name", ""),
        "field_delimiter": getattr(format_settings, "field_delimiter", ""),
        "string_delimiter": getattr(format_settings, "string_delimiter", ""),
        "ref_delimiter": getattr(format_settings, "ref_delimiter", ""),
        "ref_range_delimiter": getattr(format_settings, "ref_range_delimiter", ""),
        "keep_tabs": getattr(format_settings, "keep_tabs", None),
        "keep_line_breaks": getattr(format_settings, "keep_line_breaks", None),
    }


def serialize_schematic_bom_field(field: Any) -> dict[str, Any] | None:
    if field is None:
        return None

    return {
        "name": getattr(field, "name", ""),
        "label": getattr(field, "label", ""),
        "group_by": getattr(field, "group_by", None),
    }


def serialize_schematic_bom_field_settings(field_settings: Any) -> dict[str, Any] | None:
    if field_settings is None:
        return None

    return {
        "preset_name": getattr(field_settings, "preset_name", ""),
        "fields": [
            serialize_schematic_bom_field(field)
            for field in getattr(field_settings, "fields", [])
        ],
        "sort_field": getattr(field_settings, "sort_field", ""),
        "sort_direction": getattr(field_settings, "sort_direction", None),
        "filter": getattr(field_settings, "filter", ""),
    }


def serialize_job_result(job_result: Any) -> dict[str, Any] | None:
    if job_result is None:
        return None

    output_paths = getattr(job_result, "output_paths", None)
    if output_paths is None:
        raw_output_path = getattr(job_result, "output_path", None)
        if raw_output_path is None:
            output_paths = []
        elif isinstance(raw_output_path, str):
            output_paths = [raw_output_path]
        else:
            output_paths = list(raw_output_path)

    return {
        "succeeded": bool(getattr(job_result, "succeeded", False)),
        "status": getattr(job_result, "status", None),
        "output_paths": list(output_paths),
        "message": getattr(job_result, "message", ""),
    }


def serialize_sheet_path(path: Any) -> dict[str, Any] | None:
    if path is None:
        return None

    identifiers = [serialize_identifier(identifier) for identifier in getattr(path, "path", [])]
    human_readable = getattr(path, "path_human_readable", "") or None

    return {
        "ids": identifiers,
        "text": "/" + "/".join(identifiers),
        "human_readable": human_readable,
    }


def serialize_sheet_instance(sheet: Any) -> dict[str, Any] | None:
    if sheet is None:
        return None

    return {
        "name": getattr(sheet, "name", ""),
        "filename": getattr(sheet, "filename", ""),
        "page_number": getattr(sheet, "page_number", ""),
        "path": serialize_sheet_path(getattr(sheet, "path", None)),
        "children": [serialize_sheet_instance(child) for child in getattr(sheet, "children", [])],
    }


def serialize_schematic_net(schematic_net: Any) -> dict[str, Any] | None:
    if schematic_net is None:
        return None

    return {
        "name": getattr(schematic_net, "name", ""),
        "sheets": [
            {
                "path": serialize_sheet_path(getattr(sheet, "path", None)),
                "item_ids": [serialize_identifier(item) for item in getattr(sheet, "items", [])],
            }
            for sheet in getattr(schematic_net, "sheets", [])
        ],
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


def serialize_text_attributes(attributes: Any) -> dict[str, Any] | None:
    if attributes is None:
        return None

    result = {
        "font_name": getattr(attributes, "font_name", ""),
        "angle_degrees": getattr(attributes, "angle", None),
        "line_spacing": getattr(attributes, "line_spacing", None),
        "italic": getattr(attributes, "italic", None),
        "bold": getattr(attributes, "bold", None),
        "underlined": getattr(attributes, "underlined", None),
        "mirrored": getattr(attributes, "mirrored", None),
        "multiline": getattr(attributes, "multiline", None),
        "keep_upright": getattr(attributes, "keep_upright", None),
        "size": serialize_vector(getattr(attributes, "size", None)),
        "horizontal_alignment": getattr(attributes, "horizontal_alignment", None),
        "vertical_alignment": getattr(attributes, "vertical_alignment", None),
    }

    stroke_width = getattr(attributes, "stroke_width", None)
    if stroke_width is not None:
        result["stroke_width_nm"] = stroke_width
        result["stroke_width_mm"] = nanometers_to_millimeters(stroke_width)

    return result


def serialize_graphics_default(defaults: Any) -> dict[str, Any]:
    line_thickness = getattr(defaults, "line_thickness", None)
    result = {
        "layer_class": getattr(defaults, "layer", None),
        "text_attributes": serialize_text_attributes(getattr(defaults, "text", None)),
    }
    if line_thickness is not None:
        result["line_thickness_nm"] = line_thickness
        result["line_thickness_mm"] = nanometers_to_millimeters(line_thickness)
    return result


def serialize_editor_appearance_settings(settings: Any) -> dict[str, Any] | None:
    if settings is None:
        return None

    return {
        "inactive_layer_display": getattr(settings, "inactive_layer_display", None),
        "net_color_display": getattr(settings, "net_color_display", None),
        "board_flip": getattr(settings, "board_flip", None),
        "ratsnest_display": getattr(settings, "ratsnest_display", None),
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


def serialize_footprint(footprint: Any, board: Any | None = None) -> dict[str, Any]:
    orientation = getattr(footprint, "orientation", None)
    result = {
        "id": serialize_identifier(getattr(footprint, "id", "")),
        "reference": field_text(getattr(footprint, "reference_field", None)),
        "value": field_text(getattr(footprint, "value_field", None)),
        "position": serialize_vector(getattr(footprint, "position", None)),
        "orientation": _format_angle_text(orientation),
        "layer": getattr(footprint, "layer", None),
        "locked": getattr(footprint, "locked", None),
    }

    child_graphics = serialize_footprint_child_graphics(footprint, board)
    if child_graphics is not None:
        result["child_graphics"] = child_graphics

    return result


def serialize_footprint_child_graphics(
    footprint: Any,
    board: Any | None = None,
) -> dict[str, Any] | None:
    definition = getattr(footprint, "definition", None)
    if definition is None:
        return None

    layer_counts: dict[Any, int] = {}
    graphic_item_count = 0
    for item in _as_sequence(getattr(definition, "items", [])):
        child_layers = _get_footprint_child_layers(item)
        if not child_layers:
            continue

        graphic_item_count += 1
        for layer in child_layers:
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

    if graphic_item_count == 0:
        return None

    return {
        "count": graphic_item_count,
        "layers": [
            {
                "layer": serialize_layer(layer, board),
                "count": count,
            }
            for layer, count in layer_counts.items()
        ],
    }


def _get_footprint_child_layers(item: Any) -> list[Any]:
    if item is None:
        return []

    if hasattr(item, "number") and hasattr(item, "padstack"):
        return []

    if type(item).__name__ == "Field":
        item = getattr(item, "text", None)
        if item is None:
            return []

    layer = getattr(item, "layer", None)
    if layer is not None:
        return [layer]

    return [layer_id for layer_id in _as_sequence(getattr(item, "layers", [])) if layer_id is not None]


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


def serialize_barcode(barcode: Any, board: Any | None = None) -> dict[str, Any]:
    result = {
        "id": serialize_identifier(getattr(barcode, "id", "")),
        "kind": type(barcode).__name__,
        "text": getattr(barcode, "text", ""),
        "layer": serialize_layer(getattr(barcode, "layer", None), board),
        "locked": getattr(barcode, "locked", None),
        "position": serialize_vector(getattr(barcode, "position", None)),
        "orientation": serialize_angle(getattr(barcode, "orientation", None)),
        "barcode_kind": getattr(barcode, "kind", None),
        "error_correction": getattr(barcode, "error_correction", None),
        "show_text": getattr(barcode, "show_text", None),
        "knockout": getattr(barcode, "knockout", None),
        "bounding_box": serialize_box(_maybe_call(barcode, "bounding_box")),
    }

    for field_name in ("width", "height", "text_height"):
        value = getattr(barcode, field_name, None)
        if value is None:
            continue
        result[f"{field_name}_nm"] = value
        result[f"{field_name}_mm"] = nanometers_to_millimeters(value)

    knockout_margin = serialize_vector(getattr(barcode, "knockout_margin", None))
    if knockout_margin is not None:
        result["knockout_margin"] = knockout_margin

    return result


def serialize_reference_image(reference_image: Any, board: Any | None = None) -> dict[str, Any]:
    image_data = getattr(reference_image, "image_data", b"")

    result = {
        "id": serialize_identifier(getattr(reference_image, "id", "")),
        "kind": type(reference_image).__name__,
        "layer": serialize_layer(getattr(reference_image, "layer", None), board),
        "locked": getattr(reference_image, "locked", None),
        "position": serialize_vector(getattr(reference_image, "position", None)),
        "transform_origin_offset": serialize_vector(
            getattr(reference_image, "transform_origin_offset", None)
        ),
        "image_scale": getattr(reference_image, "image_scale", None),
        "image_byte_count": len(image_data),
        "bounding_box": serialize_box(_maybe_call(reference_image, "bounding_box")),
    }

    return result


def serialize_dimension(dimension: Any, board: Any | None = None) -> dict[str, Any]:
    result = {
        "id": serialize_identifier(getattr(dimension, "id", "")),
        "kind": type(dimension).__name__,
        "layer": serialize_layer(getattr(dimension, "layer", None), board),
        "locked": getattr(dimension, "locked", None),
        "text": _serialize_text_value(getattr(dimension, "text", None)),
        "override_text_enabled": getattr(dimension, "override_text_enabled", None),
        "bounding_box": serialize_box(_maybe_call(dimension, "bounding_box")),
    }

    override_text = getattr(dimension, "override_text", None)
    if override_text:
        result["override_text"] = override_text

    for field_name in ("prefix", "suffix"):
        value = getattr(dimension, field_name, None)
        if value:
            result[field_name] = value

    for field_name in (
        "unit",
        "unit_format",
        "arrow_direction",
        "precision",
        "text_position",
        "alignment",
        "keep_text_aligned",
        "suppress_trailing_zeroes",
    ):
        value = getattr(dimension, field_name, None)
        if value is not None:
            result[field_name] = value

    for key in ("start", "end", "center", "radius_point"):
        vector = serialize_vector(getattr(dimension, key, None))
        if vector is not None:
            result[key] = vector

    for field_name in (
        "height",
        "extension_height",
        "leader_length",
        "line_thickness",
        "arrow_length",
        "extension_offset",
    ):
        value = getattr(dimension, field_name, None)
        if value is None:
            continue
        result[f"{field_name}_nm"] = value
        result[f"{field_name}_mm"] = nanometers_to_millimeters(value)

    return result


def serialize_group(group: Any, board: Any | None = None) -> dict[str, Any]:
    _ = board
    items = _as_sequence(getattr(group, "items", []))
    item_ids = [
        serialize_identifier(getattr(item, "id", item))
        for item in items
        if serialize_identifier(getattr(item, "id", item))
    ]

    return {
        "id": serialize_identifier(getattr(group, "id", "")),
        "kind": type(group).__name__,
        "name": getattr(group, "name", ""),
        "item_count": len(item_ids),
        "item_ids": item_ids,
    }


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


def serialize_pad(
    pad: Any,
    board: Any | None = None,
    parent_footprint: Any | None = None,
) -> dict[str, Any]:
    padstack = getattr(pad, "padstack", None)
    layers = []
    if padstack is not None:
        layers = [
            serialize_layer(layer, board) for layer in _as_sequence(getattr(padstack, "layers", []))
        ]

    result = {
        "id": serialize_identifier(getattr(pad, "id", "")),
        "kind": type(pad).__name__,
        "number": getattr(pad, "number", ""),
        "position": serialize_vector(getattr(pad, "position", None)),
        "net": serialize_net(getattr(pad, "net", None)),
        "pad_type": getattr(pad, "pad_type", None),
        "layers": layers,
    }

    if parent_footprint is not None:
        result["footprint"] = {
            "id": serialize_identifier(getattr(parent_footprint, "id", "")),
            "reference": field_text(getattr(parent_footprint, "reference_field", None)),
        }

    return result


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
        result = serialize_footprint(item, board)
        result["kind"] = type(item).__name__
        return result

    if hasattr(item, "name") and hasattr(item, "items"):
        return serialize_group(item, board)

    if hasattr(item, "number") and hasattr(item, "padstack"):
        return serialize_pad(item, board)

    if hasattr(item, "drill_diameter") and hasattr(item, "diameter"):
        return serialize_via(item, board)

    if hasattr(item, "image_data") and hasattr(item, "image_scale"):
        return serialize_reference_image(item, board)

    if hasattr(item, "error_correction") and hasattr(item, "show_text"):
        return serialize_barcode(item, board)

    if hasattr(item, "override_text_enabled") and hasattr(item, "text"):
        return serialize_dimension(item, board)

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
