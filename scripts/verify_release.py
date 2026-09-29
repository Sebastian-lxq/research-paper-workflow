#!/usr/bin/env python3
"""Verify a packaged plugin archive, its checksum, and its internal manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile


PACKAGE_ROOT = "research-paper-workflow"
MANIFEST = f"{PACKAGE_ROOT}/MANIFEST.sha256"
MAX_FILES = 10_000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class VerificationError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: str) -> str:
    prefix = f"{PACKAGE_ROOT}/"
    if not name.startswith(prefix) or name.endswith("/") or "\\" in name:
        raise VerificationError(f"noncanonical archive member: {name!r}")
    relative = name[len(prefix):]
    path = PurePosixPath(relative)
    if (
        not relative
        or path.is_absolute()
        or path.as_posix() != relative
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise VerificationError(f"unsafe archive member: {name!r}")
    return relative


def verify_checksum(archive: Path, checksum: Path) -> str:
    if not checksum.is_file() or checksum.is_symlink():
        raise VerificationError(f"checksum is not an ordinary file: {checksum}")
    lines = checksum.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1:
        raise VerificationError("checksum sidecar must contain exactly one line")
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", lines[0])
    if match is None or match.group(2) != archive.name:
        raise VerificationError("checksum sidecar does not name this archive")
    actual = file_sha256(archive)
    if actual != match.group(1):
        raise VerificationError("archive SHA-256 does not match the sidecar")
    return actual


def parse_manifest(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("internal manifest is not UTF-8") from exc
    if not text or not text.endswith("\n"):
        raise VerificationError("internal manifest must be nonempty and newline-terminated")
    records: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise VerificationError("malformed internal manifest line")
        digest, relative = match.groups()
        if not SHA256.fullmatch(digest) or relative in records:
            raise VerificationError("duplicate or invalid internal manifest record")
        if safe_member(f"{PACKAGE_ROOT}/{relative}") != relative or relative == "MANIFEST.sha256":
            raise VerificationError("unsafe or self-referential internal manifest path")
        records[relative] = digest
    return records


def verify_archive(archive: Path, checksum: Path) -> dict:
    if archive.is_symlink() or checksum.is_symlink():
        raise VerificationError("archive and checksum must not be symbolic links")
    archive = archive.resolve()
    checksum = checksum.resolve()
    if not archive.is_file():
        raise VerificationError(f"archive is not an ordinary file: {archive}")
    archive_digest = verify_checksum(archive, checksum)
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        names = [item.filename for item in members]
        if len(names) > MAX_FILES:
            raise VerificationError("archive contains too many files")
        if len(names) != len(set(names)):
            raise VerificationError("archive contains duplicate member names")
        if sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES:
            raise VerificationError("archive exceeds the uncompressed-size limit")
        if bundle.testzip() is not None:
            raise VerificationError("archive CRC verification failed")
        relative_names = {safe_member(name) for name in names}
        if MANIFEST not in names:
            raise VerificationError("archive is missing MANIFEST.sha256")
        manifest = parse_manifest(bundle.read(MANIFEST))
        expected = relative_names - {"MANIFEST.sha256"}
        if set(manifest) != expected:
            missing = sorted(expected - set(manifest))
            extra = sorted(set(manifest) - expected)
            raise VerificationError(
                f"internal manifest coverage mismatch: missing={missing}, extra={extra}"
            )
        for relative, expected_digest in manifest.items():
            actual = hashlib.sha256(bundle.read(f"{PACKAGE_ROOT}/{relative}")).hexdigest()
            if actual != expected_digest:
                raise VerificationError(f"internal manifest digest mismatch: {relative}")
        try:
            portable = json.loads(bundle.read(f"{PACKAGE_ROOT}/plugin.json"))
            compatibility = json.loads(
                bundle.read(f"{PACKAGE_ROOT}/.codex-plugin/plugin.json")
            )
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VerificationError("plugin manifests are missing or invalid") from exc
        if (
            not isinstance(portable, dict)
            or not isinstance(compatibility, dict)
            or portable.get("name") != PACKAGE_ROOT
            or compatibility.get("name") != PACKAGE_ROOT
            or portable.get("version") != compatibility.get("version")
            or not isinstance(portable.get("version"), str)
        ):
            raise VerificationError("plugin manifests disagree on package identity or version")
        forbidden = sorted(
            name for name in names if "__pycache__" in name or name.endswith(".pyc")
        )
        if forbidden:
            raise VerificationError(f"archive contains generated Python files: {forbidden}")
    return {
        "valid": True,
        "name": PACKAGE_ROOT,
        "version": portable["version"],
        "archive_sha256": archive_digest,
        "packaged_file_count": len(manifest),
        "checks": [
            "external-checksum",
            "canonical-members",
            "crc",
            "internal-manifest-coverage",
            "internal-file-hashes",
            "manifest-identity",
            "generated-file-exclusion",
        ],
        "scope": "Byte integrity and package identity only; publisher identity and scientific validity are not authenticated.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--checksum", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    checksum = args.checksum or args.archive.with_name(f"{args.archive.name}.sha256")
    try:
        result = verify_archive(args.archive, checksum)
    except (OSError, VerificationError, zipfile.BadZipFile) as exc:
        if not args.quiet:
            print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if not args.quiet:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
