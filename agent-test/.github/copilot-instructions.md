# Agent-Test Workspace Guidelines

## Purpose

This workspace is a dedicated test harness for using the sibling `kipilot-mcp` server from VS Code through MCP.

## Workflow Expectations

- Use the configured `kipilot-mcp` MCP server for KiCad tasks.
- Before any board-specific reasoning, verify that the `kipilot-mcp` MCP tools are actually available in the session. If the tool namespace is missing, treat that as an MCP server startup/configuration problem, not as a signal to search the repository for board state.
- Verify connectivity with `ping_kicad` or `get_kicad_version` before board-specific actions when session state is unknown.
- Prefer board inspection first, then `dry_run=true`, then live mutations only if the user explicitly asks for a real write.
- Prefer exact IDs returned by read tools for follow-up updates or deletions.
- Prefer narrow MCP queries and smaller limits over broad fetches that force follow-up reads of generated chat resource files.
- For free-form board text edits, prefer `kicad_get_board_text` before title block, project-variable, or repository-file reasoning.

## Scope Limits

- Treat this workspace as KiCad 10 PCB-first.
- Do not assume schematic automation, plotting, export automation, or headless KiCad control are available.
- If the requested action is outside the current MCP surface, say that clearly and offer a PCB-scoped alternative.

## Safety

- Treat `kicad_revert_board` and `kicad_delete_items` as destructive operations.
- Do not claim that a board change was applied unless the MCP tool returned `ok: true`.
- If mutations are disabled, use dry-run previews and explain that live writes are currently blocked by configuration.
- Do not change `.vscode/mcp.json` or other workspace configuration just to enable live writes unless the user explicitly asks for that workspace change.
- When inferring function blocks from footprints, nets, or zones, clearly mark them as inference rather than direct fact.

## Debugging

- If the MCP server is unavailable, help diagnose the workspace setup instead of guessing.
- If `ping_kicad` or `get_kicad_version` cannot even be executed because the MCP server or tool namespace is unavailable, stop board analysis immediately and report that the MCP server is not running or not connected in the host session.
- Check `.vscode/mcp.json`, KiCad runtime state, and the workspace log path before proposing broader changes.
- Do not inspect `.kicad_pcb` files or other workspace artifacts to answer live-board questions when the MCP server is unavailable.
- Do not inspect VS Code chat-session artifacts such as generated `content.json` files when a narrower MCP query can provide the same answer.