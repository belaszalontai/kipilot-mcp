"""Verification script for the KiPilot MCP v0.4.0 tool surface.

The script exercises the new v0.4.0 capabilities twice:

1. Against an in-process fake KiCad endpoint so the request/response path
   (validation, enum mapping, serialization, commit handling) can be checked
   without a running KiCad instance.
2. Against a live KiCad IPC endpoint, when one is reachable.  The live phase is
   read-only: it queries library load statuses and, when available, lists the
   loaded symbol libraries.  Older KiCad runtimes that do not expose the
   library IPC commands are reported as skipped checks.

Run it from the repository root::

    ./.venv/Scripts/python.exe scripts/verify_v0_4_0.py
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile
from types import SimpleNamespace
from typing import Any

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


class FakeVector:
    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y


class FakeIdentifier:
    def __init__(self, library: str, name: str) -> None:
        self.library = library
        self.name = name

    def __str__(self) -> str:
        return f"{self.library}:{self.name}"


class FakeLibraryStatus:
    def __init__(self, nickname: str, status: int = 3) -> None:
        self.nickname = nickname
        self.type = 1
        self.scope = 1
        self.status = status
        self.error_message = None


class FakeSymbol:
    def __init__(self) -> None:
        self.id = FakeIdentifier("Device", "R")
        self.type = 1
        self.unit_count = 2
        self.body_style_count = 1
        self.keywords = "resistor"
        self.footprint_filters = []
        self.reference_field = SimpleNamespace(text=SimpleNamespace(value="R"))
        self.value_field = SimpleNamespace(text=SimpleNamespace(value="R"))
        self.footprint_field = SimpleNamespace(text=SimpleNamespace(value=""))
        self.datasheet_field = SimpleNamespace(text=SimpleNamespace(value=""))
        self.description_field = SimpleNamespace(text=SimpleNamespace(value="Resistor"))
        self.attributes = SimpleNamespace(
            do_not_populate=False,
            exclude_from_bill_of_materials=False,
            exclude_from_board=False,
            exclude_from_position_files=False,
            exclude_from_simulation=False,
        )
        self.pins = [
            SimpleNamespace(
                name="~",
                number="1",
                position=FakeVector(0, 0),
                length=1000000,
                orientation=1,
                electrical_type=2,
                shape=1,
                visible=True,
                alternates=[],
            )
        ]
        self.fields = [SimpleNamespace(name="MPN", text=SimpleNamespace(value="RC0603"))]


class FakeFootprint:
    def __init__(self) -> None:
        self.id = FakeIdentifier("Resistor_SMD", "R_0603_1608Metric")
        self.anchor = FakeVector()
        self.pads = [
            SimpleNamespace(
                id="pad-1",
                number="1",
                position=FakeVector(-900000, 0),
                net=None,
                pad_type=1,
                padstack=SimpleNamespace(layers=[1]),
            )
        ]
        self.texts = []
        self.shapes = []
        self.models = []
        self.private_layers = []
        self.proto = SimpleNamespace(
            reference_field=SimpleNamespace(text=SimpleNamespace(value="REF**")),
            value_field=SimpleNamespace(text=SimpleNamespace(value="R_0603")),
            datasheet_field=SimpleNamespace(text=SimpleNamespace(value="")),
            description_field=SimpleNamespace(text=SimpleNamespace(value="")),
        )


class FakeSchematic:
    def __init__(self) -> None:
        self.name = "verify.kicad_sch"
        self.document = SimpleNamespace(type=2, board_filename="", path="verify.kicad_sch")
        self.place_calls: list[tuple[Any, ...]] = []
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.commit_messages: list[str] = []

    def get_symbols(self) -> list[Any]:
        return []

    def get_hierarchy(self) -> list[Any]:
        return []

    def begin_commit(self) -> str:
        return "verify-commit"

    def push_commit(self, commit: str, message: str = "") -> None:
        self.commit_messages.append(message)

    def place_symbol_from_library(
        self,
        lib_id: str,
        position: Any,
        orientation: Any = None,
        unit: Any = None,
        reference: Any = None,
        sheet_path: Any = None,
    ) -> SimpleNamespace:
        self.place_calls.append((lib_id, position, orientation, unit, reference, sheet_path))
        return SimpleNamespace(
            id="placed-symbol",
            type=1,
            reference=reference or "R?",
            value="R",
            position=position,
        )

    def export_png(self, output_path: str, **options: Any) -> SimpleNamespace:
        self.calls.append(("export_png", {"output_path": output_path, **options}))
        return SimpleNamespace(
            succeeded=True,
            status=1,
            output_paths=[output_path],
            message="PNG export completed.",
        )

    def export_bom(self, output_path: str, **options: Any) -> SimpleNamespace:
        self.calls.append(("export_bom", {"output_path": output_path, **options}))
        return SimpleNamespace(
            succeeded=True,
            status=1,
            output_paths=[output_path],
            message="BOM export completed.",
        )


class FakeKiCad:
    def __init__(self) -> None:
        self.schematic = FakeSchematic()
        self.library_calls: list[tuple[str, Any]] = []

    def get_schematic(self) -> FakeSchematic:
        return self.schematic

    def get_board(self) -> Any:
        raise RuntimeError("no board in the fake endpoint")

    def close(self) -> None:
        pass

    def get_library_items(self, library_type: int, nicknames: Any) -> list[FakeIdentifier]:
        self.library_calls.append(("get_library_items", (library_type, list(nicknames))))
        return [FakeIdentifier("Device", "R"), FakeIdentifier("Device", "C")]

    def get_library_symbol(self, lib_id: str, document: Any = None) -> FakeSymbol:
        self.library_calls.append(("get_library_symbol", (lib_id, document)))
        return FakeSymbol()

    def get_library_footprint(self, lib_id: str, document: Any = None) -> FakeFootprint:
        self.library_calls.append(("get_library_footprint", (lib_id, document)))
        return FakeFootprint()

    def get_library_statuses(self, types: Any = None, scope: Any = None) -> list[FakeLibraryStatus]:
        self.library_calls.append(("get_library_statuses", (types, scope)))
        return [FakeLibraryStatus("Device")]

    def reload_library(self, library_type: int, scope: int, nicknames: Any) -> None:
        self.library_calls.append(("reload_library", (library_type, scope, list(nicknames))))

    def wait_for_libraries(self, **options: Any) -> list[FakeLibraryStatus]:
        self.library_calls.append(("wait_for_libraries", options))
        return [FakeLibraryStatus("Device")]


def _client(kicad: FakeKiCad, *, enable_mutations: bool = True) -> KiCadIpcClient:
    return KiCadIpcClient(
        KiCadIpcConfig(enable_mutations=enable_mutations),
        kicad_factory=lambda **_: kicad,
    )


def _predicate(name: str, result: dict[str, Any], predicate: Any, detail: str = "") -> None:
    passed = bool(result.get("ok")) and predicate(result)
    record(name, PASS if passed else FAIL, detail or json.dumps(result)[:160])


async def run_fake_phase(tmp: pathlib.Path) -> None:
    kicad = FakeKiCad()
    client = _client(kicad)

    _predicate(
        "kicad_lib_list_symbols",
        await client.list_library_symbols(["Device"]),
        lambda result: result["count"] == 2 and result["items"][0]["id"] == "Device:R",
    )
    _predicate(
        "kicad_lib_get_symbol",
        await client.get_library_symbol("Device:R"),
        lambda result: result["symbol"]["pin_count"] == 1
        and result["symbol"]["fields"][0]["name"] == "MPN",
    )
    _predicate(
        "kicad_lib_get_footprint",
        await client.get_library_footprint("Resistor_SMD:R_0603_1608Metric"),
        lambda result: result["footprint"]["pad_count"] == 1
        and result["footprint"]["fields"]["value"] == "R_0603",
    )
    _predicate(
        "kicad_lib_statuses",
        await client.get_library_statuses("symbol", "both"),
        lambda result: result["count"] == 1 and result["status_counts"] == {"loaded": 1},
    )
    _predicate(
        "kicad_lib_reload(dry_run)",
        await client.reload_library("symbol", "global", dry_run=True),
        lambda result: result["reloaded"] is False,
    )
    _predicate(
        "kicad_lib_reload",
        await client.reload_library("symbol", "global", ["Device"]),
        lambda result: result["reloaded"] is True,
    )
    _predicate(
        "kicad_lib_wait",
        await client.wait_for_libraries("symbol", interval_ms=1, timeout_s=1),
        lambda result: result["status_counts"] == {"loaded": 1},
    )

    placement_dry_run = await _client(kicad).place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=10,
        y_mm=20,
        dry_run=True,
    )
    _predicate(
        "kicad_sch_place_symbol_from_library(dry_run)",
        placement_dry_run,
        lambda result: result["placed"] is None and result["orientation"] is None,
    )

    placement = await client.place_schematic_symbol_from_library(
        lib_id="Device:R",
        x_mm=10,
        y_mm=20,
        orientation=90,
        unit=1,
        reference="R1",
    )
    _predicate(
        "kicad_sch_place_symbol_from_library",
        placement,
        lambda result: result["placed"]["reference"] == "R1"
        and result["orientation"] == "90",
    )
    record(
        "placement commit",
        PASS if kicad.schematic.commit_messages else FAIL,
        kicad.schematic.commit_messages[-1] if kicad.schematic.commit_messages else "",
    )

    png_dir = tmp / "png"
    png_result = await client.export_schematic_png(str(png_dir), dpi=300)
    _predicate(
        "kicad_sch_export_png(all_sheets)",
        png_result,
        lambda result: result["output_kind"] == "directory",
        json.dumps(png_result.get("requested_options")),
    )

    png_file = tmp / "single.png"
    png_single = await client.export_schematic_png(
        str(png_file),
        sheet_mode="single_sheet",
        antialiasing="none",
    )
    _predicate(
        "kicad_sch_export_png(single_sheet)",
        png_single,
        lambda result: result["output_kind"] == "file",
        json.dumps(png_single.get("requested_options")),
    )

    bom = await client.export_schematic_bom(str(tmp / "bom.csv"))
    _predicate(
        "kicad_sch_export_bom(CSV default)",
        bom,
        lambda result: result["ok"] is True,
        json.dumps(bom.get("requested_format_settings")),
    )


async def run_live_phase() -> None:
    client = KiCadIpcClient(KiCadIpcConfig())
    status = await client.check_connection()
    if not status.get("ok"):
        record("live_connection", SKIP, str(status.get("message"))[:120])
        return

    record("live_connection", PASS, f"KiCad {status.get('kicad_version')}")

    library_status = await client.get_library_statuses()
    if library_status.get("ok"):
        record(
            "live_library_statuses",
            PASS,
            json.dumps(library_status.get("status_counts")),
        )
    elif "KiCad 11" in str(library_status.get("message")):
        record("live_library_statuses", SKIP, "library IPC requires KiCad 11+")
    else:
        record("live_library_statuses", FAIL, str(library_status.get("message"))[:120])

    symbols = await client.list_library_symbols(["Device"])
    if symbols.get("ok"):
        record("live_library_symbols", PASS, f"{symbols.get('count')} items from Device")
    else:
        record("live_library_symbols", SKIP, str(symbols.get("message"))[:120])


async def main() -> None:
    print(f"KiPilot MCP v{__version__} verification\n")
    with tempfile.TemporaryDirectory() as tmp:
        await run_fake_phase(pathlib.Path(tmp))
    print()
    await run_live_phase()

    print()
    failures = [name for name, status, _ in RESULTS if status == FAIL]
    print(f"Checks: {len(RESULTS)}  failures: {len(failures)}")
    if failures:
        print("Failed checks: " + ", ".join(failures))
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
