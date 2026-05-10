# KiPilot Agent Test Workspace

This folder is a small standalone VS Code test workspace for running a custom Copilot agent against the sibling `kipilot-mcp` MCP server.

Open this `agent-test` folder in a separate VS Code window if you want a clean workspace that contains:

- a ready-to-use workspace MCP configuration
- a dedicated KiCad hardware agent
- project-level Copilot instructions for KiCad MCP usage

## What Is Included

- `.vscode/mcp.json`: VS Code MCP server configuration for the sibling KiPilot server
- `.github/copilot-instructions.md`: always-on workspace instructions for this mini test project
- `.github/agents/kicad-agent.agent.md`: the custom electronics/KiCad agent definition

## Recommended Versions

Use the versions below for the smoothest setup on Windows:

| Component | Recommended | Notes |
| --- | --- | --- |
| Windows | Windows 10 or Windows 11 | This test harness is Windows-oriented because its MCP config points at a Windows virtual environment path |
| Python | Stable CPython 3.11, 3.12, or 3.13 x64 | Avoid preview or alpha interpreters |
| Supported Python range | 3.11+ | Declared by the project |
| KiCad | 10.x | Current KiPilot baseline is KiCad 10 PCB-first |
| `kicad-python` | `>=0.7.1` | Runtime dependency |
| `mcp` | `>=1.8.0` | Runtime dependency |
| `pytest` | `>=8.3.0` | Optional, only for local test/development work |
| `pytest-asyncio` | `>=0.24.0` | Optional, only for local test/development work |
| `ruff` | `>=0.8.0` | Optional, only for local lint/development work |
| Microsoft Visual C++ Redistributable | latest 2015-2022 x64 release | Recommended on Windows for native dependency compatibility |

## Prerequisites

Install the following before using this workspace:

1. Git
2. A stable Python 3.11+ x64 release from python.org
3. KiCad 10.x
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
  - `mcp>=1.8.0`
- optional development dependencies when you run the editable development install:
  - `pytest>=8.3.0`
  - `pytest-asyncio>=0.24.0`
  - `ruff>=0.8.0`

## KiCad Setup

Before you start the MCP server, prepare KiCad:

1. Start KiCad 10.x.
2. Open the target hardware project.
3. Open the PCB Editor, not only the project manager window.
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
- timeout: `60000 ms`
- log level: `INFO`
- log file: `.logs/kipilot-agent-test.log`
- mutations: disabled by default

The parent `.venv` path is an intentional test-workspace convention so the checked-in MCP configuration can point at a predictable interpreter. It is not a general KiPilot requirement. This workspace is safe by default for exploration and dry-run previews.

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

4. Then continue with board-aware prompts, for example:

```text
Summarize the currently open PCB and list the first ten footprints.
```

```text
Find footprint R1 and preview moving it to x=42.0 mm, y=18.5 mm.
```

## Default Safety Behavior

This test workspace is intentionally conservative:

- `KIPILOT_ENABLE_MUTATIONS=0` in `.vscode/mcp.json`
- read tools work normally
- mutation tools work only in `dry_run=true` mode unless you explicitly enable live writes
- destructive tools such as board revert or item deletion still require explicit force guards

If you want to allow live board mutations in this test workspace, edit `.vscode/mcp.json` and change:

```json
"KIPILOT_ENABLE_MUTATIONS": "0"
```

to:

```json
"KIPILOT_ENABLE_MUTATIONS": "1"
```

Do that only when you are ready for real writes to the currently open board.

## Logs

By default the MCP server in this test workspace logs to:

`agent-test/.logs/kipilot-agent-test.log`

It also logs to `stderr`, which is useful when you manually run the server process.

## Quick Troubleshooting

### `ping_kicad` fails

- Make sure KiCad is already running.
- Make sure the PCB Editor is open.
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

## Suggested First Test Prompt

```text
Use the KiCad MCP tools to verify the connection, report the KiCad version, then summarize the open board. If a write would be needed, stay in dry-run mode and say so explicitly.
```