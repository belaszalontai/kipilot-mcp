# KiCad API Capability Map for KiPilot MCP

## Purpose

This document maps the official KiCad IPC API and `kicad-python` surface to the
realistic MCP tool surface for this repository.

The goal is to separate:

- what KiCad 10 already supports for a GUI-driven PCB workflow,
- what is technically possible but should be exposed carefully,
- what is only available in KiCad 11+, and
- what is not documented as a stable high-level capability.

This document is intentionally broader than the currently shipped MCP tool set.
A capability listed here means "the KiCad binding exposes enough surface that KiPilot can plausibly wrap it"; it does not mean "the repository already implements this as a tool today".

When deciding whether coverage is complete, use two separate questions:

- Is the capability available in the KiCad 10 + `kicad-python` baseline?
- Is that capability already exposed by the current KiPilot MCP server?

## Version and Scope Baseline

For the current project target, assume:

- Target runtime: KiCad 10.x
- Binding: official `kicad-python`
- Connection mode: GUI IPC to a running KiCad instance
- Primary editor scope: PCB Editor

Important version gates from the official KiCad IPC documentation:

- KiCad 9 and 10 support GUI IPC only.
- Headless IPC through `kicad-cli` was added in KiCad 11.
- Plotting and export support through the IPC API was added in KiCad 11.
- KiCad 9.0 initially focused on PCB editor workflows.
- Schematic API coverage is future-oriented from the KiCad 9/10 perspective; `get_schematic()` appears in the generated Python docs for KiCad 11.

## Capability Matrix for a KiCad 10 MCP Server

| Area | KiCad 10 status | What this means for MCP tools |
| --- | --- | --- |
| Connection/session | Supported | We can verify connectivity, versions, socket/token usage, and endpoint health. |
| Open document discovery | Supported | We can inspect which PCB/project documents are open and which document the server is talking to. |
| Project metadata | Supported | We can read project name/path, net classes, text variables, and expand project variables. |
| Board metadata | Supported | We can read board name, document info, active layer, visible/enabled layers, origins, title block, stackup, and editor appearance settings. |
| Footprints | Supported | We can list footprints, fields, positions, orientation, layers, lock state, attributes, 3D model references, and footprint-level overrides. |
| Pads and pad geometry | Supported | We can inspect pads and padstack layer membership today; specialized drill, copper-layer-presence, and polygonized pad-shape helpers remain future wrappers. |
| Nets and connectivity | Supported | We can read nets, net classes, items by net, items by net class, and copper-connected items. |
| Tracks and vias | Supported | We can list and modify existing tracks and vias, and create/delete board items through the generic item APIs. |
| Zones | Supported | We can inspect zones, outlines, filled polygons, priorities, settings, and trigger zone refill. |
| Graphics and annotations | Supported | We can inspect shapes, text, text boxes, dimensions, groups, reference images, and barcodes. |
| Selection/editor state | Supported | We can read and manipulate selection, active layer, visible layers, and some editor appearance settings. |
| Transactions and undo grouping | Supported | We can batch board changes into one undoable commit using `begin_commit()` and `push_commit()`. |
| Persistence | Supported | We can save, save-as, and revert the board. |
| Interactive operations | Partially supported | `interactive_move()` exists, but it hands control to the GUI and temporarily blocks further API work. This is awkward for autonomous MCP workflows. |
| Plot/export jobs | Not for KiCad 10 target | The add-on developer docs say IPC plotting/export support was added in KiCad 11. Do not promise these tools for the KiCad 10 target even if the generated Python docs already include the methods. |
| Headless workflows | Not for KiCad 10 target | Headless API server mode is KiCad 11+. |
| Schematic editor workflows | Not for KiCad 10 target | Treat schematic tooling as future work. |

## Current Implementation Reality

KiPilot currently exposes a substantial KiCad 10 PCB-first MCP surface, but it is not yet exhaustive relative to the full public `kipy` API.

Meaningful areas still not fully wrapped as MCP tools include:

- pad geometry helpers beyond basic pad listing and layer membership
- dimensions, groups, reference images, and barcodes
- selection and editor-state manipulation beyond visible/enabled layers, active layer, and board origins
- project text-variable mutation helpers
- KiCad-level text geometry helpers such as text extents and text-as-shapes
- `save_as` and other convenience operations that need stronger workflow design

Some public binding methods are also intentionally treated as internal plumbing rather than user-facing MCP tools, such as commit primitives, low-level getters used only for serialization, or GUI-interactive calls that are awkward for autonomous workflows.

## Gap-Closure Audit Method

This document now doubles as the gap-closure audit source for the repository.

Audit inputs:

- current MCP server inventory: 41 registered tools in `src/kipilot_mcp/server.py`
- public callable surface of the installed `kipy.KiCad`, `kipy.board.Board`, and `kipy.project.Project` classes
- repository product-scope rules already defined in this file

Status rules used in the audit:

- `Implemented`: the capability is available today through the current MCP surface, even if some low-level binding methods remain internal implementation details
- `Partially implemented`: part of the capability is available today, but dedicated helpers are still needed for the full user-facing workflow
- `Missing`: the capability exists in the current KiCad 10 + `kicad-python` baseline and fits the repository scope, but no dedicated MCP tool exposes it yet
- `Intentionally omitted`: the capability or method exists, but the server deliberately does not expose it because it is internal plumbing, too generic, unsafe, poor for autonomous workflows, or outside the product contract

Important interpretation rule:

- This is a capability audit, not a raw method-count audit. A public binding method can remain unexposed as a standalone MCP tool while still contributing to an `Implemented` capability through a higher-level wrapper. Examples include internal use of `create_items()`, `update_items()`, `remove_items()`, `get_project()`, `get_layer_name()`, and `get_item_bounding_box()`.
- Therefore, a direct method diff against the `kipy` classes is useful as a discovery aid, but it overstates real gaps unless the results are normalized back to user-facing capabilities.

## Coverage Status Table

| Capability slice | Representative binding surface | Status | Current MCP exposure or decision |
| --- | --- | --- | --- |
| Endpoint health and version info | `KiCad.ping`, `get_version`, `get_api_version`, `check_version` | Implemented | `ping_kicad`, `get_kicad_version` |
| Open document discovery | `KiCad.get_open_documents` | Implemented | `kicad_list_open_documents` |
| Project text-variable read | `Project.get_text_variables` | Implemented | `kicad_get_project_text_variables` |
| Project text-variable expansion | `Project.expand_text_variables` | Implemented | `kicad_expand_project_text_variables` |
| Project text-variable mutation | `Project.set_text_variables` | Missing | Baseline-compatible, but not yet surfaced |
| Project net class inspection | `Project.get_net_classes` | Implemented | `kicad_get_project_net_classes` |
| Board summary, stackup, outline, origins, and title block | board metadata getters | Implemented | `kicad_get_board_summary`, `kicad_get_stackup`, `kicad_get_board_outline`, `kicad_get_board_origins`, `kicad_get_title_block` |
| Active layer read | `Board.get_active_layer` | Implemented | Returned by `kicad_get_board_summary` |
| Active layer write | `Board.set_active_layer` | Implemented | `kicad_set_active_layer` |
| Visible layer read/write | `Board.get_visible_layers`, `set_visible_layers` | Implemented | Read via `kicad_get_stackup`, write via `kicad_set_visible_layers` |
| Enabled layer read | `Board.get_enabled_layers` | Implemented | Returned by `kicad_get_stackup` |
| Enabled layer write | `Board.set_enabled_layers` | Implemented | `kicad_set_enabled_layers` exposes a constrained non-copper-layer wrapper with a force guard for live changes |
| Footprint lookup and placement | `Board.get_footprints`, `update_items` | Implemented | `kicad_get_footprints`, `kicad_find_footprints`, `kicad_move_footprint`, `kicad_rotate_footprint` |
| Pads and pad geometry | `Board.get_pads`, `check_padstack_presence_on_layers`, `get_pad_shapes_as_polygons` | Partially implemented | `kicad_get_pads` exposes pad lookup and padstack layer membership; dedicated drill, layer-presence check, and polygonized shape helpers are still missing |
| Nets and items by net | `Board.get_nets`, `get_items_by_net` | Implemented | `kicad_get_nets`, `kicad_get_items_by_net` |
| Net-class and connectivity queries | `Board.get_items_by_netclass`, `get_netclass_for_nets`, `get_connected_items` | Implemented | `kicad_get_items_by_netclass`, `kicad_get_netclass_for_nets`, `kicad_get_connected_items` |
| Tracks, vias, and zones inspection/edit/delete/refill | `Board.get_tracks`, `get_vias`, `get_zones`, `create_items`, `update_items`, `remove_items`, `refill_zones` | Implemented | `kicad_get_tracks`, `kicad_get_vias`, `kicad_get_zones`, `kicad_create_track_segments`, `kicad_create_via`, `kicad_update_track_geometry`, `kicad_update_zone_outline`, `kicad_update_items`, `kicad_delete_items`, `kicad_refill_zones` |
| Standalone board text and text boxes | `Board.get_text`, `update_items` | Implemented | `kicad_get_board_text`, `kicad_update_board_text` |
| Generic shapes and graphics inspection | `Board.get_shapes` | Implemented | `kicad_get_graphics` plus the derived `kicad_get_board_outline` helper |
| Dimensions, groups, reference images, and barcodes | `Board.get_dimensions`, `get_groups`, `get_reference_images`, `get_barcodes` | Missing | Not yet surfaced |
| Selection inspection and manipulation | `Board.get_selection`, `add_to_selection`, `clear_selection`, `remove_from_selection` | Missing | Valid KiCad 10 capability, not yet exposed |
| Editor appearance and graphics defaults | `Board.get_editor_appearance_settings`, `set_editor_appearance_settings`, `get_graphics_defaults` | Missing | No MCP tools yet |
| Persistence: save and revert | `Board.save`, `revert` | Implemented | `kicad_save_board`, `kicad_revert_board` |
| Persistence: save as | `Board.save_as` | Missing | Deferred until file-path and overwrite safety policy is defined |
| Generic raw item enumeration by ID/type | `Board.get_items`, `get_items_by_id` | Missing | Current design favors typed lookup tools |
| Fully generic raw item creation and update | `Board.create_items`, `update_items` | Intentionally omitted | Only constrained helpers and whitelist-based updates are exposed |
| Low-level commit primitives | `Board.begin_commit`, `push_commit`, `drop_commit` | Intentionally omitted | Internal write plumbing, not user-facing MCP tools |
| GUI-interactive move | `Board.interactive_move` | Intentionally omitted | Hands control to the GUI and blocks autonomous workflows |
| Hit testing | `Board.hit_test` | Missing | Plausible future inspection tool |
| KiCad text geometry helpers | `KiCad.get_text_as_shapes`, `get_text_extents` | Missing | Useful analysis helpers, not yet surfaced |
| Generic GUI action dispatch | `KiCad.run_action` | Intentionally omitted | Too generic and unsafe for autonomous use |
| Host and installation path introspection | `KiCad.get_kicad_binary_path`, `get_plugin_settings_path` | Intentionally omitted | Low value for the core board-editing MCP workflow |
| Alternate client construction and debug/string helpers | `KiCad.from_client`, `Board.get_as_string` | Intentionally omitted | Internal or debug-oriented API surface, not product-facing tools |

## Audit-Derived Next Closure Candidates

Highest-value `Missing` areas for the next closure passes:

- pad geometry helpers beyond basic pad listing and layer membership
- dimensions, groups, reference images, and barcodes
- selection and editor-state tools
- project text-variable mutation helpers
- editor appearance and graphics defaults
- `save_as`, hit testing, and KiCad text geometry helpers

Areas currently classified as `Intentionally omitted` should stay omitted unless the product direction changes:

- low-level commit primitives as standalone tools
- fully generic unrestricted board item create/update wrappers
- `interactive_move()` as an agent tool
- `run_action()` style generic GUI dispatch
- host-path and debug-oriented helper methods

## What the API Clearly Enables

### 1. Read-only board intelligence

These are strong MCP candidates because they are high-value and low-risk:

- board summary and document identity
- footprints with filtering by reference, value, layer, sheet path, or area
- nets, net classes, and connectivity lookups
- pads, vias, tracks, and zones with geometry in millimeters
- title block and project text variables
- stackup, copper layers, and layer names
- Edge.Cuts-derived board outline and board bounding boxes
- connected-item queries for tracing copper relationships

### 2. Safe board modifications

These are realistic once the read-only tools are solid:

- move or rotate footprint instances
- update text, field, and annotation content
- set board origin or active layer
- update title block fields
- change selection or visible layers for guided user workflows
- batch multiple updates in a single commit/undo step

### 3. Advanced board editing

These are supported by the low-level item APIs, but they are more dangerous and
need stronger validation in the MCP layer:

- create board items with `create_items()`
- update arbitrary board items with `update_items()`
- delete items with `remove_items()` or `remove_items_by_id()`
- edit vias, tracks, zones, graphics, or padstack-related properties
- refill zones after geometry changes
- save or save-as after mutation

## What We Should Not Overpromise

### High-level routing

The documented API exposes board items such as `Track`, `ArcTrack`, and `Via`,
plus generic item creation and update methods.

That is enough for low-level geometry creation and editing, but it is not the
same as a documented high-level autorouter or shove router API.

For that reason, tool names like `kicad_route_track` are misleading unless the
tool is explicitly implemented as a low-level segment creation helper. A more
accurate naming direction would be:

- `kicad_create_track_segments`
- `kicad_create_via`
- `kicad_move_footprint`

### Board outline

There is no dedicated `get_board_outline()` primitive in the Python API docs.
This capability should be implemented as a derived analysis over board shapes,
typically from the Edge.Cuts layer.

### Export and fabrication outputs

The generated `kicad-python` docs list export methods on `Board`, but the KiCad
IPC add-on documentation explicitly states that IPC plotting/export support was
added in KiCad 11.

For a KiCad 10-targeted MCP server, export tools should stay out of the committed
scope until we intentionally move the project baseline to KiCad 11.

## Recommended MCP Tool Roadmap

### Phase A: Stable read-only tools

- `ping_kicad`
- `get_kicad_version`
- `kicad_list_open_documents`
- `kicad_get_board_summary`
- `kicad_get_board_outline`
- `kicad_get_stackup`
- `kicad_get_footprints`
- `kicad_find_footprints`
- `kicad_get_nets`
- `kicad_get_items_by_net`
- `kicad_get_tracks`
- `kicad_get_vias`
- `kicad_get_zones`
- `kicad_get_board_text`
- `kicad_get_project_text_variables`

### Phase B: Safe mutation tools

- `kicad_move_footprint`
- `kicad_rotate_footprint`
- `kicad_set_board_origin`
- `kicad_set_title_block`
- `kicad_set_visible_layers`
- `kicad_update_board_text`
- `kicad_revert_board`

Do not add a standalone `kicad_commit_changes` tool under the current product model.
The existing mutation tools already group writes into commits internally when live writes are enabled.

### Phase C: Advanced editing tools

- `kicad_create_track_segments`
- `kicad_create_via`
- `kicad_update_track_geometry`
- `kicad_update_zone_outline`
- `kicad_delete_items`
- `kicad_refill_zones`
- `kicad_save_board`

### Phase D: Future or version-gated tools

- schematic tools: only after the targeted KiCad version exposes stable schematic coverage
- export/plot tools: only when the project baseline is moved to KiCad 11+
- headless automation: only when the project baseline is moved to KiCad 11+

## Product Decision for This Repository

For KiPilot MCP today, the correct scope is:

- GUI-connected KiCad 10 workflow
- PCB editor first
- read-heavy tools first
- carefully validated board mutations second
- no promise of schematic or export automation in the KiCad 10 baseline

This keeps the MCP server aligned with what the official KiCad documentation
actually guarantees.