# Agent-Test Workspace Guidelines

## Purpose

This workspace is a dedicated test harness for using the sibling `kipilot-mcp` server from VS Code through MCP.

## Workflow Expectations

- Use the configured `kipilot-mcp` MCP server for every substantive KiCad answer in this workspace.
- Treat this workspace as current-board-first: interpret user requests as referring to the live board unless the user explicitly asks to debug the MCP setup itself.
- For KiCad inspection, explanation, and mutation tasks in this workspace, use only `kipilot-mcp` MCP tools as the source of truth.
- Before any board-specific reasoning, verify that the `kipilot-mcp` MCP tools are actually available in the session. If the tool namespace is missing, treat that as an MCP server startup/configuration problem, not as a signal to search the repository for board state.
- Verify connectivity with `ping_kicad` or `get_kicad_version` before substantive board actions when session state is unknown.
- Establish the current board context with a minimal MCP read before giving higher-level advice when that context has not already been confirmed in the conversation.
- If the prompt sounds generic, reference-oriented, or library-like, first inspect the current board for relevant live objects and answer from that board context instead of giving a standalone general answer.
- If the current board does not provide relevant evidence for the generic request, say that plainly and do not replace the missing live context with repository mining or free-floating domain knowledge.
- A response-language request changes only the language of the answer, not the MCP-first and current-board-first workflow.
- Prefer board inspection first, then `dry_run=true`, then live mutations only if the user explicitly asks for a real write.
- Prefer exact IDs returned by read tools for follow-up updates or deletions.
- Prefer narrow MCP queries and smaller limits over broad fetches.
- If an MCP result is too large, rerun the MCP query with tighter filters, smaller limits, or a narrower target instead of reading copied MCP payloads from chat-session resource files.
- When a power or ground net is large, prefer MCP area filters around the local design region before retrying the same global connectivity query with smaller limits.
- Do not probe guessed rail names one by one if the exact live net name can be resolved from MCP net results or from nearby items on the board.
- For free-form board text edits, prefer `kicad_get_board_text` before title block, project-variable, or repository-file reasoning.
- If a specialized KiPilot write tool contradicts earlier read-tool results about the same item, do one narrow disambiguation step instead of repeating the same failing write.
- If an equivalent narrow MCP fallback exists, prefer that fallback over declaring the capability missing.
- If the user mentions `F.SilkS`, `B.SilkS`, silkscreen, logo artwork, or printed board text, distinguish that from footprint placement side before choosing a mutation path.
- Treat `kicad_find_footprints(text_query=...)` as a lookup over footprint `reference`, `value`, and `id`, not as proof that the matching visible object is standalone silkscreen content.
- If the user explicitly says `footprint with value ...`, prioritize footprint lookup over standalone board text or graphics queries.
- Do not send guessed raw numeric layer IDs in MCP calls unless those IDs were confirmed from the live board.
- Do not generate generic electronics reference tables, package-size comparisons, or footprint matching advice without first anchoring them to the current live board through MCP.

## Scope Limits

- Treat this workspace as KiCad 10 PCB-first.
- Do not assume schematic automation, plotting, export automation, or headless KiCad control are available.
- If the requested action is outside the current MCP surface, say that clearly and offer a PCB-scoped alternative.
- Do not use repository reads, workspace file inspection, terminal parsing, or chat-session artifact inspection as a substitute for live board-state MCP queries.
- If the requested action is outside the current MCP surface, do not compensate by mining chat-session files or terminal output; report the limitation plainly.
- Only inspect or patch the sibling `kipilot-mcp` source when the user explicitly asks to debug or modify the MCP server itself.
- For local connector or pad repurpose workflows, keep the analysis local: resolve the footprint, enumerate its pads, use area-bounded nearby copper queries, and only then widen if the narrow MCP result is insufficient.
- Footprint read results now include a compact `child_graphics` layer summary for footprint-internal non-pad artwork/text, so use that summary or the flip result to verify mirrored silkscreen movement after a footprint side flip.

## Safety

- Treat `kicad_revert_board` and `kicad_delete_items` as destructive operations.
- Do not claim that a board change was applied unless the MCP tool returned `ok: true`.
- If mutations are disabled, use dry-run previews and explain that live writes are currently blocked by configuration.
- Do not change `.vscode/mcp.json` or other workspace configuration just to enable live writes unless the user explicitly asks for that workspace change.
- When inferring function blocks from footprints, nets, or zones, clearly mark them as inference rather than direct fact.
- Do not claim that a local KiPilot server fix changed the board; after patching the local server, require a server restart and a fresh MCP write result before reporting success.

## Debugging

- If the MCP server is unavailable, help diagnose the workspace setup instead of guessing.
- If `ping_kicad` or `get_kicad_version` cannot even be executed because the MCP server or tool namespace is unavailable, stop board analysis immediately and report that the MCP server is not running or not connected in the host session.
- Check `.vscode/mcp.json`, KiCad runtime state, and the workspace log path before proposing broader changes.
- Do not inspect `.kicad_pcb` files or other workspace artifacts to answer live-board questions when the MCP server is unavailable.
- Do not inspect VS Code chat-session artifacts such as generated `content.json` files to recover or filter MCP results.
- Do not run terminal commands to parse, grep, or post-process copied MCP result files for live board reasoning.
- If a KiPilot tool failure contradicts confirmed live board data and the server source is present locally, debug the local server code before concluding that the operation is fundamentally unsupported.