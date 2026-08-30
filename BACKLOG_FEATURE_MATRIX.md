# KiPilot Backlog Feature Matrix

Date: 2026-05-21

This document summarizes the discussed backlog from the currently available repository evidence.

Note: the local session store is empty in this environment, so the matrix below is reconstructed from repository documents and source code rather than from recoverable prior chat transcripts.

## Source Basis

- `kipilot-mcp/.github/kicad-api-capabilities.md`
- `kipilot-mcp/.github/product-definition.md`
- `kicad-master/IPC_API_SCH_INTEGRATION_ANALYSIS.md`
- `kipilot-mcp/src/kipilot_mcp/server.py`
- `kicad-python-main/kipy/board.py`
- `kicad-python-main/kipy/project.py`
- `kicad-python-main/kipy/schematic.py`
- `kicad-python-main/kipy/schematic_types.py`
- `kicad-master/api/proto/common/types/base_types.proto`

## Classification Rules

- `MCP only`: the required KiCad IPC capability and Python wrapper surface already exist; only KiPilot MCP needs new tools and workflow design.
- `Wrapper + MCP`: the backend capability exists, but `kicad-python-main` still needs public wrapper methods before KiPilot can expose the tool.
- `Backend + Wrapper + MCP`: the required KiCad IPC contract is still missing or incomplete in `kicad-master`, so the work must start in C++, then flow through the Python wrapper, then into KiPilot MCP.

## Implementation Progress

- 2026-05-19: implemented `kicad_get_dimensions`, `kicad_get_groups`, `kicad_get_reference_images`, and `kicad_get_barcodes` in `kipilot-mcp`.
- 2026-05-19: implemented `kicad_set_project_text_variables` with dry-run-safe project mutation plumbing.
- 2026-05-19: implemented PCB selection and editor-state tools: `kicad_get_selection`, `kicad_add_to_selection`, `kicad_remove_from_selection`, `kicad_clear_selection`, `kicad_get_editor_appearance_settings`, `kicad_set_editor_appearance_settings`, and `kicad_get_graphics_defaults`.
- 2026-05-19: implemented low-level PCB inspection helpers: `kicad_get_items`, `kicad_get_items_by_id`, `kicad_hit_test`, `kicad_get_text_extents`, and `kicad_get_text_as_shapes`.
- 2026-05-19: implemented `kicad_save_board_as`, `kicad_check_padstack_presence_on_layers`, and `kicad_get_pad_shapes_as_polygons`.
- 2026-05-19: implemented schematic endpoint-aware MCP connection fallbacks so `ping_kicad`, `get_kicad_version`, and `kicad_list_open_documents` work correctly against schematic-only IPC endpoints that do not expose common `Ping` or `GetVersion` requests.
- 2026-05-19: implemented the initial schematic tool surface: `kicad_sch_get_hierarchy`, `kicad_sch_get_netlist`, `kicad_sch_get_page_settings`, `kicad_sch_set_page_settings`, `kicad_sch_get_title_block`, and `kicad_sch_set_title_block`.
- 2026-05-19: live-validated the schematic MCP surface against a locally built `kicad-master` `eeschema` snapshot. Confirmed live success for `ping_kicad`, `get_kicad_version`, `kicad_list_open_documents`, `kicad_sch_get_hierarchy`, `kicad_sch_get_netlist`, `kicad_sch_get_page_settings`, and `kicad_sch_get_title_block`; confirmed dry-run and real setter execution for `kicad_sch_set_page_settings` and `kicad_sch_set_title_block`, with KiCad normalizing user page size on page-settings write.
- 2026-05-20: implemented the first schematic wrapper-backed export block end to end: `kicad_sch_export_svg`, `kicad_sch_export_dxf`, `kicad_sch_export_pdf`, and `kicad_sch_export_ps` are now exposed in `kipilot-mcp` on top of the new `kicad-python-main` schematic plot wrapper methods.
- 2026-05-20: implemented `kicad_sch_export_netlist` and `kicad_sch_export_bom` on top of the new schematic job wrapper methods, then live-validated both against a locally built `eeschema` snapshot.
- 2026-05-20: implemented `kicad_sch_hit_test` on top of the wrapper's schematic `HitTest` support and exposed it in `kipilot-mcp`.
- 2026-05-20: live-validated schematic export over real stdio MCP against a locally built `eeschema` session. Confirmed that SVG, DXF, and PS are directory-output jobs, while PDF is a file-output job. Hardened the MCP contract accordingly with explicit `output_dir` and `output_file` parameters.

## Status Snapshot

- Phases 1 (`MCP only`) and 2 (`Wrapper + MCP`) are locally complete in the current workspace state.
- The remaining backlog is concentrated in phase 3 and starts with `kicad-master` schematic backend parity work before reliable public MCP exposure is practical.
- Two phase-3 candidates already have provisional local wrapper methods in `kicad-python-main` (`save` / `save_as` / `revert` and `get_as_string()` / `get_selection_as_string()`), but the backend analysis still treats them as parity gaps because the schematic side lacks PCB-level lifecycle coverage, selection parity, and QA maturity.

## 1. MCP Only

| Feature / epic | Candidate MCP tools | kicad-master | kicad-python-main | kipilot-mcp | Notes |
| --- | --- | --- | --- | --- | --- |
| Pad geometry helpers | `kicad_check_padstack_presence_on_layers`, `kicad_get_pad_shapes_as_polygons` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Graphics and annotation inspection closure | `kicad_get_dimensions`, `kicad_get_groups`, `kicad_get_reference_images`, `kicad_get_barcodes` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Project text-variable mutation | `kicad_set_project_text_variables` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Board selection and editor-state tools | `kicad_get_selection`, `kicad_add_to_selection`, `kicad_remove_from_selection`, `kicad_clear_selection`, `kicad_get_editor_appearance_settings`, `kicad_set_editor_appearance_settings`, `kicad_get_graphics_defaults` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Low-level inspection helpers | `kicad_get_items`, `kicad_get_items_by_id`, `kicad_hit_test`, `kicad_get_text_extents`, `kicad_get_text_as_shapes` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Save-as convenience for PCB | `kicad_save_board_as` | No | No | Yes | Implemented in the current branch on 2026-05-19. |
| Initial schematic inspection and metadata surface | `kicad_sch_get_hierarchy`, `kicad_sch_get_netlist`, `kicad_sch_get_page_settings`, `kicad_sch_set_page_settings`, `kicad_sch_get_title_block`, `kicad_sch_set_title_block` | No | No | Yes | Implemented in the current branch and live-validated against a locally built `kicad-master` `eeschema` snapshot on 2026-05-19. This is still not a blanket KiCad 10 runtime guarantee: the installed official 10.0.1 build did not expose equivalent reliable external schematic IPC in this environment, so treat the row as source/build-gated rather than generally released-baseline-ready. |

## 2. Wrapper + MCP

| Feature / epic | Candidate MCP tools | kicad-master | kicad-python-main | kipilot-mcp | Notes |
| --- | --- | --- | --- | --- | --- |
| Schematic plot export job surface | `kicad_sch_export_svg`, `kicad_sch_export_dxf`, `kicad_sch_export_pdf`, `kicad_sch_export_ps` | No | Yes | Yes | Implemented in `kicad-python-main` block 1 and now exposed in `kipilot-mcp`. Live stdio validation confirmed the backend contract: SVG, DXF, and PS write one file per sheet into an output directory, while PDF writes one output file. The MCP layer now hardens that contract with explicit `output_dir` and `output_file` parameters. |
| Schematic netlist/BOM export jobs | `kicad_sch_export_netlist`, `kicad_sch_export_bom` | No | Yes | Yes | Implemented in `kicad-python-main` block 2 and now exposed in `kipilot-mcp`, with live stdio validation against a locally built `eeschema` snapshot. |
| Schematic hit-testing | `kicad_sch_hit_test` | No | Yes | Yes | Implemented in `kicad-python-main` block 3 and now exposed in `kipilot-mcp`. The wrapper uses the common editor `HitTest` command against schematic documents, and the MCP layer resolves one schematic item ID plus a schematic-space point/tolerance into a boolean hit result. |

## 3. Backend + Wrapper + MCP

| Feature / epic | Candidate MCP tools | kicad-master | kicad-python-main | kipilot-mcp | Notes |
| --- | --- | --- | --- | --- | --- |
| Schematic document lifecycle parity | `kicad_sch_save`, `kicad_sch_save_as`, `kicad_sch_revert` | Yes | Yes | Yes | Local `kicad-python-main` already contains optimistic `save`, `save_as`, and `revert` wrapper methods, but `kicad-master` still treats schematic document lifecycle as a parity gap because SCH lacks the PCB-side lifecycle/context coverage and validation. |
| Schematic selection parity | `kicad_sch_get_selection`, `kicad_sch_add_to_selection`, `kicad_sch_remove_from_selection`, `kicad_sch_clear_selection` | Yes | Yes | Yes | Eeschema has internal selection infrastructure, but no complete stable IPC contract or public wrapper surface is exposed yet. |
| Schematic convenience serialization | `kicad_sch_get_as_string`, `kicad_sch_get_selection_as_string` | Yes | Yes | Yes | Local `kicad-python-main` already contains convenience methods for both calls, but the backend analysis still marks schematic string serialization as incomplete and not yet ready for MCP exposure or QA closure. |
| Schematic write-safety hardening | No direct user-facing tool; platform work | Yes | Yes | Yes | Busy-state gating, headless behavior, and sheet-aware semantics are prerequisite hardening for reliable schematic mutation tools. |
| Full component library access for schematic placement | `kicad_list_symbol_libraries`, `kicad_list_symbols_in_library`, `kicad_get_symbol_definition`, `kicad_list_footprint_libraries`, `kicad_list_footprints_in_library`, `kicad_get_footprint_definition` | Yes | Yes | Yes | This is a real backend gap. The IPC data model already has `DOCTYPE_SYMBOL`, `DOCTYPE_FOOTPRINT`, `LibraryIdentifier`, and `DocumentSpecifier.lib_id`, but there are no concrete IPC commands today for library enumeration, browsing, or loading. |

## Library-Access Epic Details

The library-access item is different from the other backlog rows because it is not just an unexposed wrapper surface.

What already exists:

- The IPC type system already models library-oriented identities.
- `DocumentType` already includes `DOCTYPE_SYMBOL` and `DOCTYPE_FOOTPRINT`.
- `DocumentSpecifier` can already carry a `lib_id`.
- The Python type model already has `LibraryIdentifier`, `SchematicSymbol`, `Footprint`, and `SchematicSymbolInstance.definition`.

What is missing today:

- No KiCad IPC command for listing symbol libraries.
- No KiCad IPC command for listing symbols within a library.
- No KiCad IPC command for loading one symbol definition by library ID.
- No KiCad IPC command for listing footprint libraries.
- No KiCad IPC command for listing footprints within a library.
- No KiCad IPC command for loading one footprint definition by library ID.
- No public Python wrapper layer for those operations.
- No MCP tools on top of those missing operations.

Important distinction:

- Instance-level access already exists: KiCad can return symbols already placed on a schematic and footprints already placed on a board.
- Independent library-definition access does not exist yet as a usable IPC workflow.

That means the library epic is the missing foundation for future schematic placement helpers such as:

- `kicad_sch_place_symbol_from_library`
- `kicad_sch_place_symbols_from_library`
- library-aware symbol search and selection workflows

The likely implementation order is:

1. Add library enumeration and entry-loading IPC commands in `kicad-master`.
2. Add public wrapper methods in `kicad-python-main`.
3. Expose MCP lookup tools in `kipilot-mcp`.
4. Build higher-level schematic placement tools on top of those lookups and the existing schematic item creation path.

## Current Non-Goals And Intentional Omissions

These should stay out of the backlog unless the product direction changes:

- standalone commit primitives as user-facing MCP tools
- unrestricted generic raw item create/update tools
- generic `run_action()`-style GUI dispatch as a public agent API
- `interactive_move()` as an autonomous MCP workflow

## Version-Gated Items

These are separate from the current KiCad 10 backlog and should not be mixed into the near-term matrix:

- board export and plotting tools tied to KiCad 11+ IPC guarantees
- headless MCP workflows tied to KiCad 11+
- any schematic capability that depends on a future KiCad baseline change rather than the current KiCad 10 target
- schematic rows classified as `MCP only` because the source trees already contain enough wrapper/client code, but where the target KiCad runtime baseline still does not provide reliable external schematic IPC