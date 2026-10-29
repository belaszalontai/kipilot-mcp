# KiPilot MCP v0.4.0

Release date: 2026-10-29

KiPilot 0.4.0 grows the MCP surface from 135 to **144 tools** and adds the KiCad 11
library, library-aware symbol placement, and schematic PNG export surface.

## Highlights

- **Library browsing (7 new tools)** — list loaded symbol and footprint libraries,
  inspect real definitions with pins, alternate pin names, pads, fields, texts,
  shapes, 3D model references, and attributes, then reload or wait for asynchronous
  library loads.
- **Library-aware symbol placement (1 new tool)** — place a symbol from a loaded
  library so pins, fields, graphics, unit selection, and reference assignment are
  preserved instead of constructing an empty definition client-side.
- **Schematic PNG export (1 new tool)** — plot the current schematic at 72–2400 DPI
  with optional anti-aliasing and all-sheets or single-sheet output.
- **BOM compatibility for KiCad 11** — default CSV format and a grouped-by-value
  field set when the caller omits those settings.
- **Safer job reporting** — failed schematic plot, netlist, and BOM jobs now return a
  tool error with the KiCad job message instead of a false success.

## New MCP tools

| Tool | Purpose |
| --- | --- |
| `kicad_lib_list_symbols` | List symbol identifiers from loaded symbol libraries. |
| `kicad_lib_get_symbol` | Load one symbol definition with pins, alternates, fields, attributes, and unit counts. |
| `kicad_lib_list_footprints` | List footprint identifiers from loaded footprint libraries. |
| `kicad_lib_get_footprint` | Load one footprint definition with pads, fields, texts, shapes, and 3D models. |
| `kicad_lib_statuses` | Report per-library load status and aggregate counts. |
| `kicad_lib_reload` | Ask KiCad to reload library table rows from disk. |
| `kicad_lib_wait` | Wait until asynchronous library loads finish. |
| `kicad_sch_place_symbol_from_library` | Place a real library symbol on a schematic sheet with dry-run previews. |
| `kicad_sch_export_png` | Export schematic sheets to PNG with DPI, anti-aliasing, and sheet-mode control. |

## Improvements

- BOM export now defaults to KiCad's built-in CSV preset when no format settings are
  supplied, and defaults to a grouped-by-value field set (Reference, Value, Footprint,
  Datasheet, Qty, DNP) when neither a field preset nor an explicit field list is given.
- BOM format settings expose `include_byte_order_mark`; field settings expose
  `filter_scope`, `filter`, and `sort_field`.
- Library tools report clear, editor-specific capability errors when the active KiCad
  endpoint does not expose the matching library IPC handler.
- The Windows packaging smoke test retries once before failing, covering first-run
  antivirus and Defender scans of a freshly built executable.

## Compatibility and requirements

- PCB tools continue to run against stable KiCad 10.x (10.0.6 or later recommended).
- Library browsing, library-aware symbol placement, and schematic PNG export require
  a KiCad 11 (master/nightly) build with the library and job IPC handlers.
- Symbol library tools need the Schematic Editor kiface. Footprint library tools need
  a session with the PCB kiface loaded; the KiCad project manager, PCB Editor, and
  Footprint Editor all work. An eeschema-only endpoint reports a capability error for
  footprint tools.
- Library loads are asynchronous. Call `kicad_lib_wait` after KiCad starts or after
  `kicad_lib_reload` before treating an empty listing as an empty library.
- The Windows ZIP bundles the vendored `kicad-python` 0.9.0.dev0 wheel rebuilt with
  the library protos, plus its own Python runtime. No separate binding install is
  needed.

## Verification

- Unit and verification suite: **209 tests passed**.
- `scripts/verify_v0_4_0.py`: **16/16 checks passed**.
- `scripts/verify_v0_3_0.py`: **31/31 checks passed**.
- Live validation against a local KiCad 10.99 build: 223 symbol libraries loaded,
  155 footprint libraries loaded, 15,468 footprints listed, `Device:R` symbol lookup,
  `Resistor_SMD:R_0603_1608Metric` footprint lookup with 2 pads, library-aware symbol
  placement, schematic PNG export, BOM export, and netlist export.

## Windows package

The release workflow builds and attaches:

`kipilot-mcp-0.4.0-windows-x64.zip`

The packaged executable exposes 144 MCP tools and passes the bundled
`kicad-python` capability probe plus the MCP handshake smoke test.

## Known limitations

- KiCad 11.0.0 has no announced release date yet; use a master/nightly build for the
  new library, placement, and PNG tools.
- Library tools read and place existing definitions; they do not author or edit
  symbol, footprint, or library files.
- Footprint library tools do not work from an eeschema-only endpoint; load the PCB
  kiface by starting the KiCad project manager, PCB Editor, or Footprint Editor.
