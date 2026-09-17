"""Tests for the v0.3.0 additions: board exports, rules, embedded files, lifecycle."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("kipy")

from kipy.board_jobs import PlotSettings as KipyPlotSettings  # noqa: E402
from kipy.board_rules import (  # noqa: E402
    BoardDesignRulesResponse as KipyBoardDesignRulesResponse,
)
from kipy.board_rules import CustomRulesResponse as KipyCustomRulesResponse  # noqa: E402
from kipy.geometry import Box2 as KipyBox2  # noqa: E402
from kipy.proto.board import board_commands_pb2 as kipy_board_commands_pb2  # noqa: E402
from kipy.proto.common.types import DocumentSpecifier as KipyDocumentSpecifier  # noqa: E402
from kipy.proto.common.types import base_types_pb2 as kipy_base_types_pb2  # noqa: E402
from kipy.proto.schematic import schematic_types_pb2 as kipy_schematic_types_pb2  # noqa: E402
from kipy.schematic_types import (  # noqa: E402
    BusEntry as KipyBusEntry,
)
from kipy.schematic_types import (  # noqa: E402
    SchematicImage as KipySchematicImage,
)
from kipy.schematic_types import (  # noqa: E402
    SchematicRuleArea as KipySchematicRuleArea,
)
from kipy.schematic_types import (  # noqa: E402
    SchematicTable as KipySchematicTable,
)
from kipy.schematic_types import (  # noqa: E402
    SheetSymbol as KipySheetSymbol,
)

from kipilot_mcp.config import KiCadIpcConfig  # noqa: E402
from kipilot_mcp.ipc_client import KiCadIpcClient  # noqa: E402


class FakeJobResult:
    def __init__(self, output_paths: tuple[str, ...]) -> None:
        self.succeeded = True
        self.status = 4
        self.output_paths = list(output_paths)
        self.message = "done"


class FakeEmbeddedFile:
    def __init__(self, name: str, file_type: int = 2, data: bytes = b"abc") -> None:
        self.name = name
        self.type = file_type
        self.data = data
        self.data_hash = "hash"

    def __repr__(self) -> str:
        return f"FakeEmbeddedFile({self.name})"


class FakeEmbeddedFiles:
    def __init__(self, files: list[FakeEmbeddedFile]) -> None:
        self.files = list(files)


class FakeNetClass:
    def __init__(self, name: str, clearance: int = 100000) -> None:
        self.name = name
        self.description = ""
        self.clearance = clearance
        self.track_width = 250000
        self.via_diameter = 600000
        self.via_drill = 300000
        self.diff_pair_gap = None
        self.diff_pair_width = None
        self.diff_pair_via_gap = None
        self.net_names: list[str] = []


class FakeProject:
    def __init__(self) -> None:
        self.name = "demo"
        self.path = "C:/demo/demo.kicad_pro"
        self.document = None
        self.calls: list[tuple[str, Any, Any]] = []
        self.net_classes = [FakeNetClass("Default", clearance=150000)]

    def get_net_classes(self) -> list[FakeNetClass]:
        return list(self.net_classes)

    def set_net_classes(self, net_classes: list[Any], merge_mode: Any = None) -> None:
        self.calls.append(("set_net_classes", net_classes, merge_mode))
        self.net_classes.extend(net_classes)


class FakeNetlistResult:
    def __init__(self) -> None:
        self.report = "netlist imported"
        self.error_count = 1
        self.warning_count = 2
        self.new_footprint_count = 3


class FakeTrack:
    def __init__(self, item_id: str) -> None:
        self.id = item_id


class FakeBoard:
    def __init__(self) -> None:
        self.name = "demo"
        self.document = None
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.project = FakeProject()
        self.embedded_files = [FakeEmbeddedFile("logo.png")]
        self.design_rules_proto: Any = None

    def get_project(self) -> FakeProject:
        return self.project

    def get_tracks(self) -> list[FakeTrack]:
        return [FakeTrack("track-id")]

    def export_gerbers(self, output_path: str, **kwargs: Any) -> FakeJobResult:
        self.calls.append(("export_gerbers", {"output_path": output_path, **kwargs}))
        return FakeJobResult((f"{output_path}/demo-F_Cu.gbr",))

    def export_position(self, output_path: str, **kwargs: Any) -> FakeJobResult:
        self.calls.append(("export_position", {"output_path": output_path, **kwargs}))
        return FakeJobResult((output_path,))

    def export_drill(self, output_path: str, **kwargs: Any) -> FakeJobResult:
        self.calls.append(("export_drill", {"output_path": output_path, **kwargs}))
        return FakeJobResult((f"{output_path}/demo.drl",))

    def get_design_rules(self) -> Any:
        if self.design_rules_proto is None:
            proto = kipy_board_commands_pb2.BoardDesignRulesResponse()
            proto.rules.severities.add().rule_type = 5
            proto.rules.severities[0].severity = 2
            proto.rules.constraints.min_clearance.value_nm = 100000
            self.design_rules_proto = proto

        return KipyBoardDesignRulesResponse(self.design_rules_proto)

    def set_design_rules(self, rules: Any) -> Any:
        self.calls.append(("set_design_rules", {"rules": rules}))
        stored = kipy_board_commands_pb2.BoardDesignRulesResponse()
        stored.rules.CopyFrom(rules.proto)
        self.design_rules_proto = stored
        return KipyBoardDesignRulesResponse(self.design_rules_proto)

    def set_custom_design_rules(self, rules: list[Any]) -> Any:
        self.calls.append(("set_custom_design_rules", {"rules": rules}))
        proto = kipy_board_commands_pb2.CustomRulesResponse()
        proto.status = 2
        return KipyCustomRulesResponse(proto)

    def get_embedded_files(self) -> FakeEmbeddedFiles:
        return FakeEmbeddedFiles(self.embedded_files)

    def add_embedded_files(self, files: list[Any]) -> None:
        self.calls.append(("add_embedded_files", {"files": list(files)}))
        self.embedded_files.extend(files)

    def set_embedded_files(self, files: list[Any]) -> None:
        self.calls.append(("set_embedded_files", {"files": list(files)}))
        self.embedded_files = list(files)

    def import_netlist(self, netlist_path: str, **kwargs: Any) -> FakeNetlistResult:
        self.calls.append(("import_netlist", {"netlist_path": netlist_path, **kwargs}))
        return FakeNetlistResult()

    def get_item_bounding_box(self, items: list[Any], include_text: bool = False) -> list[Any]:
        self.calls.append(("get_item_bounding_box", {"items": list(items), "include_text": include_text}))
        boxes = []
        for item in items:
            proto = kipy_base_types_pb2.Box2()
            proto.position.x_nm = 1000
            proto.position.y_nm = 2000
            proto.size.x_nm = 500
            proto.size.y_nm = 600
            boxes.append(KipyBox2.from_proto(proto))
        return boxes


class FakeSchematic:
    shared_items: list[Any] = []

    def __init__(self) -> None:
        self.name = "demo-sch"
        self.document = None
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.modified = True

    def save_as(self, filename: str, overwrite: bool = False, include_project: bool = True) -> None:
        self.calls.append(
            (
                "save_as",
                {
                    "filename": filename,
                    "overwrite": overwrite,
                    "include_project": include_project,
                },
            )
        )

    def revert(self) -> None:
        self.calls.append(("revert", {}))
        self.modified = False

    def is_document_modified(self) -> bool:
        return self.modified

    def get_items(self) -> list[Any]:
        return list(FakeSchematic.shared_items)


class FakeKiCad:
    last_instance: FakeKiCad | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.board = FakeBoard()
        self.schematic = FakeSchematic()
        FakeKiCad.last_instance = self

    def get_board(self) -> FakeBoard:
        return self.board

    def get_schematic(self) -> FakeSchematic:
        return self.schematic

    def get_paths(self) -> dict[int, str]:
        return {3: "C:/kicad/library", 4: "C:/kicad/template"}

    def get_kicad_binary_path(self, binary_name: str) -> str:
        return f"C:/kicad/bin/{binary_name}.exe"

    def get_plugin_settings_path(self, identifier: str) -> str:
        return f"C:/kicad/settings/{identifier}"

    def run_action(self, action: str) -> Any:
        self.last_action = action
        return SimpleNamespace(status=1)

    def open_document(self, path: str, document_type: int) -> KipyDocumentSpecifier:
        specifier = KipyDocumentSpecifier()
        specifier.type = document_type
        specifier.board_filename = Path(path).name
        return specifier

    def close_document(self, document: KipyDocumentSpecifier) -> None:
        self.closed_document = document

    def close(self) -> None:
        pass


def _client(*, enable_mutations: bool = False) -> KiCadIpcClient:
    return KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=enable_mutations),
        kicad_factory=FakeKiCad,
    )


def _last_board() -> FakeBoard:
    assert FakeKiCad.last_instance is not None
    return FakeKiCad.last_instance.board


def _make_schematic_item(item_class: type, proto: Any) -> Any:
    item = item_class()
    item.__dict__["_proto"] = proto
    return item


async def test_get_paths_returns_platform_paths() -> None:
    result = await _client().get_paths()

    assert result["ok"] is True
    assert result["count"] == 2
    assert sorted(result["paths"].values()) == ["C:/kicad/library", "C:/kicad/template"]


async def test_get_kicad_binary_path_rejects_empty_name() -> None:
    result = await _client().get_kicad_binary_path("   ")

    assert result["ok"] is False
    assert "binary_name" in str(result["message"])


async def test_run_action_requires_mutations_and_reports_status() -> None:
    disabled = await _client().run_action("pcbnew.EditorControl.zoneFillAll")
    dry_run = await _client().run_action("pcbnew.EditorControl.zoneFillAll", dry_run=True)
    executed = await _client(enable_mutations=True).run_action("pcbnew.EditorControl.zoneFillAll")

    assert disabled["ok"] is False
    assert "mutations are disabled" in str(disabled["message"])
    assert dry_run["ok"] is True
    assert dry_run["executed"] is False

    assert executed["ok"] is True
    assert executed["executed"] is True
    assert executed["status"] == 1
    assert FakeKiCad.last_instance is not None
    assert FakeKiCad.last_instance.last_action == "pcbnew.EditorControl.zoneFillAll"


async def test_open_and_close_document_use_headless_document_specifiers(tmp_path: Path) -> None:
    board_path = tmp_path / "demo.kicad_pcb"
    board_path.write_text("(kicad_pcb)\n", encoding="utf-8")

    opened = await _client(enable_mutations=True).open_document(
        str(board_path),
        "pcb",
    )
    closed = await _client(enable_mutations=True).close_document(str(board_path), "pcb")

    assert opened["ok"] is True
    assert opened["document_type_name"] == "pcb"
    assert opened["document"]["board_filename"] == "demo.kicad_pcb"

    assert closed["ok"] is True
    assert closed["specifier"]["board_filename"] == "demo.kicad_pcb"
    assert FakeKiCad.last_instance is not None
    assert FakeKiCad.last_instance.closed_document.board_filename == "demo.kicad_pcb"


async def test_open_document_rejects_unknown_document_type() -> None:
    result = await _client(enable_mutations=True).open_document("demo.kicad_pcb", "gerber-layer")

    assert result["ok"] is False
    assert "document_type" in str(result["message"])


async def test_set_project_net_classes_dry_run_and_write() -> None:
    dry_run = await _client().set_project_net_classes(
        [{"name": "Power", "board": {"clearance": {"value_nm": 200000}}}],
        dry_run=True,
    )

    assert dry_run["ok"] is True
    assert dry_run["dry_run"] is True
    assert dry_run["merge_mode"] == "merge"
    assert dry_run["requested_count"] == 1
    assert dry_run["requested_net_classes"][0]["name"] == "Power"
    assert dry_run["requested_net_classes"][0]["clearance_nm"] == 200000
    assert _last_board().project.calls == []

    applied = await _client(enable_mutations=True).set_project_net_classes(
        [{"name": "Power", "board": {"clearance": {"value_nm": 200000}}}],
        merge_mode="replace",
    )

    assert applied["ok"] is True
    assert applied["merge_mode"] == "replace"
    assert applied["previous_count"] == 1
    assert applied["count"] == 2
    assert _last_board().project.calls[0][0] == "set_net_classes"
    assert _last_board().project.calls[0][2] == 2


async def test_set_project_net_classes_requires_a_name() -> None:
    result = await _client(enable_mutations=True).set_project_net_classes([{"clearance": 100000}])

    assert result["ok"] is False
    assert "name" in str(result["message"])


async def test_export_gerbers_parses_plot_settings(tmp_path: Path) -> None:
    output_dir = tmp_path / "gerbers"

    result = await _client().export_gerbers(
        str(output_dir),
        create_gerber_job_file=True,
        precision="GP_6",
        plot_settings={"color_theme": "KiCad Default", "scale": 0.5},
    )

    assert result["ok"] is True
    assert result["format"] == "gerbers"
    assert result["output_kind"] == "directory"
    assert result["output_dir"] == str(output_dir)
    assert result["job"]["succeeded"] is True
    assert result["job"]["output_paths"] == [f"{output_dir}/demo-F_Cu.gbr"]
    assert result["requested_plot_settings"]["color_theme"] == "KiCad Default"

    name, call = _last_board().calls[0]
    assert name == "export_gerbers"
    assert call["create_gerber_job_file"] is True
    assert call["precision"] == 2
    plot_settings = call["plot_settings"]
    assert isinstance(plot_settings, KipyPlotSettings)
    assert plot_settings.color_theme == "KiCad Default"
    assert plot_settings.scale == 0.5


async def test_export_position_rejects_unknown_settings_field(tmp_path: Path) -> None:
    result = await _client().export_position(
        str(tmp_path / "demo.pos"),
        settings={"not_a_real_field": 1},
    )

    assert result["ok"] is False
    assert "Unknown position settings field" in str(result["message"])


async def test_export_drill_accepts_short_enum_aliases(tmp_path: Path) -> None:
    result = await _client().export_drill(
        str(tmp_path / "drill"),
        format="excellon",
        map_format="pdf",
    )

    assert result["ok"] is True
    assert result["job"]["output_paths"] == [f"{tmp_path / 'drill'}/demo.drl"]

    name, call = _last_board().calls[0]
    assert name == "export_drill"
    assert call["format"] == 1
    assert call["map_format"] == 5


async def test_export_reports_missing_capability(tmp_path: Path) -> None:
    result = await _client().export_3d(str(tmp_path / "demo.step"))

    assert result["ok"] is False
    assert "does not expose export_3d()" in str(result["message"])


async def test_export_rejects_directory_as_file_target(tmp_path: Path) -> None:
    result = await _client().export_position(str(tmp_path))

    assert result["ok"] is False
    assert "output file" in str(result["message"])


async def test_get_and_set_design_rules_merge_and_replace_repeated_fields() -> None:
    rules = await _client().get_design_rules()

    assert rules["ok"] is True
    assert rules["rules"]["constraints"]["min_clearance"]["value_nm"] == 100000
    assert rules["rules"]["severities"] == [{"rule_type": 5, "severity": 2}]

    updated = await _client(enable_mutations=True).set_design_rules(
        {"severities": [{"rule_type": 5, "severity": 4}]}
    )

    assert updated["ok"] is True
    assert updated["mutation"] == "set_design_rules"
    assert updated["requested_fields"] == ["severities"]
    assert updated["rules"]["severities"] == [{"rule_type": 5, "severity": 4}]
    assert updated["rules"]["constraints"]["min_clearance"]["value_nm"] == 100000

    name, call = _last_board().calls[0]
    assert name == "set_design_rules"
    assert call["rules"].severities[5] == 4


async def test_set_design_rules_rejects_unknown_field() -> None:
    result = await _client(enable_mutations=True).set_design_rules({"nope": 1})

    assert result["ok"] is False
    assert "Unknown rules field" in str(result["message"])


async def test_set_custom_design_rules_builds_rule_protos() -> None:
    result = await _client(enable_mutations=True).set_custom_design_rules(
        [{"name": "Custom clearance", "condition": "A.NetClass == 'Power'", "severity": 2}]
    )

    assert result["ok"] is True
    assert result["requested_count"] == 1
    assert result["requested_rules"][0]["name"] == "Custom clearance"
    assert result["status_value"] == 2

    name, call = _last_board().calls[0]
    assert name == "set_custom_design_rules"
    assert len(call["rules"]) == 1
    assert call["rules"][0].name == "Custom clearance"


async def test_add_embedded_files_reads_local_files(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    source.write_bytes(b"fake-png-data")

    result = await _client(enable_mutations=True).add_embedded_files([str(source)])

    assert result["ok"] is True
    assert result["replace"] is False
    assert result["requested_files"][0]["name"] == "logo.png"
    assert result["requested_files"][0]["type"] == "other"
    assert result["previous_count"] == 1

    name, call = _last_board().calls[0]
    assert name == "add_embedded_files"
    assert len(call["files"]) == 1


async def test_set_embedded_files_requires_force(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    source.write_bytes(b"fake-png-data")

    blocked = await _client(enable_mutations=True).set_embedded_files([str(source)])
    forced = await _client(enable_mutations=True).set_embedded_files([str(source)], force=True)

    assert blocked["ok"] is False
    assert "destructive" in str(blocked["message"])
    assert forced["ok"] is True
    assert forced["replace"] is True


async def test_import_netlist_validates_and_reports(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("(export (version D))\n", encoding="utf-8")

    missing = await _client(enable_mutations=True).import_netlist(str(tmp_path / "missing.net"))
    assert missing["ok"] is False
    assert "readable file" in str(missing["message"])

    result = await _client(enable_mutations=True).import_netlist(
        str(netlist),
        match_mode="reference",
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["netlist_path"] == str(netlist)
    assert result["match_mode"] == "reference"
    assert result["report"] == "netlist imported"
    assert result["error_count"] == 1
    assert result["warning_count"] == 2
    assert result["new_footprint_count"] == 3

    name, call = _last_board().calls[0]
    assert name == "import_netlist"
    assert call["dry_run"] is True
    assert call["match_mode"] == 2


async def test_get_bounding_box_serializes_boxes() -> None:
    result = await _client().get_bounding_box(["track-id"], include_text=True)

    assert result["ok"] is True
    assert result["item_ids"] == ["track-id"]
    assert result["include_text"] is True
    assert result["count"] == 1
    assert result["boxes"][0]["position"] == {"x_nm": 1000, "y_nm": 2000, "x_mm": 0.001, "y_mm": 0.002}


async def test_schematic_save_as_guards_existing_files(tmp_path: Path) -> None:
    target = tmp_path / "copy.kicad_sch"
    target.write_text("(kicad_sch)\n", encoding="utf-8")

    blocked = await _client(enable_mutations=True).save_schematic_as(str(target))
    dry_run = await _client().save_schematic_as(str(target), dry_run=True)
    saved = await _client(enable_mutations=True).save_schematic_as(str(target), overwrite=True)

    assert blocked["ok"] is False
    assert "overwrite=True" in str(blocked["message"])
    assert dry_run["ok"] is True
    assert dry_run["dry_run"] is True
    assert saved["ok"] is True
    assert saved["filename"] == str(target)
    assert FakeKiCad.last_instance is not None
    assert FakeKiCad.last_instance.schematic.calls[0][0] == "save_as"


async def test_schematic_revert_requires_force() -> None:
    blocked = await _client(enable_mutations=True).revert_schematic()
    forced = await _client(enable_mutations=True).revert_schematic(force=True)

    assert blocked["ok"] is False
    assert "destructive" in str(blocked["message"])
    assert forced["ok"] is True
    assert forced["was_modified"] is True
    assert FakeKiCad.last_instance is not None
    assert FakeKiCad.last_instance.schematic.calls == [("revert", {})]


async def test_schematic_get_items_supports_read_only_kinds() -> None:
    client = _client()
    FakeSchematic.shared_items = [
        _make_schematic_item(KipySheetSymbol, kipy_schematic_types_pb2.SheetSymbol()),
        _make_schematic_item(KipySchematicImage, kipy_schematic_types_pb2.SchematicImage()),
        _make_schematic_item(KipyBusEntry, kipy_schematic_types_pb2.BusEntry()),
        _make_schematic_item(KipySchematicTable, kipy_schematic_types_pb2.SchematicTable()),
        _make_schematic_item(KipySchematicRuleArea, kipy_schematic_types_pb2.SchematicRuleArea()),
    ]

    try:
        result = await client.get_schematic_items(kinds=["sheet", "image", "bus_entry"])

        assert result["count"] == 3
        assert result["kinds"] == ["bus_entry", "image", "sheet"]

        unsupported = await client.get_schematic_items(kinds=["sprocket"])
        assert unsupported["ok"] is False
        assert "Unsupported schematic item kind" in str(unsupported["message"])
    finally:
        FakeSchematic.shared_items = []


async def test_server_exposes_v030_tools() -> None:
    from kipilot_mcp import server

    tools = server.mcp.list_tools()
    if inspect.isawaitable(tools):
        tools = await tools

    names = {tool.name for tool in tools}
    expected = {
        "kicad_get_paths",
        "kicad_get_kicad_binary_path",
        "kicad_get_plugin_settings_path",
        "kicad_run_action",
        "kicad_open_document",
        "kicad_create_document",
        "kicad_close_document",
        "kicad_set_project_net_classes",
        "kicad_export_board_svg",
        "kicad_export_board_dxf",
        "kicad_export_board_pdf",
        "kicad_export_board_ps",
        "kicad_export_gerbers",
        "kicad_export_drill",
        "kicad_export_position",
        "kicad_export_gencad",
        "kicad_export_ipc2581",
        "kicad_export_ipc_d356",
        "kicad_export_odb",
        "kicad_export_stats",
        "kicad_export_3d",
        "kicad_export_render",
        "kicad_get_design_rules",
        "kicad_set_design_rules",
        "kicad_get_custom_design_rules",
        "kicad_set_custom_design_rules",
        "kicad_get_embedded_files",
        "kicad_add_embedded_files",
        "kicad_set_embedded_files",
        "kicad_import_netlist",
        "kicad_get_bounding_box",
        "kicad_sch_save_as",
        "kicad_sch_revert",
    }

    assert expected <= names
