# KiPilot Agent Test Workspace

This folder is a small standalone VS Code test workspace for running a custom Copilot agent against the sibling `kipilot-mcp` MCP server.

Open this `agent-test` folder in a separate VS Code window if you want a clean workspace that contains:

- a ready-to-use workspace MCP configuration
- a dedicated KiCad hardware agent that works on both the board and the schematic
- project-level Copilot instructions for KiCad MCP usage
- a ready-to-run schematic showcase prompt
- a ready-to-run board release/export showcase prompt for the v0.3.0 tool families

## What Is Included

- `.vscode/mcp.json`: VS Code MCP server configuration for the sibling KiPilot server
- `.github/copilot-instructions.md`: always-on workspace instructions for this mini test project
- `.github/agents/kicad-agent.agent.md`: the custom electronics/KiCad agent definition, covering board and schematic work
- `.github/prompts/schematic-showcase.prompt.md`: the `/schematic-showcase` schematic showcase prompt
- `.github/prompts/board-release-showcase.prompt.md`: the `/board-release-showcase` manufacturing export and design rule prompt
- `.logs/` and `out/`: server log and export targets created at runtime (`out/sch-demo/`, `out/board-demo/`)

## What The v0.3.0 MCP Surface Adds

The test workspace is expected to run against KiPilot MCP v0.3.0 or newer, which exposes 135 tools. Use the **v0.3.1** Windows ZIP for this: it carries the same 135 tools, but ships a working bundled `kicad-python` binding (the 0.3.0 ZIP bundled the broken PyPI 0.8.0 wheel and could not start). The families below are the ones that most affect agent workflows:

| Family | Tools | KiCad build |
| --- | --- | --- |
| Board manufacturing exports | `kicad_export_board_svg`, `kicad_export_board_dxf`, `kicad_export_board_pdf`, `kicad_export_board_ps`, `kicad_export_gerbers`, `kicad_export_drill`, `kicad_export_position`, `kicad_export_gencad`, `kicad_export_ipc2581`, `kicad_export_ipc_d356`, `kicad_export_odb`, `kicad_export_stats`, `kicad_export_3d`, `kicad_export_render` | 10.x |
| Design rules | `kicad_get_design_rules`, `kicad_set_design_rules`, `kicad_get_custom_design_rules`, `kicad_set_custom_design_rules` | 11.0 master/nightly |
| Embedded files | `kicad_get_embedded_files`, `kicad_add_embedded_files`, `kicad_set_embedded_files` | 10.0.7+ |
| Workspace and session | `kicad_get_paths`, `kicad_get_kicad_binary_path`, `kicad_get_plugin_settings_path`, `kicad_run_action`, `kicad_open_document`, `kicad_create_document`, `kicad_close_document`, `kicad_set_project_net_classes` | 11.0 for paths and document creation; headless-only for document open/create/close |
| Forward annotation and geometry | `kicad_import_netlist`, `kicad_get_bounding_box` | 10.x |
| Schematic lifecycle | `kicad_sch_save_as`, `kicad_sch_revert` | 11.0 master/nightly |

Two behavioral notes matter for agent runs:

- Export tools write real files to disk. They do not modify the KiCad document, but they do need a writable target directory or file path, and large boards can exceed the IPC timeout. This workspace already raises it with `KIPILOT_KICAD_TIMEOUT_MS=120000`.
- `kicad_set_embedded_files` replaces every embedded file, and `kicad_sch_revert` discards unsaved work, so both require `force=true` on top of the mutation gate.

## Board Release Showcase (v0.3.0)

This workspace contains a second showcase that exercises the manufacturing export, design rule, and embedded-file surface:

| File | Purpose |
| --- | --- |
| `.github/prompts/board-release-showcase.prompt.md` | End-to-end board release prompt, invoked as `/board-release-showcase` |
| `out/board-demo/` | Export target for the Gerber, drill, position, SVG, PDF, ODB++, IPC-2581, statistics, and 3D outputs |

Run it the same way as the schematic showcase: open the `agent-test` folder, make sure the `kipilot-mcp` server is connected, open the board you want to use, select the `kicad-agent` agent, and run `/board-release-showcase`. Phases that need a newer KiCad build (design rules) are skipped with an explicit capability note instead of failing the run.

## Recommended Versions

Use the versions below for the smoothest setup on Windows:

| Component | Recommended | Notes |
| --- | --- | --- |
| Windows | Windows 10 or Windows 11 | This test harness is Windows-oriented because its MCP config points at a Windows virtual environment path |
| Python | Stable CPython 3.11, 3.12, or 3.13 x64 | Avoid preview or alpha interpreters |
| Supported Python range | 3.11+ | Declared by the project |
| KiCad | 10.x | Board tools and board manufacturing exports run against the stable 10.x series (10.0.6 or later recommended) |
| KiCad (schematic) | 11.0 master/nightly | The schematic surface needs a build that implements the schematic IPC handlers. Upstream 10.0.x only answers open-document queries there |
| KiCad (design rules) | 11.0 master/nightly | Board design rules, custom rules, KiCad paths, and headless document creation are KiCad 11 features |
| KiCad (embedded files) | 10.0.7+ | Listing and editing files embedded in the board file needs KiCad 10.0.7 or newer |
| `kicad-python` | bundled | Runtime dependency. The v0.3.0 features (design rules, custom rules, job-based exports, embedded files, schematic lifecycle) need the `0.9.0.dev0` binding from upstream `main`. The Windows ZIP bundles a prepared build of that binding (`vendor/kicad_python-*.whl`); the PyPI 0.8.0 wheel cannot be used for them at all, because several of its modules fail to import |
| `mcp` | `>=1.8.0,<2` | Runtime dependency |
| `pytest` | `>=8.3.0` | Optional, only for local test/development work |
| `pytest-asyncio` | `>=0.24.0` | Optional, only for local test/development work |
| `ruff` | `>=0.8.0` | Optional, only for local lint/development work |
| Microsoft Visual C++ Redistributable | latest 2015-2022 x64 release | Recommended on Windows for native dependency compatibility |

## Prerequisites

Install the following before using this workspace:

1. Git
2. A stable Python 3.11+ x64 release from python.org
3. KiCad 10.0.6 or later for board work, plus a KiCad 11 (master/nightly) build if you want the schematic tools
4. Microsoft Visual C++ Redistributable 2015-2022 x64
5. VS Code with GitHub Copilot / Copilot Chat and MCP support enabled

## One-Time KiPilot Server Setup

This test workspace expects the actual KiPilot server source to stay in the parent repository.
Run the setup command below once from this `agent-test` folder.

```powershell
Push-Location ..
.\start-kipilot-mcp.ps1 -SkipRun
Pop-Location
```

The helper creates or reuses the parent `.venv`, installs the KiPilot runtime package, and leaves the server stopped so VS Code can launch it through MCP.

For development work, install the optional test and lint dependencies from the parent repository:

```powershell
Push-Location ..
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Pop-Location
```

What the runtime setup installs into the parent `.venv`:

- `kipilot-mcp` in editable mode
- runtime dependencies:
  - `kicad-python>=0.7.1`
  - `mcp>=1.8.0,<2`
- optional development dependencies when you run the editable development install:
  - `pytest>=8.3.0`
  - `pytest-asyncio>=0.24.0`
  - `ruff>=0.8.0`

## KiCad Setup

Before you start the MCP server, prepare KiCad:

1. Start KiCad 10.x for board work, or your KiCad 11 (master/nightly) build for schematic work.
2. Open the target hardware project.
3. Open the editor whose document you want to drive: the PCB Editor, the Schematic Editor, or both. The project manager window on its own is not enough.
4. If needed in your KiCad build, enable the API under `Preferences -> Plugins -> Enable KiCad API`.
5. During setup, prefer having only one KiCad instance open.

## Open The Test Workspace

1. In VS Code, open this folder directly:

   `c:\Work\bitbucket\kipilot-mcp\agent-test`

2. Trust the workspace if VS Code asks.
3. Make sure GitHub Copilot is signed in.
4. Reload the window once after the first open if the agent list or MCP server does not appear immediately.

## MCP Server Configuration In This Workspace

This workspace already contains `.vscode/mcp.json`.

It is configured to start the sibling KiPilot server with:

- Python executable: `..\.venv\Scripts\python.exe`
- module: `kipilot_mcp.server`
- timeout: `120000 ms`
- log level: `INFO`
- log file: `.logs/kipilot-agent-test.log`
- mutations: enabled in this workspace (`KIPILOT_ENABLE_MUTATIONS=1`)

The parent `.venv` path is an intentional test-workspace convention so the checked-in MCP configuration can point at a predictable interpreter. It is not a general KiPilot requirement. This workspace has live writes enabled on purpose, so mutation tools take effect immediately; pass `dry_run=true` when you only want a preview.

## How To Start The MCP Server In VS Code

After opening this folder in a separate VS Code window:

1. Open the MCP / Copilot server management UI in VS Code.
2. Enable or start the `kipilot-mcp` server from this workspace.
3. Wait until VS Code shows that the MCP server is connected.
4. Open Copilot Chat.
5. Select the custom agent named `kicad-agent`.

If you want to manually run the server process for debugging, use:

```powershell
..\.venv\Scripts\python.exe -m kipilot_mcp.server
```

## How To Use The Custom Agent

The custom agent file is:

`agent-test/.github/agents/kicad-agent.agent.md`

The `.agent.md` suffix is required by the VS Code custom-agent convention, so the file uses that exact standard filename pattern.

Once the workspace is open:

1. Open Copilot Chat.
2. Pick the `kicad-agent` custom agent.
3. Start with a connectivity check prompt such as:

```text
Run ping_kicad and tell me whether KiCad is reachable.
```

4. Then continue with board prompts, for example:

```text
Summarize the currently open PCB and list the first ten footprints.
```

```text
Find footprint R1 and preview moving it to x=42.0 mm, y=18.5 mm.
```

```text
Use the KiCad MCP tools to find the footprint whose value is LOGO. Report which copper side it is currently on, then flip it to the opposite side. After the operation, verify that the footprint side changed and that any child artwork moved onto the mirrored side-specific silkscreen layer. If live writes are disabled, do the same flow as a dry run and say that explicitly.
```

5. For schematic work on a KiCad 11 build, use prompts such as:

```text
Summarize the currently open schematic: title block, page settings, hierarchy, symbol count, and the number of nets in the netlist.
```

```text
Draw a documented test-point block in a free area of this sheet with wires, a junction, a no-connect marker, a local label, a global label, and two text items. Show the dry run first, then apply it and highlight the created items.
```

```text
Create a DNP design variant, describe it, switch to it, and export the BOM for that variant.
```

## Schematic Showcase On KiCad 11

The schematic surface shipped in KiPilot MCP v0.2.0 and was extended in v0.3.0 with document lifecycle tools (`kicad_sch_save_as`, `kicad_sch_revert`) and wider item reads. It needs a KiCad build that implements the schematic IPC handlers. Upstream KiCad 10.0.x registers only `GetOpenDocuments` on the schematic API handler, so use a KiCad 11 (master/nightly) build for schematic work.

This workspace contains a ready-to-run showcase for that surface:

| File | Purpose |
| --- | --- |
| `.github/agents/kicad-agent.agent.md` | Shared KiCad agent for board and schematic work; the showcase prompt drives the schematic flow |
| `.github/prompts/schematic-showcase.prompt.md` | End-to-end showcase prompt, invoked as `/schematic-showcase` |
| `out/sch-demo/` | Export target for the SVG, PDF, netlist, and BOM produced by the showcase |

### Prerequisite: Build And Run KiCad 11

Build the schematic editor. The `eeschema` target also builds the `eeschema_kiface` module that carries the schematic IPC handler:

```bash
cmake --build <build-dir> --target eeschema --parallel
cmake --build <build-dir> --target bitmap_archive_build api_schema_build_copy --parallel
```

Then start `eeschema.exe` from the `<build-dir>/eeschema` directory with `KICAD_RUN_FROM_BUILD_DIR=1` and the build subdirectories on `PATH`, open a project in the Schematic Editor, and enable the API if your build requires it.

### Running The Showcase

1. Open this `agent-test` folder as the workspace root.
2. Make sure the `kipilot-mcp` MCP server shows as connected.
3. Open the schematic you want to record in KiCad.
4. In Copilot Chat, select the `kicad-agent` agent.
5. Run `/schematic-showcase`.

The showcase reads the live sheet, stamps the title block, draws an annotated functional block with wires, a junction, a no-connect marker, labels, and text, highlights the new objects through the selection API, edits and hit-tests an item, proves that the netlist changed, manages design variants, exports an SVG/PDF/netlist/BOM pack into `out/sch-demo`, and saves the document.

Run it against a copy of a project rather than work you care about: `KIPILOT_ENABLE_MUTATIONS=1` in `.vscode/mcp.json` makes the drawing, variant, and save steps real writes.

## Default Safety Behavior

This test workspace currently ships with live writes enabled:

- `KIPILOT_ENABLE_MUTATIONS=1` in `.vscode/mcp.json`
- read tools work normally
- mutation tools apply immediately unless you pass `dry_run=true` yourself
- destructive tools such as board revert, item deletion, variant deletion, and schematic revert still require explicit force guards, and `kicad_set_embedded_files` also requires `force=true` because it replaces every embedded file
- `kicad_import_netlist` is a large board mutation even when it runs cleanly: preview it with `dry_run=true` first, and make sure a save-as copy exists if you do not want the forward annotation persisted
- export tools never change the document, but they do write files into `agent-test/out/` and can be slow on large boards
- schematic mutations only land when the connected KiCad build supports the schematic IPC handlers

To go back to the conservative default, edit `.vscode/mcp.json` and change:

```json
"KIPILOT_ENABLE_MUTATIONS": "1"
```

to:

```json
"KIPILOT_ENABLE_MUTATIONS": "0"
```

Do that when you want exploration and dry-run previews only.

## Logs

By default the MCP server in this test workspace logs to:

`agent-test/.logs/kipilot-agent-test.log`

It also logs to `stderr`, which is useful when you manually run the server process.

## Quick Troubleshooting

### `ping_kicad` fails

- Make sure KiCad is already running.
- Make sure at least one editor is open: the PCB Editor, the Schematic Editor, or both.
- Confirm that the parent `.venv` exists and the editable install completed successfully.

### The MCP server does not start in VS Code

- Verify that `..\.venv\Scripts\python.exe` exists.
- Re-run the install commands from the `One-Time KiPilot Server Setup` section.
- Reload the VS Code window.

### The custom agent does not appear

- Confirm the file exists at `.github/agents/kicad-agent.agent.md`.
- Reload the VS Code window.
- Make sure you opened `agent-test` itself as the workspace root.

### Board tools fail but `ping_kicad` works

- You are likely connected to the wrong KiCad endpoint.
- Open the PCB Editor and retry.
- If your KiCad installation requires explicit endpoint variables, add `KICAD_API_SOCKET` and `KICAD_API_TOKEN` into `.vscode/mcp.json`.

### Schematic tools fail with a capability error

- The connected KiCad build does not implement the schematic IPC handlers. Upstream KiCad 10.0.x answers only `GetOpenDocuments` on the schematic API handler, so every other schematic call fails there.
- Start a KiCad 11 (master/nightly) build instead, open the Schematic Editor, and retry.
- See `Schematic Showcase On KiCad 11` above for the build and run steps.

### Design rule tools fail with a capability error

- `kicad_get_design_rules`, `kicad_set_design_rules`, `kicad_get_custom_design_rules`, `kicad_set_custom_design_rules`, `kicad_get_paths`, and `kicad_create_document` are KiCad 11 features. On a stable 10.x endpoint they answer with a capability error, which is expected; continue with the 10.x-compatible phases of a run.

### An export tool times out or reports a busy endpoint

- Zone refills, Gerber, and 3D exports can take longer than the default 60 s IPC timeout. Raise `KIPILOT_KICAD_TIMEOUT_MS` in `.vscode/mcp.json` (for example to `180000`) and retry.
- Make sure the target directory exists and is writable; directory-output jobs write one file per layer into it.

## Suggested First Test Prompt

```text
Use the KiCad MCP tools to verify the connection, report the KiCad version, then summarize the open board. If a write would be needed, stay in dry-run mode and say so explicitly.
```

## Suggested Flip Test Prompt

```text
Use the KiCad MCP tools to find the footprint whose value is LOGO. Explain whether it is currently on F.Cu or B.Cu, then flip it to the opposite copper side. After the tool call, verify the resulting footprint layer and confirm that the footprint-internal artwork moved to the mirrored side-specific silkscreen layer. If live writes are disabled, run the same test as a dry run and call that out explicitly.
```

## Suggested Schematic Test Prompt

```text
Use the KiCad MCP tools to verify the connection, report the KiCad version, then summarize the open schematic: hierarchy, title block, page settings, symbol count, and netlist size. Stay read-only, and call out explicitly when a step would normally be a write.
```

## Suggested Board Export Test Prompt

```text
Use the KiCad MCP tools to inspect the open board, report its layer stackup and board outline, then prepare a manufacturing pack into agent-test/out/board-demo: Gerber files, Excellon drill files, a pick-and-place position file, and a PDF plot. Quote every returned output path and say clearly that exporting does not modify the board.
```

## Suggested Design Rule Test Prompt

```text
Use the KiCad MCP tools to read the board design rules and the custom rule set. Summarize the minimum clearance, track width, via size, and any custom rules. Then preview a single design rule change with dry_run=true and explain what a live write would change, without applying it.
```