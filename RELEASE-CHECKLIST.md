# KiPilot Windows ZIP Release Checklist

Use this checklist when publishing a Windows executable release.

## Before Merge

- Confirm the intended version in `src/kipilot_mcp/__init__.py` and `pyproject.toml`.
- Review README and public site install text for consistency.
- Run tests and lint for the touched slice.

## Local Packaging Check

- Run `./build-windows-zip.ps1 -ForceInstall -Clean -ForceBindingInstall` from the repository root.
- Confirm the generated archive path under `artifacts/kipilot-mcp-<version>-windows-x64.zip`.
- Verify the ZIP includes `kipilot-mcp.exe`, `README.md`, and `LICENSE`.
- Confirm the build log reports the packaged binding (`Packaged kicad-python binding: <version>`). The
  build refuses to continue when the binding is missing the schematic, design-rule, export-job, or
  embedded-file IPC surface.
- Confirm the packaged-artifact smoke test passed (`PASS: kipilot-mcp started, <n> MCP tools available.`).
  It runs automatically at the end of the build and fails on a ZIP that cannot complete the MCP handshake.
- Start KiCad and verify one live read against the packaged executable **without** setting
  `KICAD_API_SOCKET`: `ping_kicad` must report the running KiCad version. This exercises the Windows
  named-pipe discovery and proves the artifact talks to a real KiCad instance.
- Smoke-test the extracted executable through an MCP host configuration, not by double-clicking it.

## Binding Maintenance

- The release bundles the prepared binding wheel `vendor/kicad_python-<version>-py3-none-any.whl`.
  Regenerate it with a kicad-python checkout that has generated protos:
  `./.venv/Scripts/python.exe scripts/install_dev_kipy.py <checkout> --wheel vendor/kicad_python-<version>-py3-none-any.whl`.
- Never rely on `pip install kicad-python` for packaging: the PyPI 0.8.0 wheel ships inconsistent
  generated protos, so `kipy.board_jobs`, `kipy.board_rules`, `kipy.schematic`, and `kipy.schematic_types`
  cannot be imported in it.
- Record the binding revision next to the wheel (`vendor/README.md`) when it is updated.

## Release Publication

- Merge the release branch into `main`.
- Create or update the GitHub release/tag for the target version.
- Confirm the `windows-zip-release` GitHub Actions workflow completed successfully.
- Confirm the release page contains the uploaded Windows ZIP artifact.

## Post-Release Verification

- Download the published ZIP from GitHub Releases.
- Extract it on a clean Windows machine or VM.
- Confirm the extracted build starts: `kipilot-mcp.exe` must answer the MCP `initialize` handshake and
  report 135 tools (`python scripts/smoke_test_binary.py <extracted>/kipilot-mcp.exe`).
- Start KiCad, point an MCP host at `kipilot-mcp.exe`, and run `ping_kicad`.
- Verify logs still go to `stderr` or the configured log file, never to `stdout`.

## Troubleshooting

- **The workflow fails at "Attach ZIP to GitHub release".** The ZIP is still safe as the run's
  `kipilot-mcp-windows-zip` artifact. Attach it by hand with
  `gh release upload <tag> artifacts/*.zip --clobber`, or re-run the failed jobs of the
  release-triggered run: the workflow uploads through `gh release upload`, so a re-run can simply
  retry it. A plain `workflow_dispatch` run never touches the release.