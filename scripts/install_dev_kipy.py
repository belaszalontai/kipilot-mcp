"""Stage a kicad-python source snapshot into the running environment.

KiPilot needs a kicad-python binding that exposes the schematic, design-rule, job
and embedded-file IPC wrappers.  The PyPI release (0.8.0) ships inconsistent
generated protos - ``kipy.board_jobs``, ``kipy.board_rules``, ``kipy.schematic``
and ``kipy.schematic_types`` cannot be imported - and the upstream repository
cannot be installed with pip without its Poetry build backend and proto tooling
(the generated ``*_pb2.py`` files are produced from a KiCad checkout by
``build.py`` and are not part of the git tree).

This helper therefore works on a prepared source snapshot (a local checkout
that already contains the generated protos):

* default mode stages the pure-Python ``kipy`` package directly into the active
  environment and registers minimal distribution metadata for it;
* ``--wheel`` builds a self-contained ``py3-none-any`` wheel from the snapshot,
  which can be vendored so that packaging builds do not need a KiCad checkout.

Usage::

    <target-python> scripts/install_dev_kipy.py <source-directory>
    <target-python> scripts/install_dev_kipy.py <source-directory> --wheel vendor/kicad_python-0.9.0.dev0-py3-none-any.whl
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import pathlib
import shutil
import sys
import sysconfig
import tomllib
import zipfile

DEFAULT_VERSION = "0.9.0.dev0"
IGNORED_COPY_PATTERNS = ("__pycache__", "*.pyc", "*.pyo")
WHEEL_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def distribution_name(version: str) -> str:
    """Return the normalized ``.dist-info`` directory name for a version."""

    return f"kicad_python-{version}.dist-info"


def build_metadata(version: str, dependencies: list[str]) -> str:
    """Return the ``METADATA`` file contents for the staged distribution."""

    lines = [
        "Metadata-Version: 2.1",
        "Name: kicad-python",
        f"Version: {version}",
        "Summary: KiCad API Python Bindings (staged from a pinned source snapshot for packaging)",
        "Requires-Python: >=3.9",
    ]
    lines.extend(f"Requires-Dist: {dependency}" for dependency in dependencies)
    return "\n".join(lines) + "\n"


def build_wheel_file(version: str) -> str:
    """Return the ``WHEEL`` file contents."""

    return (
        "Wheel-Version: 1.0\n"
        "Generator: kipilot-mcp packaging\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )


def read_project_metadata(source: pathlib.Path) -> tuple[str, list[str]]:
    """Return the ``(version, dependencies)`` declared by ``source/pyproject.toml``."""

    pyproject = source / "pyproject.toml"
    if not pyproject.is_file():
        return DEFAULT_VERSION, []

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:  # pragma: no cover - defensive
        print(f"warning: unable to read {pyproject}: {exc}", file=sys.stderr)
        return DEFAULT_VERSION, []

    project = data.get("project", {})
    version = str(project.get("version", DEFAULT_VERSION))
    dependencies = [str(item) for item in project.get("dependencies", [])]
    return version, dependencies


def remove_existing_installation(target_root: pathlib.Path) -> list[str]:
    """Remove a previously installed kipy package and its distribution metadata."""

    removed: list[str] = []

    package_directory = target_root / "kipy"
    if package_directory.exists():
        shutil.rmtree(package_directory)
        removed.append("kipy")

    for dist_info in sorted(target_root.glob("kicad_python-*.dist-info")):
        shutil.rmtree(dist_info, ignore_errors=True)
        removed.append(dist_info.name)

    for egg_link in sorted(target_root.glob("kicad_python*.egg-link")):
        egg_link.unlink(missing_ok=True)
        removed.append(egg_link.name)

    for pth_file in sorted(target_root.glob("kicad_python*.pth")):
        pth_file.unlink(missing_ok=True)
        removed.append(pth_file.name)

    for pth_file in sorted(target_root.glob("__editable__*kicad*")):
        pth_file.unlink(missing_ok=True)
        removed.append(pth_file.name)

    return removed


def copy_package(source: pathlib.Path, target_root: pathlib.Path) -> pathlib.Path:
    """Copy ``source/kipy`` into the target environment and return the new path."""

    package_source = source / "kipy"
    if not (package_source / "__init__.py").is_file():
        raise SystemExit(f"{source} does not contain a kipy package (missing kipy/__init__.py).")

    validate_generated_protos(package_source, source)

    package_target = target_root / "kipy"
    shutil.copytree(
        package_source,
        package_target,
        ignore=shutil.ignore_patterns(*IGNORED_COPY_PATTERNS),
    )
    return package_target


def validate_generated_protos(package_source: pathlib.Path, source: pathlib.Path) -> None:
    """Fail when the snapshot has no generated protobuf modules.

    The generated ``*_pb2.py`` files are git-ignored in kicad-python and produced by
    ``build.py`` from a KiCad checkout, so a plain archive is not a usable snapshot.
    """

    if not sorted(package_source.glob("proto/**/*_pb2.py")):
        raise SystemExit(
            f"{source} does not contain generated protobuf modules. Generate them first by "
            "running build.py against a KiCad checkout, and use that prepared checkout as the "
            "source (a plain kicad-python archive does not include them)."
        )


def write_distribution_metadata(
    target_root: pathlib.Path,
    version: str,
    dependencies: list[str],
) -> pathlib.Path:
    """Write minimal ``.dist-info`` metadata so the staged package has a version."""

    dist_info = target_root / distribution_name(version)
    if dist_info.exists():
        shutil.rmtree(dist_info, ignore_errors=True)
    dist_info.mkdir(parents=True)

    (dist_info / "METADATA").write_text(build_metadata(version, dependencies), encoding="utf-8")
    (dist_info / "WHEEL").write_text(build_wheel_file(version), encoding="utf-8")
    (dist_info / "INSTALLER").write_text("kipilot-mcp-packaging\n", encoding="utf-8")
    (dist_info / "top_level.txt").write_text("kipy\n", encoding="utf-8")
    (dist_info / "RECORD").write_text("", encoding="utf-8")
    return dist_info


def wheel_record_entry(path_in_wheel: str, payload: bytes) -> tuple[str, str, str]:
    """Return a PEP 376 RECORD row for a wheel member."""

    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
    return path_in_wheel, f"sha256={digest}", str(len(payload))


def build_wheel(source: pathlib.Path, output: pathlib.Path) -> pathlib.Path:
    """Build a self-contained pure-Python wheel from a prepared source snapshot."""

    package_source = source / "kipy"
    if not (package_source / "__init__.py").is_file():
        raise SystemExit(f"{source} does not contain a kipy package (missing kipy/__init__.py).")

    validate_generated_protos(package_source, source)

    version, dependencies = read_project_metadata(source)
    dist_info_name = distribution_name(version)

    output.parent.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, str, str]] = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(package_source.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part == "__pycache__" for part in file_path.parts):
                continue
            if file_path.suffix in (".pyc", ".pyo"):
                continue

            member = file_path.relative_to(source).as_posix()
            payload = file_path.read_bytes()
            archive.writestr(zipfile.ZipInfo(member, date_time=WHEEL_TIMESTAMP), payload)
            records.append(wheel_record_entry(member, payload))

        metadata_files = {
            f"{dist_info_name}/METADATA": build_metadata(version, dependencies).encode("utf-8"),
            f"{dist_info_name}/WHEEL": build_wheel_file(version).encode("utf-8"),
            f"{dist_info_name}/INSTALLER": b"kipilot-mcp-packaging\n",
            f"{dist_info_name}/top_level.txt": b"kipy\n",
        }
        for member, payload in metadata_files.items():
            archive.writestr(zipfile.ZipInfo(member, date_time=WHEEL_TIMESTAMP), payload)
            records.append(wheel_record_entry(member, payload))

        record_path = f"{dist_info_name}/RECORD"
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerows(records)
        writer.writerow((record_path, "", ""))
        archive.writestr(
            zipfile.ZipInfo(record_path, date_time=WHEEL_TIMESTAMP),
            buffer.getvalue().encode("utf-8"),
        )

    print(f"built wheel {output} (kicad-python {version}, {len(records)} files)")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument("source", type=pathlib.Path, help="kicad-python source directory.")
    parser.add_argument(
        "--target",
        type=pathlib.Path,
        default=None,
        help="Target site-packages directory (defaults to the running environment).",
    )
    parser.add_argument(
        "--wheel",
        type=pathlib.Path,
        default=None,
        help="Build a wheel at this path instead of staging the package into the environment.",
    )
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory.", file=sys.stderr)
        return 2

    if args.wheel is not None:
        build_wheel(source, args.wheel.expanduser().resolve())
        return 0

    target_root = args.target or pathlib.Path(sysconfig.get_paths()["purelib"])
    if not target_root.is_dir():
        print(f"error: the target site-packages directory {target_root} does not exist.", file=sys.stderr)
        return 2

    version, dependencies = read_project_metadata(source)
    removed = remove_existing_installation(target_root)
    package_target = copy_package(source, target_root)
    dist_info = write_distribution_metadata(target_root, version, dependencies)

    if removed:
        print(f"removed previous installation: {', '.join(removed)}")
    print(f"staged kicad-python {version} from {source}")
    print(f"  package: {package_target}")
    print(f"  metadata: {dist_info}")
    print(f"  dependencies declared by the source: {len(dependencies)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
