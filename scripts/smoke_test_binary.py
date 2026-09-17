"""Smoke test a packaged KiPilot MCP binary over the MCP stdio transport.

The script starts the given executable, performs the MCP handshake
(``initialize``), requests ``tools/list`` and verifies that the server reports
its expected identity and tool surface.  It is used by the Windows ZIP release
build so that a binary which cannot start (for example because an optional
kicad-python binding import fails) fails the build instead of shipping.

Usage::

    python scripts/smoke_test_binary.py artifacts/kipilot-mcp-0.3.0-windows-x64/kipilot-mcp.exe

Exit code 0 means the binary answered the handshake; any other value is a
failure and the captured stderr is printed to help diagnosing the crash.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

PROTOCOL_VERSION = "2025-06-18"
EXPECTED_SERVER_NAME = "kipilot-mcp"
DEFAULT_MIN_TOOLS = 130

BUNDLE_ROOT_MARKERS = (
    "kipy/schematic_types.py",
    "kipy/proto/board/board_rules_pb2.py",
    "kipy/proto/schematic/schematic_types_pb2.py",
)
PATH_TYPE_MARKER = "PathType"
GENCODE_PATTERN = re.compile(
    r"ValidateProtobufRuntimeVersion\(\s*[^)]*?major=(\d+),\s*minor=(\d+),\s*patch=(\d+),"
)


def check_bundled_binding(executable: pathlib.Path) -> list[str]:
    """Return a list of problems found in the kicad-python binding shipped next to the exe.

    A packaged build that silently loses the optional kicad-python modules still starts and
    answers the handshake, so the structure of the bundle is verified as well.  Files are
    checked relative to the PyInstaller onedir layout (``<exe dir>/_internal``).
    """

    problems: list[str] = []
    bundle_root = executable.parent / "_internal"
    if not bundle_root.is_dir():
        # A different packaging layout: fall back to the executable directory.
        bundle_root = executable.parent

    for marker in BUNDLE_ROOT_MARKERS:
        if not (bundle_root / marker).is_file():
            problems.append(f"the packaged binding is missing {marker}")

    common_types = bundle_root / "kipy" / "common_types.py"
    if common_types.is_file():
        try:
            if PATH_TYPE_MARKER not in common_types.read_text(encoding="utf-8", errors="replace"):
                problems.append("the packaged kipy.common_types does not expose PathType")
        except OSError as exc:  # pragma: no cover - defensive
            problems.append(f"unable to read the packaged kipy.common_types: {exc}")

    for dist_info in sorted(bundle_root.glob("kicad_python-*.dist-info")) + sorted(bundle_root.glob("kipy-*.dist-info")):
        metadata = dist_info / "METADATA"
        if metadata.is_file():
            for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Version:"):
                    print(f"packaged kicad-python version: {line.split(':', 1)[1].strip()}")
                    break

    gencode = None
    for pb2_file in sorted(bundle_root.glob("kipy/proto/common/types/*_pb2.py")):
        match = GENCODE_PATTERN.search(pb2_file.read_text(encoding="utf-8", errors="replace"))
        if match:
            gencode = tuple(int(part) for part in match.groups())
            break

    if gencode is not None:
        try:
            from importlib.metadata import PackageNotFoundError, version as package_version

            try:
                runtime = tuple(int(part) for part in package_version("protobuf").split(".")[:3])
            except (PackageNotFoundError, ValueError):
                runtime = None
            if runtime is not None:
                print(f"protobuf runtime: {'.'.join(map(str, runtime))}, binding gencode: {'.'.join(map(str, gencode))}")
                if runtime < gencode:
                    problems.append(
                        f"the packaged protobuf runtime {'.'.join(map(str, runtime))} is older than the "
                        f"binding's generated code {'.'.join(map(str, gencode))}"
                    )
        except ImportError:  # pragma: no cover - very old interpreters
            pass

    return problems


def build_payload() -> str:
    """Return the newline-delimited JSON-RPC messages for the smoke test."""

    messages = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "kipilot-smoke-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    return "".join(json.dumps(message) + "\n" for message in messages)


def run_smoke_test(command: list[str], min_tools: int, timeout: float, check_bundle: bool = True) -> int:
    """Run the handshake against ``command`` and return a process exit code."""

    if check_bundle:
        executable = pathlib.Path(command[0])
        if executable.is_file():
            problems = check_bundled_binding(executable)
            if problems:
                print("FAIL: the packaged artifact is missing required kicad-python bindings:", file=sys.stderr)
                for problem in problems:
                    print(f"  - {problem}", file=sys.stderr)
                print(
                    "Rebuild with a schematic-capable kicad-python: the release build installs the "
                    "vendored wheel from vendor/ (or the checkout passed through -KiCadPythonSource). "
                    "Regenerate that wheel with scripts/install_dev_kipy.py --wheel.",
                    file=sys.stderr,
                )
                return 1

    try:
        process = subprocess.run(
            command,
            input=build_payload(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        print(f"FAIL: the executable was not found: {command[0]}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print(f"FAIL: {command[0]} did not finish the MCP handshake within {timeout}s.", file=sys.stderr)
        return 2

    server_name: str | None = None
    tool_count: int | None = None
    last_error: str | None = None

    for line in process.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        result = message.get("result")
        if message.get("id") == 1 and isinstance(result, dict):
            server_info = result.get("serverInfo")
            if isinstance(server_info, dict):
                server_name = str(server_info.get("name", ""))
        elif message.get("id") == 2 and isinstance(result, dict):
            tools = result.get("tools")
            if isinstance(tools, list):
                tool_count = len(tools)
        elif "error" in message:
            last_error = json.dumps(message.get("error"))

    if process.returncode != 0:
        print(f"FAIL: {command[0]} exited with code {process.returncode}.", file=sys.stderr)
        if process.stderr.strip():
            print("--- stderr ---", file=sys.stderr)
            print(process.stderr.strip()[-4000:], file=sys.stderr)
        return 1

    if server_name != EXPECTED_SERVER_NAME:
        print(f"FAIL: unexpected server name {server_name!r}; expected {EXPECTED_SERVER_NAME!r}.", file=sys.stderr)
        if last_error:
            print(f"server error: {last_error}", file=sys.stderr)
        if process.stderr.strip():
            print("--- stderr ---", file=sys.stderr)
            print(process.stderr.strip()[-2000:], file=sys.stderr)
        return 1

    if tool_count is None or tool_count < min_tools:
        print(f"FAIL: the server reported {tool_count!r} tools; expected at least {min_tools}.", file=sys.stderr)
        if last_error:
            print(f"server error: {last_error}", file=sys.stderr)
        return 1

    print(f"PASS: {server_name} started, {tool_count} MCP tools available.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a packaged KiPilot MCP binary.")
    parser.add_argument("command", nargs="+", help="Executable and optional arguments to start.")
    parser.add_argument("--min-tools", type=int, default=DEFAULT_MIN_TOOLS, help="Minimum tool count.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Handshake timeout in seconds.")
    parser.add_argument(
        "--skip-bundle-check",
        action="store_true",
        help="Skip the structural check of the packaged kicad-python binding.",
    )
    args = parser.parse_args()

    return run_smoke_test(
        args.command,
        args.min_tools,
        args.timeout,
        check_bundle=not args.skip_bundle_check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
