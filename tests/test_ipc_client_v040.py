"""Tests for the v0.4.0 additions: library browsing, symbol placement, PNG export."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("kipy")

from kipy.errors import ApiError  # noqa: E402
from kipilot_mcp.config import KiCadIpcConfig  # noqa: E402
from kipilot_mcp.ipc_client import KiCadIpcClient  # noqa: E402


class FakeVector:
    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y


class FakeLibraryIdentifier:
    def __init__(self, library: str, name: str) -> None:
        self.library = library
        self.name = name

    def __str__(self) -> str:
        return f"{self.library}:{self.name}"


class FakeLibraryStatus:
    def __init__(
        self,
        nickname: str,
        *,
        library_type: int = 1,
        scope: int = 1,
        status: int = 3,
        error_message: str | None = None,
    ) -> None:
        self.nickname = nickname
        self.type = library_type
        self.scope = scope
        self.status = status
        self.error_message = error_message


class FakeSymbolField:
    def __init__(self, name: str, value: str, *, visible: bool = True) -> None:
        self.name = name
        self.text = SimpleNamespace(value=value)
        self.visible = visible
        self.show_name = False
        self.is_private = False


class FakeSymbolPin:
    def __init__(self, name: str, number: str) -> None:
        self.name = name
        self.number = number
        self.position = FakeVector(1000000, 2000000)
        self.length = 2500000
        self.orientation = 1
        self.electrical_type = 2
        self.shape = 1
        self.visible = True
        self.alternates = [SimpleNamespace(name="ALT", shape=2, electrical_type=3)]


class FakeSymbolAttributes:
    do_not_populate = False
    exclude_from_bill_of_materials = False
    exclude_from_board = False
    exclude_from_position_files = False
    exclude_from_simulation = True


class FakeLibrarySymbol:
    def __init__(self) -> None:
        self.id = FakeLibraryIdentifier("Device", "R")
        self.type = 1
        self.unit_count = 2
        self.body_style_count = 1
        self.keywords = "resistor"
        self.footprint_filters = ["R_*"]
        self.reference_field = FakeSymbolField("Reference", "R")
        self.value_field = FakeSymbolField("Value", "R")
        self.footprint_field = FakeSymbolField("Footprint", "")
        self.datasheet_field = FakeSymbolField("Datasheet", "")
        self.description_field = FakeSymbolField("Description", "Resistor")
        self.attributes = FakeSymbolAttributes()
        self.pins = [FakeSymbolPin("~", "1"), FakeSymbolPin("~", "2")]
        self.fields = [FakeSymbolField("MPN", "RC0603")]


class FakePad:
    def __init__(self, number: str, x: int, y: int) -> None:
        self.id = f"pad-{number}"
        self.number = number
        self.position = FakeVector(x, y)
        self.net = None
        self.pad_type = 1
        self.padstack = SimpleNamespace(layers=[1])


class FakeFootprintField:
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.text = SimpleNamespace(value=value)

    @property
    def value(self) -> str:
        return self.text.value


class FakeLibraryFootprint:
    def __init__(self) -> None:
        self.id = FakeLibraryIdentifier("Resistor_SMD", "R_0603_1608Metric")
        self.anchor = FakeVector(0, 0)
        self.pads = [FakePad("1", -900000, 0), FakePad("2", 900000, 0)]
        self.texts = [FakeFootprintField("Reference", "REF**")]
        self.shapes = []
        self.models = []
        self.private_layers = []
        self.proto = SimpleNamespace(
            reference_field=SimpleNamespace(text=SimpleNamespace(value="REF**")),
            value_field=SimpleNamespace(text=SimpleNamespace(value="R_0603")),
            datasheet_field=SimpleNamespace(text=SimpleNamespace(value="")),
            description_field=SimpleNamespace(text=SimpleNamespace(value="0603 resistor")),
        )


class FakeSchematicItem:
    def __init__(self, item_id: str, reference: str, value: str) -> None:
        self.id = item_id
        self.type = 1
        self.reference = reference
        self.value = value
        self.position = FakeVector(25400000, 12700000)


class FakeSheetPath:
    def __init__(self, identifiers: list[str], human_readable: str) -> None:
        self.path = [SimpleNamespace(value=identifier) for identifier in identifiers]
        self.path_human_readable = human_readable


class FakeSheet:
    def __init__(self, name: str, path: FakeSheetPath) -> None:
        self.name = name
        self.path = path
        self.children: list[FakeSheet] = []


class FakeSchematic:
    def __init__(self) -> None:
        self.name = "demo.kicad_sch"
        self.document = SimpleNamespace(type=2, board_filename="", path="demo.kicad_sch")
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.place_calls: list[tuple[Any, ...]] = []
        self.commit_messages: list[str] = []
        self.symbols: list[Any] = []
        self.sheets = [
            FakeSheet("root", FakeSheetPath(["root-id"], "/")),
            FakeSheet("power", FakeSheetPath(["root-id", "power-id"], "/power")),
        ]

    # -- placement -------------------------------------------------------
    def place_symbol_from_library(
        self,
        lib_id: Any,
        position: Any,
        orientation: Any = None,
        unit: Any = None,
        reference: Any = None,
        sheet_path: Any = None,
    ) -> FakeSchematicItem:
        self.place_calls.append((lib_id, position, orientation, unit, reference, sheet_path))
        return FakeSchematicItem("placed-symbol", reference or "R?", "R")

    # -- commits ---------------------------------------------------------
    def begin_commit(self) -> str:
        return "commit"

    def push_commit(self, commit: str, message: str = "") -> None:
        self.calls.append(("push_commit", {"commit": commit, "message": message}))
        self.commit_messages.append(message)

    def drop_commit(self, commit: str) -> None:  # pragma: no cover - defensive path
        self.calls.append(("drop_commit", {"commit": commit}))

    # -- reads -----------------------------------------------------------
    def get_symbols(self) -> list[Any]:
        return list(self.symbols)

    def get_hierarchy(self) -> list[FakeSheet]:
        return list(self.sheets)

    # -- exports ---------------------------------------------------------
    def export_png(
        self,
        output_path: str,
        plot_settings: Any = None,
        dpi: int | None = None,
        antialiasing: Any = None,
        sheet_mode: Any = None,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                "export_png",
                {
                    "output_path": output_path,
                    "plot_settings": plot_settings,
                    "dpi": dpi,
                    "antialiasing": antialiasing,
                    "sheet_mode": sheet_mode,
                },
            )
        )
        return SimpleNamespace(
            succeeded=True,
            status=1,
            output_paths=[output_path],
            message="PNG export completed.",
        )

    def export_bom(
        self,
        output_path: str,
        field_settings: Any = None,
        format_settings: Any = None,
        **options: Any,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                "export_bom",
                {
                    "output_path": output_path,
                    "field_settings": field_settings,
                    "format_settings": format_settings,
                    **options,
                },
            )
        )
        return SimpleNamespace(
            succeeded=True,
            status=1,
            output_paths=[output_path],
            message="BOM export completed.",
        )


class FakeKiCad:
    def __init__(self, *, schematic: FakeSchematic | None = None, library: bool = True) -> None:
        self.schematic = schematic or FakeSchematic()
        self.library = library
        self.library_calls: list[tuple[str, Any]] = []

    def get_schematic(self) -> FakeSchematic:
        return self.schematic

    def get_board(self) -> Any:
        raise RuntimeError("no board in this test")

    def close(self) -> None:
        pass

    # -- library API -----------------------------------------------------
    def get_library_items(self, library_type: int, nicknames: Any) -> list[FakeLibraryIdentifier]:
        if not self.library:
            raise AssertionError("library API should not be called")
        self.library_calls.append(("get_library_items", (library_type, list(nicknames))))
        if library_type == 1:
            return [
                FakeLibraryIdentifier("Device", "R"),
                FakeLibraryIdentifier("Device", "C"),
            ]
        return [FakeLibraryIdentifier("Resistor_SMD", "R_0603_1608Metric")]

    def get_library_symbol(self, lib_id: str, document: Any = None) -> FakeLibrarySymbol:
        self.library_calls.append(("get_library_symbol", (lib_id, document)))
        return FakeLibrarySymbol()

    def get_library_footprint(self, lib_id: str, document: Any = None) -> FakeLibraryFootprint:
        self.library_calls.append(("get_library_footprint", (lib_id, document)))
        return FakeLibraryFootprint()

    def get_library_statuses(self, types: Any = None, scope: Any = None) -> list[FakeLibraryStatus]:
        self.library_calls.append(("get_library_statuses", (types, scope)))
        return [
            FakeLibraryStatus("Device", library_type=1, scope=1, status=3),
            FakeLibraryStatus("Broken", library_type=2, scope=2, status=4, error_message="nope"),
        ]

    def reload_library(self, library_type: int, scope: int, nicknames: Any) -> None:
        self.library_calls.append(("reload_library", (library_type, scope, list(nicknames))))

    def wait_for_libraries(
        self,
        *,
        types: Any,
        interval_ms: int,
        timeout_s: float,
        scope: Any,
    ) -> list[FakeLibraryStatus]:
        self.library_calls.append(
            ("wait_for_libraries", (types, interval_ms, timeout_s, scope))
        )
        return [FakeLibraryStatus("Device", library_type=1, scope=1, status=3)]


class TimeoutKiCad(FakeKiCad):
    def wait_for_libraries(self, **kwargs: Any) -> list[FakeLibraryStatus]:
        raise TimeoutError("still loading")


def _client(kicad: FakeKiCad, *, enable_mutations: bool = False) -> KiCadIpcClient:
    return KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=enable_mutations),
        kicad_factory=lambda **_: kicad,
    )


async def test_list_library_symbols_and_footprints() -> None:
    kicad = FakeKiCad()

    symbols = await _client(kicad).list_library_symbols(["Device"])
    footprints = await _client(kicad).list_library_footprints()

    assert symbols["ok"] is True
    assert symbols["library_type"] == "symbol"
    assert symbols["count"] == 2
    assert symbols["items"][0] == {
        "id": "Device:R",
        "library": "Device",
        "name": "R",
    }
    assert footprints["library_type"] == "footprint"
    assert footprints["items"][0]["id"] == "Resistor_SMD:R_0603_1608Metric"
    assert kicad.library_calls[0] == ("get_library_items", (1, ["Device"]))
    assert kicad.library_calls[1] == ("get_library_items", (2, []))


async def test_list_library_symbols_reports_loading_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    kicad = FakeKiCad()
    monkeypatch.setattr(kicad, "get_library_items", lambda *_: [])

    result = await _client(kicad).list_library_symbols()

    assert result["count"] == 0
    assert "kicad_lib_wait" in result["hint"]


async def test_footprint_library_tools_explain_footprint_editor_requirement() -> None:
    kicad = FakeKiCad()

    def no_handler(*_args: Any, **_kwargs: Any) -> Any:
        raise ApiError("KiCad returned error: no handler available for request of type X")

    kicad.get_library_items = no_handler
    kicad.get_library_footprint = no_handler

    list_result = await _client(kicad).list_library_footprints()
    get_result = await _client(kicad).get_library_footprint(
        "Resistor_SMD:R_0603_1608Metric"
    )

    for result in (list_result, get_result):
        assert result["ok"] is False
        assert "project manager" in result["message"]
        assert "Footprint Editor" in result["message"]


async def test_symbol_library_tools_explain_schematic_editor_requirement() -> None:
    kicad = FakeKiCad()

    def no_handler(*_args: Any, **_kwargs: Any) -> Any:
        raise ApiError("KiCad returned error: no handler available for request of type X")

    kicad.get_library_items = no_handler
    kicad.get_library_symbol = no_handler

    list_result = await _client(kicad).list_library_symbols()
    get_result = await _client(kicad).get_library_symbol("Device:R")

    for result in (list_result, get_result):
        assert result["ok"] is False
        assert "Schematic Editor" in result["message"]


async def test_get_library_symbol_serializes_pins_and_fields() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).get_library_symbol("Device:R")

    assert result["ok"] is True
    assert result["lib_id"] == "Device:R"
    assert result["symbol"]["id"]["id"] == "Device:R"
    assert result["symbol"]["unit_count"] == 2
    assert result["symbol"]["pin_count"] == 2
    assert result["symbol"]["pins"][0]["number"] == "1"
    assert result["symbol"]["pins"][0]["length_mm"] == 2.5
    assert result["symbol"]["pins"][0]["alternates"][0]["name"] == "ALT"
    assert result["symbol"]["fields"][0] == {
        "name": "MPN",
        "value": "RC0603",
        "visible": True,
        "show_name": False,
        "is_private": False,
    }
    assert result["symbol"]["attributes"]["exclude_from_simulation"] is True
    assert kicad.library_calls[0][1][0] == "Device:R"


async def test_get_library_footprint_serializes_pads_and_fields() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).get_library_footprint("Resistor_SMD:R_0603_1608Metric")

    assert result["ok"] is True
    assert result["footprint"]["pad_count"] == 2
    assert result["footprint"]["pads"][0]["number"] == "1"
    assert result["footprint"]["fields"]["value"] == "R_0603"
    assert result["footprint"]["fields"]["description"] == "0603 resistor"
    assert result["footprint"]["texts"][0]["kind"] == "FakeFootprintField"


async def test_get_library_item_rejects_bad_lib_id() -> None:
    result = await _client(FakeKiCad()).get_library_symbol("DeviceR")

    assert result["ok"] is False
    assert "<library>:<name>" in str(result["message"])


async def test_library_tools_report_capability_error_on_old_binding() -> None:
    class OldKiCad(FakeKiCad):
        get_library_items = None
        get_library_symbol = None
        get_library_footprint = None
        get_library_statuses = None
        reload_library = None
        wait_for_libraries = None

    client = _client(OldKiCad())

    results = [
        await client.list_library_symbols(),
        await client.get_library_symbol("Device:R"),
        await client.get_library_footprint("Resistor_SMD:R_0603_1608Metric"),
        await client.get_library_statuses(),
        await client.reload_library("symbol"),
        await client.wait_for_libraries(),
    ]

    for result in results:
        assert result["ok"] is False
        assert "KiCad 11" in str(result["message"])


async def test_get_library_statuses_maps_enum_names() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).get_library_statuses("footprint", "project")

    assert result["ok"] is True
    assert result["library_type"] == "footprint"
    assert result["scope"] == "project"
    assert result["count"] == 2
    assert result["status_counts"] == {"loaded": 1, "error": 1}
    assert result["libraries"][0]["scope"] == "global"
    assert result["libraries"][1]["error_message"] == "nope"
    assert kicad.library_calls[0] == ("get_library_statuses", (2, 2))


async def test_reload_library_dry_run_and_write() -> None:
    kicad = FakeKiCad()

    dry_run = await _client(kicad).reload_library("symbol", "global", dry_run=True)

    assert dry_run["ok"] is True
    assert dry_run["dry_run"] is True
    assert dry_run["reloaded"] is False
    assert dry_run["previous_libraries"][0]["nickname"] == "Device"
    assert not any(call[0] == "reload_library" for call in kicad.library_calls)

    written = await _client(kicad).reload_library(
        "symbol",
        "project",
        ["Device"],
    )

    assert written["ok"] is True
    assert written["reloaded"] is True
    assert kicad.library_calls[-1] == ("reload_library", (1, 2, ["Device"]))


async def test_reload_library_rejects_both_scope() -> None:
    result = await _client(FakeKiCad()).reload_library("symbol", "both")

    assert result["ok"] is False
    assert "scope" in str(result["message"])


async def test_wait_for_libraries_reports_statuses_and_timeout() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).wait_for_libraries("symbol", interval_ms=10, timeout_s=2)

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["status_counts"] == {"loaded": 1}
    assert kicad.library_calls[-1] == (
        "wait_for_libraries",
        (1, 10, 2.0, 3),
    )

    timeout = await _client(TimeoutKiCad()).wait_for_libraries(timeout_s=0.5)

    assert timeout["ok"] is False
    assert "Timed out" in str(timeout["message"])


async def test_place_symbol_from_library_writes_with_default_orientation() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad, enable_mutations=True).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=25.4,
        y_mm=12.7,
        orientation=90,
        unit=2,
        reference="R10",
    )

    assert result["ok"] is True
    assert result["lib_id"] == "Device:R"
    assert result["orientation"] == "90"
    assert result["orientation_value"] == 2
    assert result["unit"] == 2
    assert result["placed"]["reference"] == "R10"

    lib_id, position, orientation, unit, reference, sheet_path = (
        kicad.schematic.place_calls[0]
    )
    assert lib_id == "Device:R"
    assert (position.x, position.y) == (25400000, 12700000)
    assert orientation == 2
    assert unit == 2
    assert reference == "R10"
    assert sheet_path is None
    assert kicad.schematic.commit_messages == ["KiPilot MCP: sch_place_symbol_from_library"]


async def test_place_symbol_from_library_dry_run_skips_placement() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=1,
        y_mm=2,
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["placed"] is None
    assert kicad.schematic.place_calls == []


async def test_place_symbol_from_library_resolves_sheet_path() -> None:
    kicad = FakeKiCad()

    result = await _client(kicad, enable_mutations=True).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=1,
        y_mm=2,
        sheet_path="/power",
    )

    assert result["ok"] is True
    assert kicad.schematic.place_calls[0][5] is kicad.schematic.sheets[1].path

    missing = await _client(kicad, enable_mutations=True).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=1,
        y_mm=2,
        sheet_path="/nope",
    )

    assert missing["ok"] is False
    assert "No schematic sheet matches" in str(missing["message"])


async def test_place_symbol_from_library_rejects_bad_unit() -> None:
    result = await _client(FakeKiCad(), enable_mutations=True).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=1,
        y_mm=2,
        unit=0,
    )

    assert result["ok"] is False
    assert "unit must be a positive integer" in str(result["message"])


async def test_place_symbol_from_library_reports_missing_capability() -> None:
    class OldSchematic(FakeSchematic):
        place_symbol_from_library = None

    kicad = FakeKiCad(schematic=OldSchematic())

    result = await _client(kicad, enable_mutations=True).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=1,
        y_mm=2,
    )

    assert result["ok"] is False
    assert "KiCad 11" in str(result["message"])


async def test_export_schematic_png_all_sheets(tmp_path: Any) -> None:
    kicad = FakeKiCad()
    output_dir = tmp_path / "pngs"

    result = await _client(kicad).export_schematic_png(
        str(output_dir),
        dpi=600,
        antialiasing="none",
    )

    assert result["ok"] is True
    assert result["format"] == "png"
    assert result["output_kind"] == "directory"
    assert result["output_path"] == str(output_dir)

    name, call = kicad.schematic.calls[0]
    assert name == "export_png"
    assert call["output_path"] == str(output_dir)
    assert call["dpi"] == 600
    assert call["antialiasing"] == 1
    assert call["sheet_mode"] == 1


async def test_export_schematic_png_single_sheet(tmp_path: Any) -> None:
    kicad = FakeKiCad()
    output_file = tmp_path / "sheet.png"

    result = await _client(kicad).export_schematic_png(
        str(output_file),
        sheet_mode="single_sheet",
    )

    assert result["ok"] is True
    assert result["output_kind"] == "file"
    name, call = kicad.schematic.calls[0]
    assert name == "export_png"
    assert call["sheet_mode"] == 2
    assert call["antialiasing"] == 2


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"dpi": 10}, "dpi"),
        ({"dpi": "abc"}, "dpi"),
        ({"antialiasing": "fast"}, "antialiasing"),
        ({"sheet_mode": "unknown"}, "sheet_mode"),
    ],
)
async def test_export_schematic_png_rejects_invalid_options(
    tmp_path: Any,
    kwargs: dict[str, Any],
    expected: str,
) -> None:
    result = await _client(FakeKiCad()).export_schematic_png(
        str(tmp_path / "out"),
        **kwargs,
    )

    assert result["ok"] is False
    assert expected in str(result["message"])


async def test_export_schematic_png_requires_directory_for_all_sheets(tmp_path: Any) -> None:
    result = await _client(FakeKiCad()).export_schematic_png(str(tmp_path / "sheet.png"))

    assert result["ok"] is False
    assert "output directory" in str(result["message"])


async def test_export_schematic_bom_defaults_to_csv_preset(tmp_path: Any) -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).export_schematic_bom(str(tmp_path / "demo.csv"))

    assert result["ok"] is True
    name, call = kicad.schematic.calls[0]
    assert name == "export_bom"
    assert call["format_settings"] is not None
    assert call["format_settings"].field_delimiter == ","
    assert call["format_settings"].string_delimiter == '"'
    assert call["field_settings"] is not None
    assert call["field_settings"].sort_field == "Reference"
    assert [field.name for field in call["field_settings"].fields][:2] == [
        "Reference",
        "Value",
    ]


async def test_export_schematic_bom_fills_fields_for_partial_settings(tmp_path: Any) -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).export_schematic_bom(
        str(tmp_path / "demo.csv"),
        field_settings={"filter": "R*"},
    )

    assert result["ok"] is True
    name, call = kicad.schematic.calls[0]
    assert name == "export_bom"
    assert call["field_settings"].filter == "R*"
    assert call["field_settings"].sort_field == "Reference"
    assert len(call["field_settings"].fields) >= 4


async def test_export_schematic_bom_reports_failed_job(tmp_path: Any) -> None:
    kicad = FakeKiCad()
    kicad.schematic.export_bom = lambda *args, **kwargs: SimpleNamespace(
        succeeded=False,
        status=3,
        output_paths=[],
        message="Failed to load kiface library '_cvpcb.dll'.",
    )

    result = await _client(kicad).export_schematic_bom(str(tmp_path / "demo.csv"))

    assert result["ok"] is False
    assert "KiCad bom job failed" in result["message"]
    assert "_cvpcb.dll" in result["message"]


async def test_export_schematic_netlist_reports_failed_job(tmp_path: Any) -> None:
    kicad = FakeKiCad()
    kicad.schematic.export_netlist = lambda *args, **kwargs: SimpleNamespace(
        succeeded=False,
        status=3,
        output_paths=[],
        message="Failed to load kiface library '_cvpcb.dll'.",
    )

    result = await _client(kicad).export_schematic_netlist(str(tmp_path / "demo.net"))

    assert result["ok"] is False
    assert "KiCad netlist job failed" in result["message"]
    assert "_cvpcb.dll" in result["message"]


async def test_export_schematic_bom_accepts_new_format_fields(tmp_path: Any) -> None:
    kicad = FakeKiCad()

    result = await _client(kicad).export_schematic_bom(
        str(tmp_path / "demo.csv"),
        format_settings={"include_byte_order_mark": True},
        field_settings={"filter": "R*", "filter_scope": 2},
    )

    assert result["ok"] is True
    name, call = kicad.schematic.calls[0]
    assert name == "export_bom"
    assert call["format_settings"].include_byte_order_mark is True
    assert call["field_settings"].filter_scope == 2
    assert call["field_settings"].filter == "R*"
    assert len(call["field_settings"].fields) >= 4


async def test_server_exposes_v040_tools() -> None:
    from kipilot_mcp import server

    tools = server.mcp.list_tools()
    if inspect.isawaitable(tools):
        tools = await tools

    names = {tool.name for tool in tools}
    expected = {
        "kicad_lib_list_symbols",
        "kicad_lib_get_symbol",
        "kicad_lib_list_footprints",
        "kicad_lib_get_footprint",
        "kicad_lib_statuses",
        "kicad_lib_reload",
        "kicad_lib_wait",
        "kicad_sch_place_symbol_from_library",
        "kicad_sch_export_png",
    }

    assert expected <= names
