# KiPilot Windows ZIP Release Checklist

Use this checklist when publishing a Windows executable release.

## Before Merge

- Confirm the intended version in `src/kipilot_mcp/__init__.py` and `pyproject.toml`.
- Review README and public site install text for consistency.
- Run tests and lint for the touched slice.

## Local Packaging Check

- Run `./build-windows-zip.ps1 -ForceInstall -Clean` from the repository root.
- Confirm the generated archive path under `artifacts/kipilot-mcp-<version>-windows-x64.zip`.
- Verify the ZIP includes `kipilot-mcp.exe`, `README.md`, and `LICENSE`.
- Smoke-test the extracted executable through an MCP host configuration, not by double-clicking it.

## Release Publication

- Merge the release branch into `main`.
- Create or update the GitHub release/tag for the target version.
- Confirm the `windows-zip-release` GitHub Actions workflow completed successfully.
- Confirm the release page contains the uploaded Windows ZIP artifact.

## Post-Release Verification

- Download the published ZIP from GitHub Releases.
- Extract it on a clean Windows machine or VM.
- Start KiCad, point an MCP host at `kipilot-mcp.exe`, and run `ping_kicad`.
- Verify logs still go to `stderr` or the configured log file, never to `stdout`.