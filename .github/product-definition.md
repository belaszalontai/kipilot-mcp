# Product Definition: KiCad MCP Server

## 1. Product Vision
The KiCad MCP (Model Context Protocol) Server acts as an intelligent bridge between GitHub Copilot running in VSCode (or any MCP-compatible client) and the KiCad EDA suite. It allows AI agents to interact with a live, running instance of KiCad via KiCad's IPC API, enabling prompt-driven hardware design and contextual querying of the board state.

## 2. Core Architecture
- **Client:** VSCode + GitHub Copilot (using MCP client capabilities).
- **Middleware:** Python-based MCP Server implementing the official Anthropic MCP SDK.
- **Target:** KiCad 9.0+ running locally with IPC API support. KiCad 9/10 require a running KiCad GUI instance for IPC access.
- **Communication Protocol:** 
  - Client <-> MCP Server: stdio / MCP Protocol
  - MCP Server <-> KiCad: official `kicad-python` (`kipy`) binding over KiCad's platform IPC endpoint (named pipe on Windows, Unix domain socket on macOS/Linux)

## 3. Key Features & Capabilities (MCP Tools)
The server will expose specific tools to the LLM, but the scope must follow the
official KiCad IPC API as it exists in the targeted KiCad version.

### Baseline for this repository
- KiCad 10 target.
- GUI IPC only.
- PCB Editor first.
- Read-heavy tools first, mutation second.
- No committed schematic or export scope in the KiCad 10 baseline.

### Phase 1: Connection and Read-only PCB Context
- `ping_kicad`: Verify that a user-running KiCad GUI instance is reachable through the IPC API.
- `get_kicad_version`: Retrieve KiCad and IPC API version information.
- `kicad_list_open_documents`: Retrieve the open project and board documents visible through the current KiCad endpoint.
- `kicad_get_board_summary`: Retrieve high-level information about the currently open PCB.
- `kicad_get_board_outline`: Derive the board outline from board geometry, typically from Edge.Cuts items.
- `kicad_get_stackup`: Retrieve layer and stackup information.
- `kicad_get_footprints`: Retrieve placed footprint references, values, layers, and positions.
- `kicad_get_nets`: Retrieve board net information.
- `kicad_get_items_by_net`: Retrieve board items associated with a net or netclass.

### Phase 2: Safe PCB Mutation
- `kicad_move_footprint`: Move a specific footprint by reference or UUID.
- `kicad_rotate_footprint`: Rotate a specific footprint.
- `kicad_set_board_origin`: Update the board origin.
- `kicad_set_title_block`: Update title block metadata.
- `kicad_set_visible_layers`: Assist user workflows by controlling visible layers.

### Phase 3: Advanced PCB Editing
- `kicad_create_track_segments`: Create low-level track geometry.
- `kicad_create_via`: Create vias.
- `kicad_update_items`: Apply validated low-level updates to board items.
- `kicad_delete_items`: Remove board items by UUID.
- `kicad_refill_zones`: Refill zones after geometry changes.

### Future: Version-gated Features
- Export and plotting MCP tools should be added only when the project baseline moves to KiCad 11+, because the official add-on documentation states IPC export support was added there.
- Headless MCP workflows should be added only when the project baseline moves to KiCad 11+.
- Schematic MCP tools should be added only when the targeted KiCad version exposes the needed schematic IPC coverage through the official API.

See `.github/kicad-api-capabilities.md` for the detailed capability map and the rationale behind these scope decisions.

## 4. Technical Stack
- **Language:** Python 3.11+
- **Key Libraries:**
  - `mcp`: Official Anthropic Model Context Protocol SDK.
  - `kicad-python`: Official KiCad Python bindings for the IPC API, imported as `kipy`.
  - `asyncio`: For async MCP tool handlers and thread offloading of blocking IPC calls.

## 5. User Workflow
1. Developer opens a firmware/hardware project in VSCode.
2. Developer opens the corresponding board/project in KiCad 9+.
3. Developer asks Copilot: "List the footprints and nets on the currently open PCB."
4. Copilot invokes the KiCad MCP Server tool.
5. The MCP server uses `kicad-python` to call the KiCad IPC API.
6. KiCad returns the requested board context to Copilot.