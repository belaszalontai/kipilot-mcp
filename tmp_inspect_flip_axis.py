from collections import defaultdict

from kipy import KiCad

kc = KiCad()
board = kc.get_board()
groups = defaultdict(list)
for fp in board.get_footprints():
    position = getattr(fp, "position", None)
    ref_pos = getattr(getattr(getattr(fp, "reference_field", None), "text", None), "position", None)
    val_pos = getattr(getattr(getattr(fp, "value_field", None), "text", None), "position", None)
    groups[str(getattr(fp, "id", None))].append(
        {
            "ref": str(getattr(getattr(fp.reference_field, "text", None), "value", "")),
            "value": str(getattr(getattr(fp.value_field, "text", None), "value", "")),
            "layer": board.get_layer_name(getattr(fp, "layer", None)),
            "pos": (getattr(position, "x", None), getattr(position, "y", None)),
            "ref_delta": None
            if ref_pos is None or position is None
            else (ref_pos.x - position.x, ref_pos.y - position.y),
            "val_delta": None
            if val_pos is None or position is None
            else (val_pos.x - position.x, val_pos.y - position.y),
        }
    )
for fp_id, entries in groups.items():
    layers = {entry["layer"] for entry in entries}
    if "F.Cu" in layers and "B.Cu" in layers:
        print("footprint_id", fp_id)
        for entry in entries[:8]:
            print(entry)
