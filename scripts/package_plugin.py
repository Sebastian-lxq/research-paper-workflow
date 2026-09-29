#!/usr/bin/env python3
"""Build a deterministic plugin ZIP after the public-release contract passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "research-paper-workflow"
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
MANIFEST_NAME = "MANIFEST.sha256"


def plugin_version() -> str:
    data = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("plugin.json has no version")
    return version


def included_files():
    for path in sorted(PLUGIN_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(PLUGIN_ROOT)
        if path.name in IGNORED_NAMES or path.suffix == ".pyc":
            continue
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        yield path, relative


def build(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [(path, relative, path.read_bytes()) for path, relative in included_files()]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative, content in files:
            member = Path("research-paper-workflow") / relative
            info = zipfile.ZipInfo(member.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".py" else 0o644) << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        manifest = "".join(
            f"{hashlib.sha256(content).hexdigest()}  {relative.as_posix()}\n"
            for _, relative, content in files
        ).encode("utf-8")
        info = zipfile.ZipInfo(
            (Path("research-paper-workflow") / MANIFEST_NAME).as_posix(),
            ZIP_TIMESTAMP,
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(
            info,
            manifest,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    return output


def write_checksum(archive: Path) -> Path:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_name(f"{archive.name}.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return checksum


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()
    if not args.skip_validation:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_public_release.py")],
            cwd=ROOT,
            check=False,
        )
        if completed.returncode:
            return completed.returncode
    try:
        version = plugin_version()
        output = args.output or ROOT / "dist" / f"research-paper-workflow-{version}.zip"
        archive = build(output)
        checksum = write_checksum(archive)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"package failed: {exc}", file=sys.stderr)
        return 1
    verified = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_release.py"),
            str(archive),
            "--checksum",
            str(checksum),
            "--quiet",
        ],
        cwd=ROOT,
        check=False,
    )
    if verified.returncode:
        print("package failed self-verification", file=sys.stderr)
        return verified.returncode
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
