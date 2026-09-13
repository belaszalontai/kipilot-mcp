---
name: schematic-showcase
description: "Full-spectrum KiPilot MCP schematic showcase: inspect the live sheet, stamp the title block, draw an annotated functional block, highlight it, edit and hit-test items, prove the netlist changed, manage design variants, export the documentation pack, and save."
agent: kicad-agent
tools: [todo, "kipilot-mcp/*"]
---
Run the complete KiPilot MCP schematic showcase on the schematic that is currently open in the KiCad Schematic Editor.

This run is being recorded for the public gallery, so narrate in short, confident, camera-friendly lines:
one line before each tool batch (what and why), one line after (the concrete evidence).

## Hard rules

1. Work only through the `kipilot-mcp/*` tool namespace. Never read `.kicad_sch` files from disk.
2. Every mutation goes `dry_run=true` first, then live, then a verifying read.
3. Never claim success unless the tool returned `ok: true`.
4. If a tool returns a capability error, quote it, mark the phase as unsupported by this KiCad build, and continue with the next phase.
5. Schematic tools only. Do not call PCB mutation tools.
6. All coordinates are millimeters. Reuse the item IDs that the tools return.
7. Keep the run under 12 tool batches per phase so the recording stays readable.

## Output paths

Use exactly these absolute paths for the export phase:

- SVG directory: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/svg`
- PDF file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.pdf`
- Netlist file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.net`
- BOM file: `C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.csv`

## Phase 0 — Connect

- `ping_kicad`, `get_kicad_version`, `kicad_list_open_documents`.
- Say in one line: which KiCad build answered, and that a schematic document is present.
- If no schematic document is open, stop and ask the user to open one in the Schematic Editor.

## Phase 1 — Baseline snapshot (read-only)

- `kicad_sch_is_document_modified` — is there unsaved work?
- `kicad_sch_get_page_settings`, `kicad_sch_get_title_block` — sheet and title block facts.
- `kicad_sch_get_hierarchy` — sheet name and hierarchical children.
- `kicad_sch_get_items(limit=1000)` — count items per kind and compute `min_x`, `max_x`, `min_y`, `max_y` over all coordinates and polyline points.
- `kicad_sch_get_symbols(limit=20)`, `kicad_sch_get_labels(limit=20)` — a short inventory of what the sheet already contains.
- `kicad_sch_get_netlist()` — remember the net count and keep the list of net names.
- `kicad_sch_get_variants` — existing variants and the active one.

Report: dirty state, page size, symbol count, net count, active variant, and the free-area anchor you will use.

Choose the net to join in Phase 3 from this netlist: prefer a named net that is not auto-generated (its name does not start with `Net-(`) and that has at least two nodes. If no such net exists, use the literal name `KIPILOT_DEMO_TP1`.

## Phase 2 — Title block (first visible change)

- `kicad_sch_set_title_block(dry_run=true)` with:
  - `title`: `KiPilot MCP v0.2.0 Schematic Showcase`
  - `revision`: `v0.2.0`
  - `company`: `gwt_team`
  - `comments`: `{1: "Drawn live over the KiCad IPC API by GitHub Copilot"}`
- Repeat live, then `kicad_sch_get_title_block` to verify field by field.

Point out that the sheet's title block area just changed inside KiCad.

## Phase 3 — Draw an annotated functional block (the centerpiece)

Compute the anchor first and round every number to 0.1 mm. Try these candidates in order and stop at the first one whose block area (94 x 60 mm envelope) stays inside 20..185 mm horizontally and 25..145 mm vertically:

1. `BX = max_x + 30`, `BY = clamp(min_y, 25, 140)` — free area to the right of existing content.
2. `BX = 20`, `BY = max_y + 30` — free area below existing content.
3. `BX = 20`, `BY = 25` — last resort; say plainly that the sheet looks full and that the block may overlap existing content.

State the chosen `BX`/`BY` and the reason in one line before drawing.

Build this exact block relative to `BX`, `BY` and send it as one `kicad_sch_create_items` call (`dry_run=true` first, then live):

- `text` `KiPilot MCP v0.2.0 — live schematic block` at `(BX, BY - 8)`
- `wire` closed box: `(BX,BY) (BX+70,BY) (BX+70,BY+40) (BX,BY+40) (BX,BY)`
- `wire` signal line straight through: `(BX-12,BY+10) (BX+82,BY+10)`
- `wire` branch downwards: `(BX+35,BY+10) (BX+35,BY+34)`
- `junction` at `(BX+35, BY+10)`
- `no_connect` at `(BX+35, BY+34)`
- `label` `DEMO_CLK` at `(BX+20, BY+10)` with `spin_style: "up"`
- `global_label` with the net name chosen in Phase 1 at `(BX-12, BY+10)` with `spin_style: "right"`, `shape: "input"`
- `global_label` `KIPILOT_DEMO_OUT` at `(BX+82, BY+10)` with `spin_style: "left"`, `shape: "output"`
- `text` `Agent-drawn functional block` at `(BX+3, BY+36)`
- `text` `Created via kicad_sch_create_items · KiCad IPC API` at `(BX, BY+46)`

After the live call: report the created item count and keep every returned item ID in a list named `created_ids`.

Then verify with `kicad_sch_get_items(kinds=["wire", "junction", "no_connect", "label", "text"], limit=200)` and confirm the new objects are present.

If the live call fails with a capability error, report it and skip the rest of the drawing phases, then continue with Phase 6 onward.

Note: a `hierarchical_label` only makes sense inside a subsheet. Mention that once, and only use it if the open sheet is a child sheet.

## Phase 4 — Highlight what the agent just drew (very visible)

- `kicad_sch_add_to_selection(item_ids=created_ids, dry_run=true)`, then live.
- `kicad_sch_get_selection(limit=200)` — report how many items are now selected.
- `kicad_sch_get_selection_as_string()` — show the first lines of the s-expression of the agent-created selection, then state that this is the same representation a human would get from the editor.
- Leave the selection active until Phase 8 so the recording shows the highlighted block.

## Phase 5 — Edit and precisely hit-test

- `kicad_sch_update_items` on the header `text` item: change its text to `KiPilot MCP v0.2.0 — edited live by the agent`. Dry-run, live, then verify with `kicad_sch_get_items(kinds=["text"], limit=50)`.
- `kicad_sch_hit_test` on the `DEMO_CLK` label item id at its exact anchor `(BX+20, BY+10)` with `tolerance_mm=0.5` — expect a hit.
- `kicad_sch_hit_test` on the same item at `(BX+60, BY+30)` — expect a miss.
- Explain in one line that this is point-precise geometric interrogation of a live editor object.

## Phase 6 — Prove the netlist changed

- `kicad_sch_get_netlist()` again.
- Compare with the Phase 1 snapshot: report the previous net count, the new net count, and whether the chosen net name now carries the newly drawn label.
- If the netlist is unchanged, say so explicitly and explain that the label attaches on the next connectivity rebuild.

## Phase 7 — Design variants

- `kicad_sch_add_variant(name="KIPILOT_DEMO", description="KiPilot showcase variant", dry_run=true)` then live.
- `kicad_sch_copy_variant(old_name="KIPILOT_DEMO", new_name="KIPILOT_DEMO_DNP", new_description="KiPilot showcase variant, DNP build", dry_run=true)` then live.
- `kicad_sch_set_current_variant(name="KIPILOT_DEMO", dry_run=true)` then live, and `kicad_sch_get_current_variant()` to confirm.
- `kicad_sch_get_variants()` — report the full variant list and which one is active.
- Leave `KIPILOT_DEMO` active for the export phase.

## Phase 8 — Documentation pack (export jobs)

- `kicad_sch_clear_selection()` first so the exports are clean.
- `kicad_sch_export_svg(output_dir="C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/svg")`
- `kicad_sch_export_pdf(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.pdf")`
- `kicad_sch_export_netlist(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.net", variant_name="KIPILOT_DEMO")`
- `kicad_sch_export_bom(output_file="C:/Work/bitbucket/kipilot-mcp/agent-test/out/sch-demo/kipilot-showcase.csv", group_symbols=true, variant_name="KIPILOT_DEMO")`
- Report every returned output path verbatim so the viewer can open the SVG and the PDF.

## Phase 9 — Persist and wrap up

- `kicad_sch_save(dry_run=true)` then live.
- `kicad_sch_is_document_modified()` — must now report clean.
- `kicad_sch_set_current_variant()` to restore the default variant, and confirm with `kicad_sch_get_current_variant()`.
- Close with a compact summary table:
  - what was read, what was created (with counts), what was edited, what was exported (with paths), what is persisted, and what remains optional (symbol placement, hierarchical labels on subsheets, review of the exported SVG/PDF).

## Optional bonus (only when asked)

Symbol placement through `kicad_sch_create_items` with `kind: "symbol"`, for example `lib_id: "Device:R"`, `reference: "R900"`, `value: "10k"`. Place it inside a fresh 20 x 20 mm free area, never on existing geometry, and state that the pins are intentionally left unwired because pin-level connection coordinates must be resolved from the symbol definition before wiring.
