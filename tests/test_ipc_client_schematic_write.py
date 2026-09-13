"""Tests for the schematic write, read and design variant IPC tools.

The client opens a fresh connection per call, so the fakes here share one schematic
instance across every connection the client creates.
"""

from __future__ import annotations

from typing import Any

from kipy.schematic_types import SchematicLine as KipySchematicLine

from kipilot_mcp.config import KiCadIpcConfig
from kipilot_mcp.ipc_client import KiCadIpcClient


class FakeVector:
    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y


class FakeSchematicProjectRef:
    def __init__(self) -> None:
        self.name = "demo"
        self.path = "C:/demo/demo.kicad_pro"


class FakeSchematicDocument:
    def __init__(self) -> None:
        self.type = 2
        self.project = FakeSchematicProjectRef()
        self.path = "C:/demo/demo.kicad_sch"


class FakeSchematicItem:
    """Schematic item exposing the writable attributes the client relies on."""

    def __init__(self, item_id: str, *, x_nm: int = 0, y_nm: int = 0) -> None:
        self.id = item_id
        self.position = FakeVector(x_nm, y_nm)
        self.type = None
        self.text: Any = None
        self.value: Any = None
        self.reference: Any = None
        self.unit: Any = None
        self.body_style: Any = None
        self.spin_style: Any = None
        self.shape: Any = None
        self.diameter: Any = None
        self.locked: Any = None
        self.start: Any = None
        self.end: Any = None


class FakeSchematicVariant:
    def __init__(self, name: str, description: str | None = None) -> None:
        self.name = name
        self.description = description


class FakeSchematicWriter:
    name = "demo.kicad_sch"

    def __init__(self) -> None:
        self.document = FakeSchematicDocument()
        self.items: list[FakeSchematicItem] = []
        self.calls: list[tuple[object, ...]] = []
        self.created_batches: list[list[Any]] = []
        self.updated_batches: list[list[Any]] = []
        self.removed_batches: list[list[Any]] = []
        self.save_calls = 0
        self.modified = True
        self.document_string = "(kicad_sch (version 20250114))"
        self.selection_string = "(wire (pts (xy 0 0) (xy 10 0)))"
        self.variants: list[FakeSchematicVariant] = [
            FakeSchematicVariant("default", "Default variant")
        ]
        self.current_variant: str | None = "default"
        self.variant_calls: list[tuple[object, ...]] = []

    # -- commit handling -------------------------------------------------
    def begin_commit(self) -> str:
        self.calls.append(("begin_commit",))
        return "fake-commit"

    def push_commit(self, commit: str, message: str = "") -> None:
        self.calls.append(("push_commit", commit, message))

    def drop_commit(self, commit: str) -> None:
        self.calls.append(("drop_commit", commit))

    # -- item access -----------------------------------------------------
    def get_items_by_id(self, ids: object | list[object]) -> list[FakeSchematicItem]:
        resolved_ids = ids if isinstance(ids, list) else [ids]
        wanted = {str(getattr(item_id, "value", item_id)).strip().lower() for item_id in resolved_ids}
        return [item for item in self.items if str(item.id).lower() in wanted]

    def get_items(self, types: object = None, sheet_path: object = None) -> list[FakeSchematicItem]:
        return list(self.items)

    def get_lines(self, sheet_path: object = None) -> list[FakeSchematicItem]:
        return [item for item in self.items if item.type is not None]

    def get_symbols(self, sheet_path: object = None) -> list[FakeSchematicItem]:
        return [item for item in self.items if item.reference is not None]

    def get_labels(self, sheet_path: object = None) -> list[FakeSchematicItem]:
        return [item for item in self.items if item.text is not None]

    # -- mutation --------------------------------------------------------
    def create_items(self, items: object) -> list[Any]:
        created = items if isinstance(items, list) else [items]
        self.created_batches.append(list(created))
        self.items.extend(created)
        return list(created)

    def update_items(self, items: object) -> None:
        updated = items if isinstance(items, list) else [items]
        self.updated_batches.append(list(updated))

    def remove_items(self, items: object) -> None:
        removed = items if isinstance(items, list) else [items]
        self.removed_batches.append(list(removed))
        for item in removed:
            if item in self.items:
                self.items.remove(item)

    def save(self) -> None:
        self.save_calls += 1
        self.modified = False

    # -- document access -------------------------------------------------
    def get_as_string(self) -> str:
        return self.document_string

    def get_selection_as_string(self) -> str:
        return self.selection_string

    def is_document_modified(self) -> bool:
        return self.modified

    # -- design variants -------------------------------------------------
    def get_variants(self) -> list[FakeSchematicVariant]:
        return list(self.variants)

    def get_current_variant(self) -> str | None:
        return self.current_variant

    def add_variant(self, name: str, description: str | None = None) -> None:
        self.variant_calls.append(("add_variant", name, description))
        self.variants.append(FakeSchematicVariant(name, description))

    def delete_variant(self, name: str) -> None:
        self.variant_calls.append(("delete_variant", name))
        self.variants = [variant for variant in self.variants if variant.name != name]

    def rename_variant(self, old_name: str, new_name: str) -> None:
        self.variant_calls.append(("rename_variant", old_name, new_name))
        for variant in self.variants:
            if variant.name == old_name:
                variant.name = new_name

    def copy_variant(self, old_name: str, new_name: str, new_description: str | None = None) -> None:
        self.variant_calls.append(("copy_variant", old_name, new_name, new_description))
        for variant in self.variants:
            if variant.name == old_name:
                description = new_description if new_description is not None else variant.description
                self.variants.append(FakeSchematicVariant(new_name, description))

    def set_variant_description(self, name: str, description: str) -> None:
        self.variant_calls.append(("set_variant_description", name, description))
        for variant in self.variants:
            if variant.name == name:
                variant.description = description

    def set_current_variant(self, name: str | None = None) -> None:
        self.variant_calls.append(("set_current_variant", name))
        self.current_variant = name


def _kicad_factory(schematic: FakeSchematicWriter) -> type:
    """Build a fake KiCad class that always hands out the given schematic."""

    class FakeSchematicKiCad:
        def __init__(self, **_kwargs: object) -> None:
            self.schematic = schematic

        def get_schematic(self) -> FakeSchematicWriter:
            return schematic

        def close(self) -> None:
            pass

    return FakeSchematicKiCad


def _client(
    schematic: FakeSchematicWriter | None = None, *, mutations: bool = True
) -> tuple[KiCadIpcClient, FakeSchematicWriter]:
    resolved_schematic = schematic if schematic is not None else FakeSchematicWriter()
    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=mutations),
        kicad_factory=_kicad_factory(resolved_schematic),
    )
    return client, resolved_schematic


async def test_create_schematic_items_requires_enabled_mutations() -> None:
    client, schematic = _client(mutations=False)

    result = await client.create_schematic_items(
        items=[{"kind": "junction", "x_mm": 1.0, "y_mm": 1.0}]
    )

    assert result["ok"] is False
    assert "mutations are disabled" in str(result["message"])
    assert schematic.created_batches == []

    dry_run = await client.create_schematic_items(
        items=[{"kind": "junction", "x_mm": 1.0, "y_mm": 1.0}],
        dry_run=True,
    )
    assert dry_run["ok"] is True


async def test_create_schematic_items_splits_wire_polylines_into_segments() -> None:
    client, schematic = _client()

    result = await client.create_schematic_items(
        items=[
            {
                "kind": "wire",
                "points": [
                    {"x_mm": 10.0, "y_mm": 10.0},
                    {"x_mm": 20.0, "y_mm": 10.0},
                    {"x_mm": 20.0, "y_mm": 20.0},
                ],
            }
        ]
    )

    assert result["ok"] is True
    assert result["mutation"] == "sch_create_items"
    assert result["dry_run"] is False
    assert result["count"] == 2
    assert result["requested_specs"] == 1
    assert result["kinds"] == ["wire"]
    assert result["schematic"]["name"] == "demo.kicad_sch"

    assert len(schematic.created_batches) == 1
    segments = schematic.created_batches[0]
    assert len(segments) == 2
    assert segments[0].start.x == 10_000_000
    assert segments[0].end.x == 20_000_000
    assert segments[1].start.y == 10_000_000
    assert segments[1].end.y == 20_000_000
    assert [segment.type for segment in segments] == [1, 1]
    assert [call[0] for call in schematic.calls] == ["begin_commit", "push_commit"]


async def test_create_schematic_items_dry_run_keeps_document_untouched() -> None:
    client, schematic = _client()

    result = await client.create_schematic_items(
        items=[{"kind": "junction", "x_mm": 5.0, "y_mm": 6.0}],
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["count"] == 1
    assert schematic.created_batches == []
    assert schematic.calls == []


async def test_create_schematic_items_supports_labels_text_buses_and_no_connect() -> None:
    client, schematic = _client()

    result = await client.create_schematic_items(
        items=[
            {
                "kind": "global_label",
                "text": "VCC",
                "x_mm": 1.0,
                "y_mm": 2.0,
                "spin_style": "right",
                "shape": "input",
            },
            {"kind": "text", "text": "Power rail", "x_mm": 3.0, "y_mm": 4.0},
            {
                "kind": "bus",
                "points": [{"x_mm": 0.0, "y_mm": 0.0}, {"x_mm": 0.0, "y_mm": 10.0}],
            },
            {"kind": "no_connect", "x_mm": 7.0, "y_mm": 8.0},
            {"kind": "junction", "x_mm": 9.0, "y_mm": 9.0, "diameter_mm": 0.9144},
        ]
    )

    assert result["ok"] is True
    assert result["count"] == 5

    label, text_item, bus_segment, no_connect, junction = schematic.created_batches[0]

    assert label.text.value == "VCC"
    assert label.spin_style == 3
    assert label.shape == 1
    assert text_item.value == "Power rail"
    assert bus_segment.type == 2
    assert no_connect.position.y == 8_000_000
    assert junction.diameter == 914_400


async def test_create_schematic_items_rejects_invalid_specifications() -> None:
    client, schematic = _client()

    unknown = await client.create_schematic_items(
        items=[{"kind": "netclass_flag", "x_mm": 1.0, "y_mm": 1.0}],
        dry_run=True,
    )
    assert unknown["ok"] is False
    assert "Unsupported schematic item kind" in str(unknown["message"])

    missing = await client.create_schematic_items(
        items=[{"kind": "junction", "x_mm": 1.0}],
        dry_run=True,
    )
    assert missing["ok"] is False
    assert "requires both x_mm and y_mm" in str(missing["message"])

    empty = await client.create_schematic_items(items=[], dry_run=True)
    assert empty["ok"] is False
    assert "At least one schematic item specification is required" in str(empty["message"])

    bad_style = await client.create_schematic_items(
        items=[{"kind": "label", "text": "NET", "x_mm": 1.0, "y_mm": 1.0, "spin_style": "sideways"}],
        dry_run=True,
    )
    assert bad_style["ok"] is False
    assert "Unsupported spin_style" in str(bad_style["message"])

    assert schematic.created_batches == []


async def test_create_schematic_items_reports_missing_capability() -> None:
    schematic = FakeSchematicWriter()
    schematic.create_items = None  # type: ignore[method-assign]
    client, _ = _client(schematic)

    result = await client.create_schematic_items(
        items=[{"kind": "junction", "x_mm": 1.0, "y_mm": 1.0}]
    )

    assert result["ok"] is False
    assert "create_items" in str(result["message"])


async def test_update_schematic_items_applies_position_text_and_fields() -> None:
    schematic = FakeSchematicWriter()
    schematic.items = [
        FakeSchematicItem("label-1"),
        FakeSchematicItem("symbol-1"),
        FakeSchematicItem("wire-1"),
    ]
    client, _ = _client(schematic)

    result = await client.update_schematic_items(
        updates=[
            {"item_id": "label-1", "x_mm": 4.0, "y_mm": 5.0, "text": "GND"},
            {"item_id": "symbol-1", "reference": "R2", "value": "4k7", "unit": 2},
            {"item_id": "wire-1", "locked": True},
        ]
    )

    assert result["ok"] is True
    assert result["count"] == 3
    assert result["updated"][0]["fields"] == ["x_mm", "y_mm", "text"]
    assert result["updated"][1]["fields"] == ["reference", "value", "unit"]
    assert result["updated"][2]["fields"] == ["locked"]

    label, symbol, wire = schematic.items
    assert label.position.x == 4_000_000
    assert label.position.y == 5_000_000
    assert label.value == "GND"
    assert symbol.reference == "R2"
    assert symbol.value == "4k7"
    assert symbol.unit == 2
    assert wire.locked is True
    assert len(schematic.updated_batches) == 1


async def test_update_schematic_items_validates_payload() -> None:
    schematic = FakeSchematicWriter()
    schematic.items = [FakeSchematicItem("label-1")]
    client, _ = _client(schematic)

    no_fields = await client.update_schematic_items(updates=[{"item_id": "label-1"}])
    assert no_fields["ok"] is False
    assert "does not change any supported field" in str(no_fields["message"])

    no_id = await client.update_schematic_items(updates=[{"text": "GND"}])
    assert no_id["ok"] is False
    assert "requires an item_id" in str(no_id["message"])

    partial_move = await client.update_schematic_items(
        updates=[{"item_id": "label-1", "x_mm": 1.0}]
    )
    assert partial_move["ok"] is False
    assert "requires both x_mm and y_mm" in str(partial_move["message"])

    missing_item = await client.update_schematic_items(
        updates=[{"item_id": "unknown-1", "text": "GND"}]
    )
    assert missing_item["ok"] is False
    assert "Unable to find schematic item(s)" in str(missing_item["message"])


async def test_remove_and_save_schematic_items() -> None:
    schematic = FakeSchematicWriter()
    schematic.items = [FakeSchematicItem("symbol-1"), FakeSchematicItem("symbol-2")]
    client, _ = _client(schematic)

    removed = await client.remove_schematic_items(item_ids=["symbol-1"], force=True)

    assert removed["ok"] is True
    assert removed["mutation"] == "sch_remove_items"
    assert removed["count"] == 1
    assert len(schematic.removed_batches) == 1
    assert [item.id for item in schematic.items] == ["symbol-2"]

    saved = await client.save_schematic()
    assert saved["ok"] is True
    assert saved["mutation"] == "sch_save"
    assert schematic.save_calls == 1

    dry_saved = await client.save_schematic(dry_run=True)
    assert dry_saved["ok"] is True
    assert schematic.save_calls == 1


async def test_remove_schematic_items_reports_missing_capability() -> None:
    schematic = FakeSchematicWriter()
    schematic.items = [FakeSchematicItem("symbol-1")]
    schematic.remove_items = None  # type: ignore[method-assign]
    client, _ = _client(schematic)

    result = await client.remove_schematic_items(item_ids=["symbol-1"], force=True)

    assert result["ok"] is False
    assert "remove_items" in str(result["message"])


async def test_remove_schematic_items_requires_force() -> None:
    schematic = FakeSchematicWriter()
    schematic.items = [FakeSchematicItem("symbol-1")]
    client, _ = _client(schematic)

    result = await client.remove_schematic_items(item_ids=["symbol-1"])

    assert result["ok"] is False
    assert "destructive" in str(result["message"])
    assert schematic.removed_batches == []


async def test_get_schematic_items_filters_by_kind_and_reports_truncation() -> None:
    schematic = FakeSchematicWriter()
    wires = [KipySchematicLine() for _ in range(3)]
    for wire in wires:
        wire.type = 1
    schematic.items = [*wires, FakeSchematicItem("label-1")]
    client, _ = _client(schematic)

    result = await client.get_schematic_items(limit=2, kinds=["wire"])

    assert result["total"] == 4
    assert result["count"] == 2
    assert result["truncated"] is True
    assert result["kinds"] == ["wire"]
    assert len(result["items"]) == 2

    unfiltered = await client.get_schematic_items()
    assert unfiltered["total"] == 4
    assert unfiltered["count"] == 4
    assert unfiltered["truncated"] is False
    assert unfiltered["kinds"] is None

    invalid = await client.get_schematic_items(kinds=["nope"])
    assert invalid["ok"] is False
    assert "Unsupported schematic item kind" in str(invalid["message"])


async def test_get_schematic_symbols_and_labels() -> None:
    schematic = FakeSchematicWriter()
    symbol = FakeSchematicItem("symbol-1", x_nm=1_000_000, y_nm=2_000_000)
    symbol.reference = "R1"
    symbol.value = "10k"
    label = FakeSchematicItem("label-1", x_nm=3_000_000, y_nm=4_000_000)
    label.text = "GND"
    schematic.items = [symbol, label]
    client, _ = _client(schematic)

    symbols = await client.get_schematic_symbols()
    labels = await client.get_schematic_labels()

    assert symbols["total"] == 1
    assert symbols["symbols"][0]["reference"] == "R1"
    assert symbols["symbols"][0]["position"] == {
        "x_nm": 1_000_000,
        "y_nm": 2_000_000,
        "x_mm": 1.0,
        "y_mm": 2.0,
    }

    assert labels["total"] == 1
    assert labels["labels"][0]["text"] == "GND"


async def test_schematic_document_strings_and_modified_flag() -> None:
    schematic = FakeSchematicWriter()
    client, _ = _client(schematic)

    document = await client.get_schematic_as_string()
    selection = await client.get_schematic_selection_as_string()
    modified = await client.is_schematic_document_modified()

    assert document["content"] == schematic.document_string
    assert document["length"] == len(schematic.document_string)
    assert selection["content"] == schematic.selection_string
    assert modified["modified"] is True
    assert modified["schematic"]["document"]["path"] == "C:/demo/demo.kicad_sch"


async def test_schematic_document_tools_report_missing_capability() -> None:
    schematic = FakeSchematicWriter()
    schematic.get_as_string = None  # type: ignore[method-assign]
    client, _ = _client(schematic)

    result = await client.get_schematic_as_string()

    assert result["ok"] is False
    assert "get_as_string" in str(result["message"])


async def test_schematic_variant_lifecycle() -> None:
    client, schematic = _client()

    created = await client.add_schematic_variant(name="lite", description="Reduced BOM")
    assert created["ok"] is True
    assert created["variant"] == {"name": "lite", "description": "Reduced BOM"}

    listed = await client.get_schematic_variants()
    assert listed["count"] == 2
    assert [entry["name"] for entry in listed["variants"]] == ["default", "lite"]
    assert listed["current"] == "default"

    renamed = await client.rename_schematic_variant(old_name="lite", new_name="lite2")
    assert renamed["ok"] is True
    assert renamed["renamed"] == {"from": "lite", "to": "lite2"}

    copied = await client.copy_schematic_variant(
        old_name="lite2", new_name="lite3", new_description="Copy"
    )
    assert copied["ok"] is True
    assert copied["copied"] == {"from": "lite2", "to": "lite3"}

    described = await client.set_schematic_variant_description(
        name="lite2", description="Cheaper parts"
    )
    assert described["ok"] is True
    assert described["previous_description"] == "Reduced BOM"

    activated = await client.set_current_schematic_variant(name="lite2")
    assert activated["ok"] is True
    assert activated["current"] == "lite2"

    reset = await client.set_current_schematic_variant(name="")
    assert reset["ok"] is True
    assert reset["current"] is None
    assert schematic.current_variant is None

    reactivated = await client.set_current_schematic_variant(name="lite2")
    assert reactivated["ok"] is True

    current = await client.get_current_schematic_variant()
    assert current["current"] == "lite2"

    deleted = await client.delete_schematic_variant(name="lite3")
    assert deleted["ok"] is True

    assert [variant.name for variant in schematic.variants] == ["default", "lite2"]
    assert schematic.variant_calls == [
        ("add_variant", "lite", "Reduced BOM"),
        ("rename_variant", "lite", "lite2"),
        ("copy_variant", "lite2", "lite3", "Copy"),
        ("set_variant_description", "lite2", "Cheaper parts"),
        ("set_current_variant", "lite2"),
        ("set_current_variant", None),
        ("set_current_variant", "lite2"),
        ("delete_variant", "lite3"),
    ]


async def test_schematic_variant_dry_run_keeps_variants_untouched() -> None:
    client, schematic = _client()

    result = await client.add_schematic_variant(name="lite", dry_run=True)

    assert result["ok"] is True
    assert result["variant"] == {"name": "lite", "description": None}
    assert schematic.variant_calls == []
    assert [variant.name for variant in schematic.variants] == ["default"]


async def test_schematic_variant_commands_report_errors() -> None:
    client, _ = _client()

    duplicate = await client.add_schematic_variant(name="default")
    assert duplicate["ok"] is False
    assert "already exists" in str(duplicate["message"])

    unknown = await client.rename_schematic_variant(old_name="missing", new_name="x")
    assert unknown["ok"] is False
    assert "No schematic variant named 'missing' exists" in str(unknown["message"])

    blank = await client.add_schematic_variant(name="   ")
    assert blank["ok"] is False
    assert "non-empty name" in str(blank["message"])

    unknown_current = await client.set_current_schematic_variant(name="ghost")
    assert unknown_current["ok"] is False
    assert "No schematic variant named 'ghost' exists" in str(unknown_current["message"])


async def test_schematic_variant_commands_require_capability() -> None:
    schematic = FakeSchematicWriter()
    schematic.get_variants = None  # type: ignore[method-assign]
    client, _ = _client(schematic)

    result = await client.get_schematic_variants()

    assert result["ok"] is False
    assert "design variant commands" in str(result["message"])
