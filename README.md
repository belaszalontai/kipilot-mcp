<p align="center">
	<img src="web/KiPilot.svg" alt="KiPilot MCP">
</p>

# KiPilot MCP

KiPilot is a Python-based Model Context Protocol (MCP) server that connects MCP-aware clients, such as GitHub Copilot in VS Code, to a user-controlled KiCad 10.x PCB Editor session through the official `kicad-python` IPC binding.

The server runs over `stdio`, exposes board-aware MCP tools, and is designed for live KiCad PCB workflows where the user keeps full control of the GUI session.

## Documentation

Public project documentation is available at [kipilot.org/docs.html](https://kipilot.org/docs.html).

## Overview

KiPilot exists to let an MCP client inspect and manipulate the PCB that is already open in KiCad.

- Uses the official KiCad IPC path through `kicad-python`
- Runs as a `stdio` MCP server for VS Code and similar hosts
- Supports read-heavy PCB workflows plus guarded mutation tools
- Keeps KiCad as a separate, user-launched GUI application

This repository targets the KiCad 10 PCB-first baseline. It does not aim to be a 1:1 wrapper over every public method exposed by the KiCad Python binding.

## Current Scope

Implemented MCP surface includes:

- MCP stdio server entry point
- Async-friendly KiCad IPC client wrapper around `kipy.KiCad`
- Connectivity and version checks such as `ping_kicad` and `get_kicad_version`
- Board and document inspection tools for open documents, outlines, stackup, footprints, nets, pads, tracks, vias, zones, graphics, text, origins, title blocks, and connectivity
- Filtered lookup tools for footprints, nets, net classes, and connected items
- Guarded mutation tools for visible layers, active layer, enabled layers, origins, title block fields, board text, track creation, via creation, item updates, track geometry, zone outlines, item deletion, zone refill, board revert, and board save
- Unit tests for IPC connection and error-handling behavior

Committed baseline:

- GUI IPC only
- PCB editor first
- Read-heavy workflows first, validated mutation workflows second
- No committed schematic, export, plot, or headless automation scope

## Requirements

- Python 3.11+
- Git
- KiCad 10.x installed locally
- A running KiCad GUI instance with IPC API support

Use a stable CPython release such as 3.11, 3.12, or 3.13. Avoid preview or alpha Python interpreters because the native dependency chain may not publish wheels for them yet.

## Quick Start

Clone the public repository:

```powershell
git clone https://github.com/belaszalontai/kipilot.git
cd kipilot
```

### Windows helper

On Windows, the repository includes a convenience script that creates `.venv` when needed, installs the runtime package, applies conservative default environment variables, and can start the server for manual checks:

```powershell
.\start-kipilot-mcp.ps1 -SkipRun
```

Run without `-SkipRun` to start the server process directly from a terminal:

```powershell
.\start-kipilot-mcp.ps1
```

For VS Code, Claude Desktop, and other MCP hosts, prefer configuring the host to launch `python -m kipilot_mcp.server` directly from the prepared environment. That keeps the stdio server command explicit and easy to audit.

### Manual install

A virtual environment is recommended for dependency isolation, but it is not a KiPilot-specific requirement. If you already manage Python environments another way, point your MCP host at that interpreter instead.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
```

For development and tests, install in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Start KiCad yourself, open the target hardware project, and open the PCB Editor before using board-aware MCP tools.

## Configuration

The IPC connection uses KiCad's official API endpoint. On Windows this is a named pipe; on macOS and Linux it is a Unix domain socket. When KiCad launches an API plugin it provides these environment variables:

```powershell
$env:KICAD_API_SOCKET = "..."
$env:KICAD_API_TOKEN = "..."
```

When the server is launched from VS Code rather than from KiCad, those variables may not be present. In that case `kicad-python` falls back to the default platform-dependent IPC endpoint, which is easiest to work with when only one KiCad instance is open.

KiPilot-specific settings:

```powershell
$env:KIPILOT_KICAD_CLIENT_NAME = "kipilot-mcp"
$env:KIPILOT_KICAD_TIMEOUT_MS = "60000"
$env:KIPILOT_ENABLE_MUTATIONS = "0"
$env:KIPILOT_COMMIT_MESSAGE_PREFIX = "KiPilot MCP"
$env:KIPILOT_LOG_LEVEL = "INFO"
$env:KIPILOT_LOG_FILE = ".logs/kipilot-mcp.log"
```

Operational notes:

- `KIPILOT_ENABLE_MUTATIONS=0` keeps live board writes disabled by default
- `dry_run=true` previews remain available even when writes are disabled
- destructive tools such as revert and delete still require `force=true`
- logs go to `stderr` by default so `stdout` stays clean for MCP traffic

## Running The Server

After installation, run:

```powershell
kipilot-mcp
```

or:

```powershell
python -m kipilot_mcp.server
```

Example VS Code MCP configuration:

```json
{
	"servers": {
		"kipilot-mcp": {
			"type": "stdio",
			"command": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
			"args": ["-m", "kipilot_mcp.server"],
			"env": {
				"KIPILOT_KICAD_CLIENT_NAME": "kipilot-mcp",
				"KIPILOT_KICAD_TIMEOUT_MS": "60000",
				"KIPILOT_LOG_LEVEL": "INFO",
				"KIPILOT_LOG_FILE": ".logs/kipilot-mcp.log"
			}
		}
	}
}
```

If your KiCad setup requires an explicit API socket or token, add `KICAD_API_SOCKET` and `KICAD_API_TOKEN` to the same `env` block.

The bundled `start-kipilot-mcp.ps1` script is useful for first-run setup and manual terminal checks on Windows. MCP host configuration should normally use the direct Python command shown above so the host owns process startup and environment values.

## Development

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
python -m pytest
```

Run linting:

```powershell
python -m ruff check .
```

## Repository Layout

```text
.
|-- agent-test/
|   |-- .github/
|   |-- .logs/
|   |-- .vscode/
|   `-- README.md
|-- src/
|   `-- kipilot_mcp/
|       |-- __init__.py
|       |-- config.py
|       |-- errors.py
|       |-- ipc_client.py
|       |-- lookups.py
|       |-- serializers.py
|       `-- server.py
|-- tests/
|   `-- test_ipc_client.py
|-- web/
|   |-- KiPilot.svg
|   |-- changelog.html
|   |-- docs.html
|   |-- index.html
|   |-- script.js
|   `-- styles.css
|-- pyproject.toml
|-- README.md
`-- start-kipilot-mcp.ps1
```

## The `web/` Folder

The `web/` directory contains the static project website and public-facing documentation assets for KiPilot.
The contents of this directory are the source for the deployed `https://kipilot.org` site.

- `index.html`: landing page for the project
- `docs.html`: detailed product and MCP tool documentation
- `changelog.html`: public release notes and roadmap-style changelog page
- `styles.css`: shared styling for the site
- `script.js`: lightweight client-side behavior such as reveal animations and dynamic year handling
- `KiPilot.svg`: shared logo and branding asset

This folder is the repository's static presentation layer. It is separate from the Python MCP server so the product site, docs, and changelog can evolve independently from the runtime code.
When the website content changes, treat updates in `web/` as updates to the public `kipilot.org` site as well.

## The `agent-test/` Folder

The `agent-test/` directory is a small standalone VS Code test workspace for validating the MCP server from the perspective of a real Copilot agent setup.

Its purpose is to provide:

- a clean workspace separate from the main source tree
- a ready-made `.vscode/mcp.json` configuration that points to the sibling KiPilot server
- custom Copilot agent and instruction files for KiCad-focused testing
- a controlled workspace for end-to-end MCP validation

Open `agent-test/` in a separate VS Code window when you want to test the full agent workflow end to end without mixing that setup into the main development workspace.

## References

- [kicad-python documentation](https://docs.kicad.org/kicad-python-main/)
- [KiCad IPC API for add-on developers](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html)

## Capability Mapping

The current capability map for the server target is documented in `.github/kicad-api-capabilities.md`. Use that file as the source of truth for deciding which MCP tools belong in the KiCad 10 baseline, which ones need stronger validation, and which ones are version-gated for future KiCad releases.