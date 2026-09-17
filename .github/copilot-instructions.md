# GitHub Copilot / Agent Instructions: KiCad MCP Server Development

## Role and Context
You are an expert Python developer with deep knowledge of the Model Context Protocol (MCP) and the KiCad EDA IPC API. We are building an MCP server in Python that connects VS Code/Copilot to a running KiCad 10.x instance to enable agentic hardware development.

## Development Rules & Guidelines

1. **Tech Stack & Libraries:**
   - Use Python 3.11+.
   - Use the official Anthropic `mcp` library (`pip install mcp`).
   - Use the official KiCad `kicad-python` package (`pip install kicad-python`) and import it as `kipy` for KiCad 10.x IPC access.
   - Keep MCP tool handlers async. Wrap blocking `kipy` calls with `asyncio.to_thread` when needed.

2. **Architecture Requirements:**
   - The server must run over `stdio` to integrate seamlessly with VS Code's MCP client configuration.
   - Implement a `KiCadIpcClient` wrapper around `kipy.KiCad` for connection handling and user-friendly error messages.
   - Expose MCP Tools using the `@mcp.tool()` decorator provided by the MCP SDK.

3. **KiCad IPC Implementation Details:**
   - KiCad 10.x IPC clients connect to a running KiCad GUI through the platform IPC endpoint: Unix domain socket on macOS/Linux and named pipe on Windows.
    - Use `KICAD_API_SOCKET` and `KICAD_API_TOKEN` when KiCad provides them; otherwise rely on `kicad-python` defaults while developing with one running KiCad instance.
    - Do not implement raw TCP/JSON-RPC calls unless the current KiCad documentation explicitly requires that for a future API path.
   - The current repository baseline is KiCad 10 PCB-first. Treat schematic automation as future or version-gated work until the targeted KiCad version documents the needed IPC coverage.

4. **Code Style & Formatting:**
   - Write clean, asynchronous (`async`/`await`) Python code.
   - Include type hints for all function arguments and return types.
   - Handle IPC connection errors gracefully (e.g., if KiCad is not running, return a clear error message to the MCP client instead of crashing).
   - ALL code comments must be strictly in English, regardless of the prompt language.

5. **First Task to Execute:**
   - When asked to start coding, first scaffold the basic `server.py` using the `mcp` stdio server setup.
   - Next, implement the asynchronous `KiCadIpcClient` wrapper around `kipy.KiCad`.
   - Finally, implement simple test tools, e.g., `ping_kicad` and `get_kicad_version`, to verify the connection.