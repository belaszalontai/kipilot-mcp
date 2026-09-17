<p align="center">
	<img src="KiPilot.svg" alt="KiPilot MCP">
</p>

# KiPilot MCP

KiPilot is a Python-based Model Context Protocol (MCP) server that connects MCP-aware clients, such as GitHub Copilot in VS Code, to a user-controlled KiCad 10.x GUI session through the official `kicad-python` IPC binding.

The server runs over `stdio`, exposes PCB-first MCP tools plus a build-gated schematic subset, and is designed for live KiCad workflows where the user keeps full control of the GUI session.

## Usage Videos

Usage videos are available at [kipilot.org/galery.html](https://kipilot.org/galery.html).

## Documentation

Public project documentation is available at [kipilot.org/docs.html](https://kipilot.org/docs.html).

## What's New In 0.3.0

The 0.3.0 release grows the MCP surface from 102 to 135 tools and closes the largest gaps between the
Python binding surface and the MCP tool surface:

- **Board manufacturing export jobs (14 new tools)** — SVG, DXF, PDF, PostScript, Gerber, NC drill,
  pick-and-place position, GenCAD, IPC-2581, IPC-D-356, ODB++, statistics, STEP/STEPZ 3D models, and
  raytraced 3D renders, all driven by the KiCad-side export jobs of the IPC API
- **Design rule access (4 new tools)** — read and merge-update board design rules (minimum constraints,
  predefined sizes, DRC severities, exclusions) and read/replace custom rules
- **Embedded file management (3 new tools)** — list, add, or replace fonts, 3D models, and datasheets
  embedded in the board file; `kicad-python` performs the zstd compression for you
- **Netlist import and geometry helpers (2 new tools)** — forward-annotate a schematic netlist into the
  board, and query KiCad-side bounding boxes for board items
- **Workspace and session tools (8 new tools)** — KiCad filesystem paths, binary and plugin settings
  paths, TOOL_ACTION execution, headless document open/create/close, and project net class writes
- **Schematic lifecycle (2 new tools)** — `kicad_sch_save_as` and `kicad_sch_revert`
- **Richer item reads** — `kicad_get_items` now covers board tables, grid items, constraints, and
  reference points, while `kicad_sch_get_items` additionally reads sheets, sheet pins, images, shapes,
  bus entries, rule areas, tables, groups, text boxes, directive labels, fields, and pins
- **Verification script** — `scripts/verify_v0_3_0.py` exercises the new surface against an in-process
  fake endpoint (and a live endpoint when one is reachable), so the release can be checked without a
  running KiCad instance

Every new mutation keeps the existing safety contract: `dry_run` previews without the mutation gate,
real writes need `KIPILOT_ENABLE_MUTATIONS=1`, and destructive operations (embedded-file replacement,
schematic revert) also need `force=true`.

## Overview

KiPilot exists to let an MCP client inspect and manipulate KiCad documents that are already open in the user-controlled GUI session, with PCB workflows as the primary baseline.

- Uses the official KiCad IPC path through `kicad-python`
- Runs as a `stdio` MCP server for VS Code and similar hosts
- Supports read-heavy PCB workflows plus guarded mutation tools
- Adds a source-build-gated schematic surface for hierarchy, hit-testing, metadata mutation, and export workflows where the running KiCad build exposes the newer schematic IPC handlers
- Adds selected higher-level MCP helpers on top of raw IPC primitives, such as a real footprint side-flip workflow that mirrors child artwork and swaps paired layers
- Keeps KiCad as a separate, user-launched GUI application

This repository targets the KiCad 10 PCB-first baseline. It does not aim to be a 1:1 wrapper over every public method exposed by the KiCad Python binding.

Where the raw IPC surface does not expose a single native operation but the underlying board objects are still mutable, KiPilot may provide a higher-level MCP tool that composes those lower-level capabilities into one agent-friendly action. The current example is `kicad_flip_footprint`, which performs a real mirrored side flip even though the KiCad binding does not expose one direct footprint-flip call.

## Current Scope

Implemented MCP surface includes:

- MCP stdio server entry point
- Async-friendly KiCad IPC client wrapper around `kipy.KiCad`
- Connectivity and version checks such as `ping_kicad` and `get_kicad_version`
- Board and document inspection tools for open documents, outlines, stackup, footprints, nets, pads, tracks, vias, zones, graphics, dimensions, groups, reference images, barcodes, tables, grid items, constraints, reference points, text, text geometry, bounding boxes, project text variables, project net classes, origins, title blocks, selection state, and connectivity
- Filtered lookup tools for footprints, footprint-scoped pads, nets, net classes, and connected items
- Board manufacturing export tools for SVG, DXF, PDF, PostScript, Gerber, drill, position, GenCAD, IPC-2581, IPC-D-356, ODB++, statistics, 3D models, and 3D renders
- Design rule tools for board design rules, custom rules, DRC severities, and rule exclusions
- Embedded file tools for fonts, 3D models, and datasheets stored inside the board file
- Workspace tools for KiCad paths, binaries, plugin settings directories, TOOL_ACTION execution, and headless document lifecycle
- Guarded mutation tools for visible layers, active layer, enabled layers, footprint move/rotate/flip, footprint pad net reassignment, origins, title block fields, board text, track creation, via creation, item updates, track geometry, zone outlines, item deletion, zone refill, netlist import, project net classes, board revert, and board save
- Schematic hierarchy, netlist, hit-testing, page-settings, title-block, metadata-mutation, lifecycle (save-as/revert), item reads, and export tools when the active KiCad runtime exposes schematic IPC support
- 135 MCP tools total, covered by unit tests plus a runnable verification script
- Unit tests for IPC connection and error-handling behavior

Committed baseline:

- GUI IPC only
- PCB editor first
- Initial schematic inspection, hit-testing, metadata mutation, and export workflows are supported only when the running KiCad build exposes the newer schematic IPC surface
- Read-heavy workflows first, validated mutation workflows second
- No committed headless automation scope

## Schematic MCP Surface

See the new surface section below for the 0.3.0 schematic lifecycle tools and the extended item kinds.

The schematic surface is intentionally smaller and more runtime-dependent than the PCB surface.

Available schematic tools:

- Inspection: `kicad_sch_get_hierarchy`, `kicad_sch_get_netlist`, `kicad_sch_get_page_settings`, and `kicad_sch_get_title_block`
- Inspection geometry: `kicad_sch_hit_test`
- Guarded metadata mutation: `kicad_sch_set_page_settings` and `kicad_sch_set_title_block`
- Plot export: `kicad_sch_export_svg`, `kicad_sch_export_dxf`, `kicad_sch_export_pdf`, and `kicad_sch_export_ps`
- File export: `kicad_sch_export_netlist` and `kicad_sch_export_bom`

Important export semantics:

- `kicad_sch_export_svg`, `kicad_sch_export_dxf`, and `kicad_sch_export_ps` take `output_dir` because KiCad writes one file per plotted sheet into a directory.
- `kicad_sch_export_pdf` takes `output_file` because KiCad writes one PDF file to a file path.
- `kicad_sch_export_netlist` and `kicad_sch_export_bom` also take `output_file` because they produce single file outputs.
- When you want a full schematic export, `plot_all=true` with omitted `plot_pages` is the safest default unless you already know the exact sheet-instance paths to filter.
- In this environment, live end-to-end schematic MCP validation succeeded against a locally built `kicad-master` `eeschema` snapshot. The installed official KiCad 10.0.1 build did not expose the same reliable external schematic IPC behavior, so treat the schematic surface as source-build-gated rather than universally available across all KiCad 10 installations. Upstream KiCad 10.0.x registers only `GetOpenDocuments` on the schematic API handler, which is why the schematic tools need a KiCad 11 (master/nightly) build.

## Board Export, Rules And Workspace Surface (0.3.0)

### Board export jobs

These tools call the KiCad-side export jobs of the IPC API, so the output matches what the GUI and
`kicad-cli` produce. Directory-output jobs write one file per layer (or per board) into a directory;
file-output jobs write exactly one file.

| Tool | Output | Notes |
| --- | --- | --- |
| `kicad_export_board_svg` | directory | `fit_page_to_board`, `precision`, optional `plot_settings` |
| `kicad_export_board_dxf` | directory | contour plotting, polygon mode, units |
| `kicad_export_board_pdf` | file | metadata, single-document mode, background color, property popups |
| `kicad_export_board_ps` | directory | `force_a4`, global settings |
| `kicad_export_gerbers` | directory | X2 attributes, job file, Protel extensions, precision |
| `kicad_export_drill` | directory | `drill_format` (`excellon` or `gerber`), origin, map format, report file |
| `kicad_export_position` | file | optional `PositionExportSettings`-shaped mapping |
| `kicad_export_gencad` | file | pad flipping, individual shapes, drill origin |
| `kicad_export_ipc2581` | file | optional settings mapping |
| `kicad_export_ipc_d356` | file | — |
| `kicad_export_odb` | directory | units, precision, compression, drawing sheet, variant |
| `kicad_export_stats` | file | report or JSON output |
| `kicad_export_3d` | file | STEP/STEPZ, optional settings mapping |
| `kicad_export_render` | file | raytraced render, optional settings mapping |

`plot_settings` accepts the same object shape as `kicad_set_board_plot_settings`, so a plot preset can be
read once with `kicad_get_board_plot_settings`, adjusted, and reused for several export formats. Settings
mappings for 3D, render, position, and IPC-2581 exports use snake_case proto field names and are merged
into the matching KiCad job settings object; unknown fields are rejected with a helpful error.

### Design rules

| Tool | Kind | Notes |
| --- | --- | --- |
| `kicad_get_design_rules` | read | minimum constraints, predefined sizes, solder mask/paste, teardrops, via protection, DRC severities and exclusions (KiCad 11) |
| `kicad_set_design_rules` | guarded write | merges the given fields into the current rules; repeated fields are replaced, not appended |
| `kicad_get_custom_design_rules` | read | parsed `.kicad_dru` rules plus parse status and error text |
| `kicad_set_custom_design_rules` | guarded write | replaces the custom rule set; an empty list clears the rules file |

Design rule payloads round-trip: the objects returned by the `kicad_get_*` tools can be edited and passed
back to the matching `kicad_set_*` tool, because both directions use the same proto field names.

### Embedded files

| Tool | Kind | Notes |
| --- | --- | --- |
| `kicad_get_embedded_files` | read | lists name, type, hash, and compressed size; `include_data=true` also returns base64 payloads |
| `kicad_add_embedded_files` | guarded write | embeds the given local files, keeping existing embedded files |
| `kicad_set_embedded_files` | guarded + destructive | replaces all embedded files, therefore also requires `force=true` |

### Forward annotation, geometry and workspace

| Tool | Kind | Notes |
| --- | --- | --- |
| `kicad_import_netlist` | guarded write | imports a schematic netlist: match mode (`uuid`/`reference`), delete extra footprints, update footprints, transfer groups, override locks |
| `kicad_get_bounding_box` | read | KiCad-side bounding boxes for up to N board item IDs, plus a merged box |
| `kicad_set_project_net_classes` | guarded write | creates or updates net classes; `merge_mode` is `merge` or `replace` |
| `kicad_get_paths` | read | well-known KiCad filesystem paths (library, template, plugin roots) |
| `kicad_get_kicad_binary_path` | read | absolute path of a KiCad binary such as `kicad-cli` |
| `kicad_get_plugin_settings_path` | read | per-plugin writable settings directory |
| `kicad_run_action` | guarded write | runs a KiCad TOOL_ACTION by name, for example `pcbnew.EditorControl.zoneFillAll` |
| `kicad_open_document` | guarded write | headless API server sessions only |
| `kicad_create_document` | guarded write | headless API server sessions only |
| `kicad_close_document` | guarded write | headless API server sessions only |

### Item kinds

`kicad_get_items` accepts the additional board item kinds `table`, `grid_item`, `constraint`, and
`reference_point`. `kicad_sch_get_items` accepts the additional schematic read kinds `sheet`, `sheet_pin`,
`image`, `shape`, `bus_entry`, `rule_area`, `table`, `group`, `text_box`, `directive_label`, `field`, and
`pin`. Only the original creation kinds can be created or updated; the additional kinds are read-only.

## Requirements

- KiCad 10.x installed locally for the PCB surface
- A KiCad 11 build (master/nightly) for the schematic surface — see below
- A running KiCad GUI instance with IPC API support
- Python 3.11+ for source installs and local ZIP builds
- Git for source installs

The supported KiCad version depends on the tool family you use:

- PCB tools run against the stable KiCad 10.x series (10.0.6 or later recommended).
- Schematic tools require a KiCad build that implements the schematic IPC handlers. Upstream KiCad 10.0.x
  registers only `GetOpenDocuments` on the schematic API handler, so schematic tools fail there with a
  capability error. The full schematic surface (item reads and writes, selection, page settings, title block,
  exports, and design variants) is implemented on the KiCad master branch, which is the KiCad 11 development
  line. KiCad 11.0.0 has no announced release date yet.
- The Python wrapper side is already available in source form: `kicad-python` from the upstream `main` branch
  (version `0.9.0.dev0`) and later. The 0.9.0 release is not on PyPI yet, so packaging that needs the schematic
  client bindings must vendor or pin the wrapper rather than rely on `pip install kicad-python`.
- The Windows ZIP release bundles both the Python runtime and the `kicad-python` binding, so no separate wrapper
  installation is needed when you install from the downloadable Windows artifact.

Use a stable CPython release such as 3.11, 3.12, or 3.13. Avoid preview or alpha Python interpreters because the native dependency chain may not publish wheels for them yet.

The Windows ZIP release bundles its own Python runtime for the server process, so local Python is not required when you install from the downloadable Windows artifact.

## Quick Start

Choose the installation path that fits your workflow:

- Windows ZIP release if you want a ready-to-run Windows MCP server without managing Python locally
- Source install if you want to inspect, modify, or develop the server from this repository

### Windows ZIP release

Download the latest Windows release ZIP from GitHub Releases, extract it, and point your MCP host at `kipilot-mcp.exe`.

- Latest release: https://github.com/belaszalontai/kipilot-mcp/releases/latest
- Artifact name pattern: `kipilot-mcp-<version>-windows-x64.zip`
- The ZIP contains the stdio server executable plus its bundled runtime

Example VS Code MCP configuration using the extracted Windows ZIP:

```json
{
	"servers": {
		"kipilot-mcp": {
			"type": "stdio",
			"command": "C:\\Tools\\kipilot-mcp-<version>-windows-x64\\kipilot-mcp.exe",
			"env": {
				"KIPILOT_KICAD_CLIENT_NAME": "kipilot-mcp",
				"KIPILOT_KICAD_TIMEOUT_MS": "60000",
				"KIPILOT_LOG_LEVEL": "INFO",
				"KIPILOT_LOG_FILE": ".logs/kipilot-mcp.log"
			}
		}
	}
}
```

Do not double-click the executable for normal use. Let your MCP host start it so stdio stays attached to the host.

### Source install

Clone the public repository:

```powershell
git clone https://github.com/belaszalontai/kipilot-mcp.git
cd kipilot-mcp
```

### Windows helper

On Windows, the repository includes a convenience script that creates `.venv` when needed, installs the runtime package, applies conservative default environment variables, and can start the server for manual checks:

```powershell
.\start-kipilot-mcp.ps1 -SkipRun
```

Run without `-SkipRun` to start the server process directly from a terminal:

```powershell
.\start-kipilot-mcp.ps1
```

For VS Code, Claude Desktop, and other MCP hosts, prefer configuring the host to launch `python -m kipilot_mcp.server` directly from the prepared environment. That keeps the stdio server command explicit and easy to audit.

### Manual install

A virtual environment is recommended for dependency isolation, but it is not a KiPilot-specific requirement. If you already manage Python environments another way, point your MCP host at that interpreter instead.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
```

For development and tests, install in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Start KiCad yourself, open the target hardware project, and open the PCB Editor before using board-aware MCP tools.

## Configuration

The IPC connection uses KiCad's official API endpoint. On Windows this is a named pipe; on macOS and Linux it is a Unix domain socket. When KiCad launches an API plugin it provides these environment variables:

```powershell
$env:KICAD_API_SOCKET = "..."
$env:KICAD_API_TOKEN = "..."
```

When the server is launched from VS Code rather than from KiCad, those variables may not be present. In that case `kicad-python` falls back to the default platform-dependent IPC endpoint, which is easiest to work with when only one KiCad instance is open.

KiPilot-specific settings:

```powershell
$env:KIPILOT_KICAD_CLIENT_NAME = "kipilot-mcp"
$env:KIPILOT_KICAD_TIMEOUT_MS = "60000"
$env:KIPILOT_ENABLE_MUTATIONS = "0"
$env:KIPILOT_COMMIT_MESSAGE_PREFIX = "KiPilot MCP"
$env:KIPILOT_LOG_LEVEL = "INFO"
$env:KIPILOT_LOG_FILE = ".logs/kipilot-mcp.log"
```

Operational notes:

- `KIPILOT_ENABLE_MUTATIONS=0` keeps live board writes disabled by default
- `dry_run=true` previews remain available even when writes are disabled
- destructive tools such as revert and delete still require `force=true`
- logs go to `stderr` by default so `stdout` stays clean for MCP traffic

## Running The Server

After a source installation, run:

```powershell
kipilot-mcp
```

or:

```powershell
python -m kipilot_mcp.server
```

Example VS Code MCP configuration for a source install:

```json
{
	"servers": {
		"kipilot-mcp": {
			"type": "stdio",
			"command": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
			"args": ["-m", "kipilot_mcp.server"],
			"env": {
				"KIPILOT_KICAD_CLIENT_NAME": "kipilot-mcp",
				"KIPILOT_KICAD_TIMEOUT_MS": "60000",
				"KIPILOT_LOG_LEVEL": "INFO",
				"KIPILOT_LOG_FILE": ".logs/kipilot-mcp.log"
			}
		}
	}
}
```

If your KiCad setup requires an explicit API socket or token, add `KICAD_API_SOCKET` and `KICAD_API_TOKEN` to the same `env` block.

The bundled `start-kipilot-mcp.ps1` script is useful for first-run setup and manual terminal checks on Windows. If you use the downloadable Windows ZIP, point the MCP host at `kipilot-mcp.exe` instead of the Python command. For source installs, MCP host configuration should normally use the direct Python command shown above so the host owns process startup and environment values.

## Development

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
python -m pytest
```

Run the release verification script (fake endpoint plus optional live endpoint):

```powershell
python scripts/verify_v0_3_0.py
```

Run linting:

```powershell
python -m ruff check .
```

Build the Windows ZIP release locally:

```powershell
.\build-windows-zip.ps1 -ForceInstall -Clean
```

That script creates a versioned archive at `artifacts/kipilot-mcp-<version>-windows-x64.zip`, includes `README.md` and `LICENSE` inside the archive, and is the same build path used by the GitHub Actions release workflow.

Release process checklist: see `RELEASE-CHECKLIST.md`.

## Repository Layout

```text
.
|-- agent-test/
|   |-- .github/
|   |-- .logs/
|   |-- .vscode/
|   `-- README.md
|-- src/
|   `-- kipilot_mcp/
|       |-- __init__.py
|       |-- config.py
|       |-- errors.py
|       |-- ipc_client.py
|       |-- ipc_client_core.py
|       |-- ipc_client_pcb.py
|       |-- ipc_client_sch.py
|       |-- lookups.py
|       |-- serializers.py
|       `-- server.py
|-- scripts/
|   `-- verify_v0_3_0.py
|-- tests/
|   |-- test_ipc_client.py
|   |-- test_ipc_client_schematic_write.py
|   `-- test_ipc_client_v030.py
|-- KiPilot.svg
|-- build-windows-zip.ps1
|-- pyproject.toml
|-- pyinstaller_entry.py
|-- README.md
`-- start-kipilot-mcp.ps1
```

## The `agent-test/` Folder

The `agent-test/` directory is a small standalone VS Code test workspace for validating the MCP server from the perspective of a real Copilot agent setup.

Its purpose is to provide:

- a clean workspace separate from the main source tree
- a ready-made `.vscode/mcp.json` configuration that points to the sibling KiPilot server
- custom Copilot agent and instruction files for KiCad-focused testing
- a controlled workspace for end-to-end MCP validation

Open `agent-test/` in a separate VS Code window when you want to test the full agent workflow end to end without mixing that setup into the main development workspace.

## References

- [kicad-python documentation](https://docs.kicad.org/kicad-python-main/)
- [KiCad IPC API for add-on developers](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html)

## Capability Mapping

The current capability map for the server target is documented in `.github/kicad-api-capabilities.md`. Use that file as the source of truth for deciding which MCP tools belong in the KiCad 10 baseline, which ones need stronger validation, and which ones are version-gated for future KiCad releases.