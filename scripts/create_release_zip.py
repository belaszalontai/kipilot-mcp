"""Create the Windows release ZIP from a staged build folder.

The PowerShell helper cannot rely on an external archiver: ``Compress-Archive``
fails when a freshly copied runtime file is still being scanned (Windows Defender
is the usual cause), GNU tar cannot write ZIP files at all, and the bsdtar and GNU
tar implementations share the ``tar`` name on machines with a unix-like toolchain.

This script writes the archive with the standard library instead, retries when the
operating system reports a sharing violation, and reports the archive structure so
the build can assert on it.

Usage::

    python scripts/create_release_zip.py --source artifacts/kipilot-mcp-1.2.3-windows-x64 \
        --output artifacts/kipilot-mcp-1.2.3-windows-x64.zip \
        --entry-root kipilot-mcp-1.2.3-windows-x64
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
import zipfile

SHARING_ERRORS = (PermissionError, OSError)
MAX_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 3.0


def build_archive(source: pathlib.Path, output: pathlib.Path, entry_root: str) -> None:
    """Write ``output`` as a ZIP archive containing ``source`` under ``entry_root``."""

    files = [path for path in sorted(source.rglob("*")) if path.is_file()]
    if not files:
        raise SystemExit(f"{source} does not contain any files to archive.")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)

    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in files:
            member = f"{entry_root}/{file_path.relative_to(source).as_posix()}"
            archive.write(file_path, member)

    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("--source", type=pathlib.Path, required=True, help="Staged release folder.")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="ZIP file to create.")
    parser.add_argument("--entry-root", required=True, help="Top-level folder name inside the ZIP.")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory.", file=sys.stderr)
        return 2

    output.unlink(missing_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            build_archive(source, output, args.entry_root)
        except SHARING_ERRORS as exc:
            last_error = exc
            print(f"zip attempt {attempt} failed: {exc}", file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        with zipfile.ZipFile(output) as archive:
            entries = archive.infolist()
            leaf_names = {entry.filename.rsplit("/", 1)[-1] for entry in entries}

        print(
            f"created {output} ({len(entries)} entries, "
            f"{round(output.stat().st_size / 1e6, 1)} MB)"
        )
        for required in ("kipilot-mcp.exe", "README.md", "LICENSE"):
            if required not in leaf_names:
                print(f"error: the archive does not contain {required}.", file=sys.stderr)
                return 1

        return 0

    print(f"error: failed to create {output}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
