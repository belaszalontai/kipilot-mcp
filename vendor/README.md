# Vendored kicad-python binding

`kicad_python-0.9.0.dev0-py3-none-any.whl` is a pure-Python build of the official KiCad IPC
bindings (`kipy`). The Windows ZIP release installs this wheel instead of the PyPI release.

## Why this wheel exists

- The PyPI release **0.8.0** ships inconsistent generated protos. In that wheel `kipy.board_jobs`,
  `kipy.board_rules`, `kipy.schematic`, and `kipy.schematic_types` cannot be imported at all, so it
  cannot serve the export-job, design-rule, embedded-file, or schematic tools.
- The upstream repository cannot be installed with `pip`. Its build backend is Poetry and
  `[tool.poetry.build]` runs `build.py`, which regenerates the protobuf modules from a KiCad
  checkout (`kicad/api/proto`). Those generated `kipy/proto/**/*_pb2.py` files are git-ignored
  upstream, so a source archive does not contain a usable package.
- Packaging therefore uses this prepared wheel: no KiCad checkout, no `protoc`, and no Poetry
  build backend is needed on the build machine or in CI.

## Provenance

- Upstream source: `https://gitlab.com/kicad/code/kicad-python`, revision `87b945a`
  (`0.9.0.dev0`, the revision KiPilot 0.4.0 is developed and tested against). This revision adds the
  KiCad 11 library IPC surface (`get_library_*`, `load_all_libraries`, `reload_library`,
  `wait_for_libraries`), `place_symbol_from_library` / `place_footprint_from_library`, PNG plotting,
  and net class assignments.
- Protobuf modules: generated from the KiCad `api/proto` sources at KiCad revision `dcadf9b`
  (the submodule revision recorded by kicad-python `87b945a`), then rewritten with protoletariat.
  The generated modules include `common/types/library_types_pb2` and
  `common/commands/library_commands_pb2`.
- Runtime dependencies are installed separately by the build script: `protobuf==6.33.5` (matching
  the generated code), `pynng`, `jsonschema`, `typing_extensions`, and `zstandard`.

## Regenerating the wheel

Run this on a machine that has a kicad-python checkout with generated protos:

```powershell
./.venv/Scripts/python.exe scripts/install_dev_kipy.py <kicad-python-checkout> --wheel vendor/kicad_python-<version>-py3-none-any.whl
```

Update the upstream revision and this file when the wheel is rebuilt. The build script installs the
newest `vendor/kicad_python-*.whl`, probes the environment for the required IPC surface, and fails
the build if the binding is incomplete.
