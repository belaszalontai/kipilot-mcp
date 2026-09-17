"""Verification script for the KiPilot MCP v0.3.0 tool surface.

The script exercises the new v0.3.0 client capabilities twice:

1. Against an in-process fake KiCad endpoint so the full request/response path
   (validation, proto handling, serialization, mutation gating) can be checked
   without a running KiCad instance.
2. Against a live KiCad IPC endpoint, when one is reachable.  The live phase is
   read-only unless ``KIPILOT_ENABLE_MUTATIONS=1`` is set, and it degrades to a
   skipped step when no endpoint answers.

Run it from the repository root::

    ./.venv/Scripts/python.exe scripts/verify_v0_3_0.py
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile
from types import SimpleNamespace
from typing import Any

from kipy.board_jobs import PlotSettings as KipyPlotSettings
from kipy.board_rules import BoardDesignRulesResponse as KipyBoardDesignRulesResponse
from kipy.board_rules import CustomRulesResponse as KipyCustomRulesResponse
from kipy.geometry import Box2 as KipyBox2
from kipy.proto.board import board_commands_pb2 as kipy_board_commands_pb2
from kipy.proto.common.types import DocumentSpecifier as KipyDocumentSpecifier
from kipy.proto.common.types import base_types_pb2 as kipy_base_types_pb2

from kipilot_mcp import __version__
from kipilot_mcp.config import KiCadIpcConfig
from kipilot_mcp.ipc_client import KiCadIpcClient

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

RESULTS: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    print(f"[{status}] {name}{f' -> {detail}' if detail else ''}")


class FakeJobResult:
    def __init__(self, output_paths: tuple[str, ...]) -> None:
        self.succeeded = True
        self.status = 4
        self.output_paths = list(output_paths)
        self.message = "job completed"


class FakeEmbeddedFile:
    def __init__(self, name: str, file_type: int = 2, data: bytes = b"embedded") -> None:
        self.name = name
        self.type = file_type
        self.data = data
        self.data_hash = "hash"


class FakeEmbeddedFiles:
    def __init__(self, files: list[FakeEmbeddedFile]) -> None:
        self.files = list(files)


class FakeNetClass:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = ""
        self.clearance = 150000
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
        self.net_classes = [FakeNetClass("Default")]

    def get_net_classes(self) -> list[FakeNetClass]:
        return list(self.net_classes)

    def set_net_classes(self, net_classes: list[Any], merge_mode: Any = None) -> None:
        self.calls.append(("set_net_classes", net_classes, merge_mode))
        self.net_classes.extend(net_classes)


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

    def export_drill(self, output_path: str, **kwargs: Any) -> FakeJobResult:
        self.calls.append(("export_drill", {"output_path": output_path, **kwargs}))
        return FakeJobResult((f"{output_path}/demo.drl",))

    def export_3d(self, output_path: str, **kwargs: Any) -> FakeJobResult:
        self.calls.append(("export_3d", {"output_path": output_path, **kwargs}))
        return FakeJobResult((output_path,))

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
        return KipyBoardDesignRulesResponse(stored)

    def set_custom_design_rules(self, rules: list[Any]) -> Any:
        self.calls.append(("set_custom_design_rules", {"rules": list(rules)}))
        proto = kipy_board_commands_pb2.CustomRulesResponse()
        proto.status = 2
        return KipyCustomRulesResponse(proto)

    def get_embedded_files(self) -> FakeEmbeddedFiles:
        return FakeEmbeddedFiles(self.embedded_files)

    def add_embedded_files(self, files: list[Any]) -> None:
        self.calls.append(("add_embedded_files", {"files": list(files)}))
        self.embedded_files.extend(files)

    def import_netlist(self, netlist_path: str, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("import_netlist", {"netlist_path": netlist_path, **kwargs}))
        return SimpleNamespace(
            report="netlist applied",
            error_count=0,
            warning_count=1,
            new_footprint_count=2,
        )

    def get_item_bounding_box(self, items: list[Any], include_text: bool = False) -> list[Any]:
        self.calls.append(("get_item_bounding_box", {"items": list(items)}))
        proto = kipy_base_types_pb2.Box2()
        proto.position.x_nm = 1000
        proto.position.y_nm = 2000
        proto.size.x_nm = 500
        proto.size.y_nm = 600
        return [KipyBox2.from_proto(proto) for _ in items]


class FakeKiCad:
    last_instance: FakeKiCad | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.board = FakeBoard()
        FakeKiCad.last_instance = self

    def get_board(self) -> FakeBoard:
        return self.board

    def get_paths(self) -> dict[int, str]:
        return {3: "C:/kicad/library"}

    def get_kicad_binary_path(self, binary_name: str) -> str:
        return f"C:/kicad/bin/{binary_name}.exe"

    def run_action(self, action: str) -> Any:
        return SimpleNamespace(status=1)

    def open_document(self, path: str, document_type: int) -> KipyDocumentSpecifier:
        specifier = KipyDocumentSpecifier()
        specifier.type = document_type
        specifier.board_filename = pathlib.Path(path).name
        return specifier

    def close(self) -> None:
        pass


async def run_fake_phase(tmp: pathlib.Path, *, enable_mutations: bool) -> None:
    client = KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=enable_mutations),
        kicad_factory=FakeKiCad,
    )

    result = await client.get_paths()
    record("get_paths", PASS if result.get("ok") else FAIL, json.dumps(result.get("paths")))

    result = await client.get_kicad_binary_path("kicad-cli")
    record(
        "get_kicad_binary_path",
        PASS if result.get("path", "").endswith("kicad-cli.exe") else FAIL,
        result.get("path", ""),
    )

    result = await client.run_action("pcbnew.EditorControl.zoneFillAll", dry_run=True)
    record("run_action(dry_run)", PASS if result.get("executed") is False else FAIL)

    board_path = tmp / "demo.kicad_pcb"
    board_path.write_text("(kicad_pcb)\n", encoding="utf-8")
    result = await client.open_document(str(board_path), "pcb", dry_run=True)
    record(
        "open_document(dry_run)",
        PASS if result.get("document_type_name") == "pcb" else FAIL,
        str(result.get("path")),
    )

    result = await client.export_gerbers(
        str(tmp / "gerbers"),
        precision="GP_6",
        plot_settings={"color_theme": "KiCad Default"},
    )
    passed = (
        result.get("ok") is True
        and result["job"]["output_paths"] == [f"{tmp / 'gerbers'}/demo-F_Cu.gbr"]
    )
    record("export_gerbers", PASS if passed else FAIL, json.dumps(result.get("format")))

    call = FakeKiCad.last_instance.board.calls[-1][1]
    plot_settings = call.get("plot_settings")
    record(
        "export_gerbers(plot_settings)",
        PASS if isinstance(plot_settings, KipyPlotSettings) else FAIL,
        str(getattr(plot_settings, "color_theme", None)),
    )

    result = await client.export_drill(str(tmp / "drill"), format="excellon")
    record(
        "export_drill",
        PASS if result.get("ok") and result.get("job", {}).get("output_paths") else FAIL,
        str(result.get("message", json.dumps(result.get("output_kind")))),
    )

    result = await client.export_3d(str(tmp / "demo.step"))
    record("export_3d", PASS if result.get("ok") else FAIL)

    result = await client.get_design_rules()
    clearance = result.get("rules", {}).get("constraints", {}).get("min_clearance", {})
    record(
        "get_design_rules",
        PASS if clearance.get("value_nm") == 100000 else FAIL,
        json.dumps(clearance),
    )

    result = await client.get_bounding_box(["track-id"], include_text=True)
    record(
        "get_bounding_box",
        PASS if result.get("boxes") else FAIL,
        json.dumps(result.get("boxes")),
    )

    netlist_path = tmp / "demo.net"
    netlist_path.write_text("(export)\n", encoding="utf-8")
    result = await client.import_netlist(str(netlist_path), match_mode="reference", dry_run=True)
    record(
        "import_netlist(dry_run)",
        PASS
        if result.get("new_footprint_count") == 2 and result.get("match_mode") == "reference"
        else FAIL,
    )

    result = await client.set_project_net_classes(
        [{"name": "Power", "board": {"clearance": {"value_nm": 200000}}}],
        dry_run=True,
    )
    requested = result.get("requested_net_classes", [{}])[0]
    record(
        "set_project_net_classes(dry_run)",
        PASS if requested.get("clearance_nm") == 200000 else FAIL,
        json.dumps(requested),
    )

    if not enable_mutations:
        gated = await client.set_design_rules({"severities": []})
        record(
            "mutation_gate",
            PASS if gated.get("ok") is False else FAIL,
            str(gated.get("message"))[:80],
        )
        return

    embedded_source = tmp / "logo.png"
    embedded_source.write_bytes(b"fake-png")

    checks: list[tuple[str, Any, Any]] = [
        (
            "set_design_rules",
            lambda outcome: outcome.get("rules", {}).get("severities")
            == [{"rule_type": 5, "severity": 4}],
            client.set_design_rules({"severities": [{"rule_type": 5, "severity": 4}]}),
        ),
        (
            "set_custom_design_rules",
            lambda outcome: outcome.get("requested_rules", [{}])[0].get("name")
            == "Power clearance",
            client.set_custom_design_rules(
                [{"name": "Power clearance", "condition": "A.NetClass == 'Power'", "severity": 2}]
            ),
        ),
        (
            "add_embedded_files",
            lambda outcome: outcome.get("requested_files", [{}])[0].get("name") == "logo.png",
            client.add_embedded_files([str(embedded_source)]),
        ),
    ]

    for name, predicate, coro in checks:
        outcome = await coro
        record(name, PASS if outcome.get("ok") and predicate(outcome) else FAIL)


async def run_live_phase() -> None:
    client = KiCadIpcClient(KiCadIpcConfig.from_env())

    status = await client.check_connection()
    if not status.get("ok"):
        record("live_connection", SKIP, str(status.get("message"))[:120])
        return

    record("live_connection", PASS, f"KiCad {status.get('kicad_version')}")

    for name, coro in (
        ("live_get_paths", client.get_paths()),
        ("live_export_gerbers(dry_validation)", client.export_gerbers("")),
    ):
        result = await coro
        if name.endswith("(dry_validation)"):
            record(name, PASS if result.get("ok") is False else FAIL, str(result.get("message"))[:120])
        else:
            record(name, PASS if result.get("ok") else SKIP, str(result.get("message", ""))[:120])


async def main() -> None:
    print(f"KiPilot MCP verification script — package version {__version__}")
    print("-" * 72)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = pathlib.Path(tmp_dir)
        print("Phase 1: in-process fake KiCad endpoint (mutations disabled)")
        await run_fake_phase(tmp, enable_mutations=False)
        print()
        print("Phase 2: in-process fake KiCad endpoint (mutations enabled)")
        await run_fake_phase(tmp, enable_mutations=True)

    print()
    print("Phase 3: live KiCad IPC endpoint (optional)")
    await run_live_phase()

    failures = [name for name, status, _ in RESULTS if status == FAIL]
    print("-" * 72)
    print(f"Checks: {len(RESULTS)}  failures: {len(failures)}")
    for name in failures:
        print(f"  FAILED: {name}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
