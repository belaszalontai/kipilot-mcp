---
name: board-release-showcase
description: "Full-spectrum KiPilot MCP board release showcase: inspect the live board, export the manufacturing pack (Gerber, drill, position, SVG, PDF, statistics, ODB++, IPC-2581, IPC-D-356, GenCAD, STEP, render), read design rules, preview a rule change, embed a datasheet, and write a save-as copy."
agent: kicad-agent
tools: [todo, "kipilot-mcp/*"]
---
Run the complete KiPilot MCP board release showcase on the board that is currently open in the KiCad PCB Editor.

This run is being recorded for the public gallery, so narrate in short, confident, camera-friendly lines:
one line before each tool batch (what and why), one line after (the concrete evidence).

## Hard rules

1. Work only through the `kipilot-mcp/*` tool namespace. Never read `.kicad_pcb` files from disk.
2. Every document mutation goes `dry_run=true` first, then live, then a verifying read.
3. Never claim success unless the tool returned `ok: true`.
4. Export tools write files but never modify the document; say that explicitly once, then keep going.
5. If a tool returns a capability error, quote it, mark the phase as unsupported by this KiCad build, and continue with the next phase.
6. Board tools only. Do not call schematic mutation tools.
7. All coordinates are millimeters. Reuse the item IDs that the tools return.
8. Keep the run under 12 tool batches per phase so the recording stays readable.

## Output paths

Use exactly these absolute paths for the export phases:

- Gerber directory: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/gerbers`
- Drill directory: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/drill`
- SVG directory: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/svg`
- PDF file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.pdf`
- Position file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.pos`
- Statistics file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-stats.txt`
- ODB++ directory: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/odb`
- IPC-2581 file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-ipc2581.xml`
- IPC-D-356 file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-ipc-d356.net`
- GenCAD file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.cad`
- STEP file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.step`
- Render file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-render.png`
- Save-as copy: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-copy.kicad_pcb`

## Phase 0 — Connect

- `ping_kicad`, `get_kicad_version`, `kicad_list_open_documents`.
- Say in one line: which KiCad build answered, and that a board document is present.
- `kicad_get_paths` — optional environment context; if the build answers with a capability error, note that it needs KiCad 11 and move on.
- If no board is open, stop and ask the user to open one in the PCB Editor.

## Phase 1 — Baseline snapshot (read-only)

- `kicad_get_board_summary` — counts, copper layer count, active layer.
- `kicad_get_board_outline` and `kicad_get_stackup` — outline bounding box, layer stack, visible and enabled layers.
- `kicad_get_board_plot_settings` — which layers and options the board would plot with today.
- `kicad_get_design_rules` and `kicad_get_custom_design_rules` — read the current rules; if these answer with a capability error, state that design rules need a KiCad 11 build and continue.

Report: board name, footprint/track/via/zone counts, outline size in millimeters, and whether design rules were readable.

## Phase 2 — Manufacturing pack (the centerpiece)

Send these exports one at a time and quote every returned output path verbatim:

- `kicad_export_gerbers(output_dir="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/gerbers", create_gerber_job_file=true)`
- `kicad_export_drill(output_dir="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/drill", drill_format="excellon", report_filename="kipilot-showcase-drill-report.txt")`
- `kicad_export_position(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.pos")`
- `kicad_export_board_svg(output_dir="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/svg", fit_page_to_board=true)`
- `kicad_export_board_pdf(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.pdf")`
- `kicad_export_stats(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-stats.txt")`

After each call, summarize in one line what the job produced (layer count or single file), and remind the viewer once that the board document itself is untouched.

## Phase 3 — Advanced data outputs

- `kicad_export_odb(output_dir="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/odb")`
- `kicad_export_ipc2581(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-ipc2581.xml")`
- `kicad_export_ipc_d356(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-ipc-d356.net")`
- `kicad_export_gencad(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.cad")`

Mention that these are the formats an EMS or assembly partner usually asks for, and that each one is one call away.

## Phase 4 — 3D model and render (slow, do last among the exports)

- `kicad_export_3d(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.step")`
- `kicad_export_render(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-render.png")`

Warn before this phase that 3D export and raytraced render can take a while and may exceed the default IPC timeout.

## Phase 5 — Design rule preview (KiCad 11 only)

Skip this phase entirely if Phase 1 reported a design rule capability error.

- Summarize two or three concrete rule values from `kicad_get_design_rules`, for example minimum clearance, minimum track width, and minimum via size.
- `kicad_set_design_rules(rules={"constraints": {"min_track_width": {"value_nm": ...}}}, dry_run=true)` with a value derived from the current rule, and explain what the live call would change.
- Do **not** apply the change live. State explicitly that this is a preview-only demonstration because design rules are a project-level setting.

## Phase 6 — Embedded datasheet demo (optional, only when asked)

- `kicad_get_embedded_files()` — report whether the board already embeds fonts, models, or datasheets.
- If the user asked for a live demo, `kicad_add_embedded_files(paths=["C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase.pdf"], dry_run=true)` then live, then `kicad_get_embedded_files()` to verify.
- Say clearly that this is a real board mutation (the embedded set grows), that it only lives in memory until the document is saved, and that `kicad_set_embedded_files` would be the destructive replacement path.

## Phase 7 — Persist as a copy

- `kicad_save_board_as(filename="C:/Work/bitbucket/kipilot-mcp/agent-test/out/board-demo/kipilot-showcase-copy.kicad_pcb", include_project=false, dry_run=true)` then live.
- Explain that this writes a copy without opening it, so the user's working file stays untouched.
- Do not call `kicad_save_board` on the original document in this showcase.

## Phase 8 — Wrap up

Close with a compact summary table:

- what was read (board context, rules, embedded files),
- what was exported (one row per format with the returned path),
- what was previewed but intentionally not applied (rule change),
- what was mutated (embedded file, if Phase 6 ran) and where the copy was written,
- what remains optional: `kicad_refill_zones`, `kicad_import_netlist` (forward annotation with `dry_run=true` first), `kicad_set_project_net_classes`, and `kicad_run_action` for a named KiCad action.

## Optional bonus (only when asked)

- `kicad_get_bounding_box(item_ids=[...])` on a few footprint IDs to show per-item and merged boxes.
- `kicad_import_netlist(netlist_path="C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.net", dry_run=true)` to show the forward-annotation preview path without touching the board.
