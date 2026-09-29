"""Read-only file/fragment freshness checks for registered release records.

Bindings attest byte identity to an explicitly registered baseline, never proof
truth or the meaning of the contract's content_hash/scope_hash. The record digest
is SHA256 of canonical JSON (sort_keys=True, ensure_ascii=False, separators=(",",
":"), allow_nan=False), encoded as UTF-8. No baseline refresh is performed.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any


BINDING_SCHEMA = "research-content-bindings.v1"
REPORT_SCHEMA = "research-content-bindings-report.v1"
# Compatibility alias for callers that imported the original constant.
BINDING_VERSION = BINDING_SCHEMA
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = (
    "Byte identity and registered record identity only; scientific correctness, "
    "semantic mappings, and unregistered objects or dependencies remain unverified."
)


def record_sha256(record: dict[str, Any]) -> str:
    """Fingerprint an existing object/artifact record without reinterpreting it."""
    raw = json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _safe_path(root: Path, value: str) -> Path:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("path must be a project-relative POSIX path without traversal")
    try:
        resolved = (root / path).resolve()
        resolved.relative_to(root)
    except (ValueError, RuntimeError, OSError) as exc:
        raise ValueError("path escapes project root or cannot safely resolve") from exc
    return resolved


def _check_content(path: Path, locator: dict, expected: str) -> dict[str, Any]:
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return {"status": "locator_unresolved", "detail": "bound path is not a regular file"}
        content = path.read_bytes()
    except FileNotFoundError:
        return {"status": "missing", "detail": "bound file is missing"}
    except OSError as exc:
        return {"status": "locator_unresolved", "detail": f"cannot read file: {type(exc).__name__}"}
    if locator["kind"] == "markers":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return {"status": "locator_unresolved", "detail": "fragment file is not UTF-8"}
        start, end = locator["start"], locator["end"]
        first, last = text.find(start), text.find(end)
        # Find from the next character so overlapping duplicate markers also fail.
        if (
            first < 0 or last < 0
            or text.find(start, first + 1) >= 0
            or text.find(end, last + 1) >= 0
            or last < first + len(start)
        ):
            return {"status": "locator_unresolved", "detail": "markers must each occur once and enclose a non-overlapping fragment"}
        content = text[first + len(start):last].encode("utf-8")
    actual = hashlib.sha256(content).hexdigest()
    return {"status": "unchanged" if actual == expected else "changed", "actual_sha256": actual}


def check_bindings(
    data: dict[str, Any], bindings: Any, project_root: Path | str | None,
    required_claim_ids: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Check all registered targets; only the required closure controls coverage.

    The caller must validate the original contract first. Artifact snapshots may
    preserve prior support IDs, but only existing claims can receive graph blockers.
    If prior support cannot be recovered, the required closure is explicitly unknown.
    Malformed bindings/path escapes are structural errors, never weak matches.
    """
    if bindings is None:
        if project_root is not None:
            return {}, ["project_root requires a bindings sidecar"]
        return {
            "mode": "record-only", "scope": "Recorded contract consistency only; no actual files or byte hashes were checked.",
            "coverage": None, "targets": [],
        }, []
    if not isinstance(bindings, dict) or bindings.get("schema_version") != BINDING_VERSION:
        return {}, [f"bindings sidecar must have schema_version={BINDING_VERSION}"]
    errors: list[str] = []
    if set(bindings) != {"schema_version", "bindings"}:
        errors.append("bindings sidecar must contain exactly schema_version and bindings")
    if not isinstance(bindings.get("bindings"), list):
        return {}, errors + ["bindings sidecar bindings must be an array"]
    if project_root is None:
        return {}, errors + ["bindings sidecar requires an explicit project_root"]
    try:
        root = Path(project_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("project_root is not a directory")
    except (TypeError, ValueError, OSError, RuntimeError) as exc:
        return {}, errors + [f"invalid project_root: {type(exc).__name__}: {exc}"]

    records = {
        (kind, record[f"{kind}_id"]): record
        for kind, collection in (("object", "objects"), ("artifact", "artifacts"))
        for record in data[collection]
    }
    selected: dict[tuple[str, str], tuple[dict, Path]] = {}
    common = {"record_sha256", "path", "sha256", "locator"}
    for index, binding in enumerate(bindings["bindings"]):
        prefix = f"bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        keys = set(binding)
        kinds = [kind for kind in ("object", "artifact") if f"{kind}_id" in binding]
        if len(kinds) != 1:
            errors.append(f"{prefix} must contain one object_id/artifact_id plus {sorted(common)}")
            continue
        kind = kinds[0]
        required_keys = common | {f"{kind}_id"}
        allowed_keys = required_keys | ({"record_snapshot"} if kind == "artifact" else set())
        if not required_keys.issubset(keys) or keys - allowed_keys:
            errors.append(f"{prefix} has missing or unknown binding fields")
            continue
        identifier = binding[f"{kind}_id"]
        if not isinstance(identifier, str) or (kind, identifier) not in records:
            errors.append(f"{prefix} references an unregistered {kind}")
            continue
        identity = (kind, identifier)
        if identity in selected:
            errors.append(f"{prefix} repeats {kind}_id={identifier}")
            continue
        if any(not isinstance(binding[key], str) or not SHA256.fullmatch(binding[key])
               for key in ("sha256", "record_sha256")):
            errors.append(f"{prefix} sha256 and record_sha256 must be lowercase SHA256 hex")
            continue
        if "record_snapshot" in binding:
            snapshot = binding["record_snapshot"]
            if (
                not isinstance(snapshot, dict)
                or snapshot.get("artifact_id") != identifier
                or snapshot.get("freshness") not in ("current", "stale")
                or not isinstance(snapshot.get("claim_ids"), list)
                or not all(isinstance(cid, str) and cid.strip() for cid in snapshot["claim_ids"])
            ):
                errors.append(f"{prefix}.record_snapshot must be a complete artifact record with the same artifact_id")
                continue
            try:
                snapshot_digest = record_sha256(snapshot)
            except (TypeError, ValueError) as exc:
                errors.append(f"{prefix}.record_snapshot cannot be canonical JSON: {type(exc).__name__}")
                continue
            if snapshot_digest != binding["record_sha256"]:
                errors.append(f"{prefix}.record_snapshot does not match record_sha256")
                continue
        locator = binding["locator"]
        if not isinstance(locator, dict) or not (
            (locator == {"kind": "file"})
            or (set(locator) == {"kind", "start", "end"}
                and locator["kind"] == "markers"
                and all(isinstance(locator[key], str) and locator[key] for key in ("start", "end")))
        ):
            errors.append(f"{prefix}.locator must be file or explicit non-empty start/end markers")
            continue
        if not isinstance(binding["path"], str) or not binding["path"]:
            errors.append(f"{prefix}.path must be a non-empty project-relative path")
            continue
        try:
            path = _safe_path(root, binding["path"])
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
            continue
        selected[identity] = binding, path
    if errors:
        return {}, sorted(set(errors))

    targets = []
    registered_claim_ids = {claim["claim_id"] for claim in data["claims"]}
    for (kind, identifier), record in sorted(records.items()):
        claim_ids = sorted(set(
            record["claim_ids"] if kind == "artifact" else
            [claim["claim_id"] for claim in data["claims"] if claim["object_id"] == identifier]
        ))
        target = {
            "target_kind": kind, "target_id": identifier, "claim_ids": claim_ids,
            "required": bool(required_claim_ids.intersection(claim_ids)),
            "blocking_claim_ids": claim_ids,
            "support_ownership_unknown": False,
        }
        if (kind, identifier) not in selected:
            target.update(status="unbound", record_matches=None)
        else:
            binding, path = selected[(kind, identifier)]
            current_record = record_sha256(record)
            result = _check_content(path, binding["locator"], binding["sha256"])
            target.update(result)
            target.update(
                path=binding["path"], locator=binding["locator"],
                expected_sha256=binding["sha256"],
                expected_record_sha256=binding["record_sha256"],
                actual_record_sha256=current_record,
                record_matches=current_record == binding["record_sha256"],
            )
            if not target["record_matches"] and target["status"] == "unchanged":
                target.update(status="changed", detail="registered record changed")
            if kind == "artifact" and not target["record_matches"]:
                snapshot = binding.get("record_snapshot")
                baseline_ids = set(snapshot["claim_ids"]) if snapshot is not None else set()
                unresolved = baseline_ids - registered_claim_ids
                known_support = set(claim_ids) | (baseline_ids & registered_claim_ids)
                unknown = snapshot is None or bool(unresolved)
                # This is a coverage blocker, not a newly invented support edge.
                blocking_ids = known_support | (required_claim_ids if unknown else set())
                target.update(
                    current_claim_ids=claim_ids,
                    baseline_claim_ids=sorted(baseline_ids) if snapshot is not None else None,
                    unresolved_claim_ids=sorted(unresolved),
                    claim_ids=sorted(known_support),
                    blocking_claim_ids=sorted(blocking_ids),
                    support_ownership_unknown=unknown,
                    required=bool(required_claim_ids.intersection(blocking_ids)),
                )
        targets.append(target)
    required = [target for target in targets if target["required"]]
    return {
        "mode": "bound-content-check", "schema_version": REPORT_SCHEMA, "scope": SCOPE,
        "coverage": {
            "required_target_count": len(required),
            "bound_required_target_count": sum(target["status"] != "unbound" for target in required),
            "required_unbound_targets": [
                {"target_kind": target["target_kind"], "target_id": target["target_id"]}
                for target in required if target["status"] == "unbound"
            ],
            "unknown_support_targets": [
                {"target_kind": target["target_kind"], "target_id": target["target_id"]}
                for target in targets if target["support_ownership_unknown"]
            ],
            "registered_required_contents_unchanged": bool(required) and all(
                target["status"] == "unchanged" for target in required
            ),
        },
        "targets": targets,
    }, []
