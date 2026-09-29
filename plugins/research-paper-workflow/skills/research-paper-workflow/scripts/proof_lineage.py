#!/usr/bin/env python3
"""Validate a hash-bound proof-lineage handoff without certifying mathematics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys


MANIFEST_SCHEMA = "proof-lineage-manifest.v1"
STATUS_SCHEMA = "proof-lineage-status.v1"
KINDS = {
    "claim", "assumption-set", "obligation", "lemma", "proof",
    "counterexample", "review", "certificate",
}
STATES = {
    "verified", "open", "false", "externally-dependent",
    "not-applicable", "superseded", "withdrawn",
}
RESOLVED = {"verified", "not-applicable"}
RELATIONS = {
    "depends-on", "uses-assumptions", "discharged-by", "reviewed-by",
    "falsified-by", "supersedes",
}
SUPPORT_RELATIONS = {
    "depends-on", "uses-assumptions", "discharged-by", "reviewed-by",
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,160}\Z")


class ProofLineageError(ValueError):
    pass


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ProofLineageError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path):
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(
            ProofLineageError(f"invalid JSON number: {item}")
        ),
    )
    if not isinstance(value, dict):
        raise ProofLineageError("manifest must be a JSON object")
    return value


def _exact(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ProofLineageError(f"{field} must contain exactly {sorted(fields)}")
    return value


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ProofLineageError(f"{field} must be nonempty text")
    return value.strip()


def _identifier(value, field):
    value = _text(value, field)
    if not IDENTIFIER.fullmatch(value):
        raise ProofLineageError(f"invalid {field}: {value}")
    return value


def _relative(value, field):
    value = _text(value, field)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or "\\" in value
        or value == "."
        or any(part in {"", ".", ".."} for part in path.parts)
        or value.startswith(".paper/workflow/")
    ):
        raise ProofLineageError(f"unsafe or self-referential {field}: {value}")
    return value


def _project_path(root: Path, value: str) -> Path:
    path = root
    for part in PurePosixPath(value).parts:
        path /= part
        if path.is_symlink():
            raise ProofLineageError(f"symlink project paths are not accepted: {value}")
    return path


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _binding_result(root: Path, value, field):
    binding = _exact(value, {"role", "path", "sha256", "locator"}, field)
    role = _identifier(binding["role"], f"{field}.role")
    relative = _relative(binding["path"], f"{field}.path")
    expected = binding["sha256"]
    if not isinstance(expected, str) or not SHA256.fullmatch(expected):
        raise ProofLineageError(f"{field}.sha256 must be lowercase SHA-256")
    locator = binding["locator"]
    if not isinstance(locator, dict):
        raise ProofLineageError(f"{field}.locator must be an object")
    if locator == {"kind": "file"}:
        kind = "file"
    elif (
        set(locator) == {"kind", "start", "end"}
        and locator.get("kind") == "markers"
        and all(isinstance(locator.get(name), str) and locator[name] for name in ("start", "end"))
    ):
        kind = "markers"
    else:
        raise ProofLineageError(
            f"{field}.locator must be file or explicit nonempty start/end markers"
        )

    path = _project_path(root, relative)
    result = {"role": role, "path": relative, "expected_sha256": expected}
    try:
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1:
            raise ProofLineageError(f"project artifact is not an ordinary single-link file: {relative}")
        content = path.read_bytes()
    except FileNotFoundError:
        return {**result, "status": "missing"}
    except OSError as exc:
        return {**result, "status": "unreadable", "detail": type(exc).__name__}

    if kind == "markers":
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            return {**result, "status": "locator-unresolved", "detail": "file is not UTF-8"}
        start, end = locator["start"], locator["end"]
        first, last = decoded.find(start), decoded.find(end)
        if (
            first < 0
            or last < 0
            or decoded.find(start, first + 1) >= 0
            or decoded.find(end, last + 1) >= 0
            or last < first + len(start)
        ):
            return {
                **result,
                "status": "locator-unresolved",
                "detail": "markers must occur once and enclose a non-overlapping fragment",
            }
        content = decoded[first + len(start):last].encode("utf-8")
    actual = _digest(content)
    return {
        **result,
        "status": "current" if actual == expected else "changed",
        "actual_sha256": actual,
    }


def _string_list(value, field, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "nonempty " if nonempty else ""
        raise ProofLineageError(f"{field} must be a {qualifier}array")
    result = [_identifier(item, f"{field}[]") for item in value]
    if len(result) != len(set(result)):
        raise ProofLineageError(f"{field} contains duplicates")
    return result


def _assert_acyclic(objects, edges, relations, label):
    adjacency = {identifier: [] for identifier in objects}
    for edge in edges:
        if edge["relation"] in relations:
            adjacency[edge["from"]].append(edge["to"])
    visiting, visited = set(), set()

    def visit(identifier):
        if identifier in visiting:
            raise ProofLineageError(f"{label} relations contain a cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for target in adjacency[identifier]:
            visit(target)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in adjacency:
        visit(identifier)


def validate(root: Path, manifest):
    _exact(
        manifest,
        {"schema", "lineage_id", "producer", "specialist_release", "roots", "objects", "edges"},
        "manifest",
    )
    if manifest["schema"] != MANIFEST_SCHEMA:
        raise ProofLineageError(f"unsupported schema: {manifest['schema']}")
    lineage_id = _identifier(manifest["lineage_id"], "lineage_id")
    producer = _exact(manifest["producer"], {"name", "version"}, "producer")
    producer_name = _text(producer["name"], "producer.name")
    _text(producer["version"], "producer.version")
    release = _exact(
        manifest["specialist_release"],
        {"status", "scope", "permitted_wording"},
        "specialist_release",
    )
    if release["status"] not in {"pass", "partial", "fail"}:
        raise ProofLineageError("specialist_release.status must be pass, partial, or fail")
    _text(release["scope"], "specialist_release.scope")
    _text(release["permitted_wording"], "specialist_release.permitted_wording")
    roots = _string_list(manifest["roots"], "roots", nonempty=True)

    if not isinstance(manifest["objects"], list) or not manifest["objects"]:
        raise ProofLineageError("objects must be a nonempty array")
    objects = {}
    binding_results = []
    for index, raw in enumerate(manifest["objects"]):
        field = f"objects[{index}]"
        item = _exact(raw, {"id", "kind", "version", "status", "required", "actor", "bindings"}, field)
        identifier = _identifier(item["id"], f"{field}.id")
        if identifier in objects:
            raise ProofLineageError(f"duplicate object id: {identifier}")
        if item["kind"] not in KINDS:
            raise ProofLineageError(f"unsupported {field}.kind: {item['kind']}")
        _text(item["version"], f"{field}.version")
        if item["status"] not in STATES:
            raise ProofLineageError(f"unsupported {field}.status: {item['status']}")
        if type(item["required"]) is not bool:
            raise ProofLineageError(f"{field}.required must be boolean")
        if item["kind"] == "review":
            actor = _text(item["actor"], f"{field}.actor")
        elif item["actor"] is not None:
            raise ProofLineageError(f"{field}.actor must be null outside review objects")
        else:
            actor = None
        if not isinstance(item["bindings"], list) or not item["bindings"]:
            raise ProofLineageError(f"{field}.bindings must be a nonempty array")
        roles = set()
        for binding_index, binding in enumerate(item["bindings"]):
            result = _binding_result(root, binding, f"{field}.bindings[{binding_index}]")
            if result["role"] in roles:
                raise ProofLineageError(f"{field}.bindings repeats role {result['role']}")
            roles.add(result["role"])
            binding_results.append({"object_id": identifier, **result})
        objects[identifier] = {**item, "actor": actor}

    for root_id in roots:
        if root_id not in objects:
            raise ProofLineageError(f"root references unknown object: {root_id}")
        if objects[root_id]["kind"] != "claim":
            raise ProofLineageError(f"root must reference a claim object: {root_id}")

    if not isinstance(manifest["edges"], list) or not manifest["edges"]:
        raise ProofLineageError("edges must be a nonempty array")
    edges, seen_edges = [], set()
    for index, raw in enumerate(manifest["edges"]):
        field = f"edges[{index}]"
        edge = _exact(raw, {"from", "to", "relation"}, field)
        source = _identifier(edge["from"], f"{field}.from")
        target = _identifier(edge["to"], f"{field}.to")
        if source not in objects or target not in objects:
            raise ProofLineageError(f"{field} references an unknown object")
        if source == target:
            raise ProofLineageError(f"{field} cannot be a self edge")
        if edge["relation"] not in RELATIONS:
            raise ProofLineageError(f"unsupported {field}.relation: {edge['relation']}")
        source_kind, target_kind = objects[source]["kind"], objects[target]["kind"]
        if edge["relation"] == "uses-assumptions" and target_kind != "assumption-set":
            raise ProofLineageError(f"{field} uses-assumptions must target an assumption-set")
        if edge["relation"] == "discharged-by" and not (
            source_kind == "obligation" and target_kind in {"proof", "certificate"}
        ):
            raise ProofLineageError(f"{field} discharged-by must connect an obligation to a proof/certificate")
        if edge["relation"] == "reviewed-by" and target_kind != "review":
            raise ProofLineageError(f"{field} reviewed-by must target a review")
        if edge["relation"] == "falsified-by" and target_kind != "counterexample":
            raise ProofLineageError(f"{field} falsified-by must target a counterexample")
        if edge["relation"] == "supersedes" and source_kind != target_kind:
            raise ProofLineageError(f"{field} supersedes must connect objects of the same kind")
        if edge["relation"] == "depends-on" and target_kind in {
            "assumption-set", "counterexample", "review"
        }:
            raise ProofLineageError(f"{field} depends-on uses the wrong target kind")
        key = (source, target, edge["relation"])
        if key in seen_edges:
            raise ProofLineageError(f"duplicate edge: {key}")
        seen_edges.add(key)
        edges.append({"from": source, "to": target, "relation": edge["relation"]})
    _assert_acyclic(objects, edges, SUPPORT_RELATIONS, "load-bearing support")
    _assert_acyclic(objects, edges, {"supersedes"}, "supersession")

    outgoing = {identifier: [] for identifier in objects}
    for edge in edges:
        outgoing[edge["from"]].append(edge)
    closure, frontier = set(roots), list(roots)
    while frontier:
        source = frontier.pop()
        for edge in outgoing[source]:
            if edge["relation"] in SUPPORT_RELATIONS and edge["to"] not in closure:
                closure.add(edge["to"])
                frontier.append(edge["to"])

    blockers = []
    unresolved = sorted(identifier for identifier in closure if objects[identifier]["status"] not in RESOLVED)
    if unresolved:
        blockers.append(f"unresolved support objects: {unresolved}")
    required_ids = sorted(identifier for identifier, item in objects.items() if item["required"])
    orphan_required = sorted(set(required_ids) - closure)
    if orphan_required:
        blockers.append(f"required objects are outside the active root closure: {orphan_required}")
    unresolved_required = sorted(identifier for identifier in required_ids if objects[identifier]["status"] not in RESOLVED)
    if unresolved_required:
        blockers.append(f"required objects are unresolved: {unresolved_required}")

    review_ids = set()
    for root_id in roots:
        if objects[root_id]["status"] != "verified":
            blockers.append(f"root claim is not verified: {root_id}")
        if not objects[root_id]["required"]:
            blockers.append(f"active root claim is not marked required: {root_id}")
        related = outgoing[root_id]
        assumptions = [edge["to"] for edge in related if edge["relation"] == "uses-assumptions" and objects[edge["to"]]["kind"] == "assumption-set"]
        obligations = [edge["to"] for edge in related if edge["relation"] == "depends-on" and objects[edge["to"]]["kind"] == "obligation"]
        reviews = [edge["to"] for edge in related if edge["relation"] == "reviewed-by" and objects[edge["to"]]["kind"] == "review"]
        if not assumptions:
            blockers.append(f"root claim has no bound assumption set: {root_id}")
        if not obligations:
            blockers.append(f"root claim has no bound proof obligation: {root_id}")
        if not reviews:
            blockers.append(f"root claim has no review record: {root_id}")
        review_ids.update(reviews)

    for identifier in sorted(closure):
        item = objects[identifier]
        if item["kind"] == "obligation" and item["status"] == "verified":
            discharge = [
                edge["to"] for edge in outgoing[identifier]
                if edge["relation"] == "discharged-by"
                and objects[edge["to"]]["kind"] in {"proof", "certificate"}
                and objects[edge["to"]]["status"] == "verified"
            ]
            if not discharge:
                blockers.append(f"verified obligation lacks a verified proof/certificate: {identifier}")

    recorded_distinct_review = bool(review_ids) and all(
        objects[identifier]["status"] == "verified"
        and objects[identifier]["actor"] != producer_name
        for identifier in review_ids
    )
    if not recorded_distinct_review:
        blockers.append("a verified review with a reviewer identity distinct from the producer is not recorded")
    if release["status"] != "pass":
        blockers.append(f"specialist release status is {release['status']}")
    noncurrent = [item for item in binding_results if item["status"] != "current"]
    if noncurrent:
        blockers.append(
            "bound artifacts are not current: "
            + str(sorted({item["object_id"] for item in noncurrent}))
        )

    return {
        "schema": STATUS_SCHEMA,
        "lineage_id": lineage_id,
        "valid": True,
        "workflow_consumable": not blockers,
        "active_root_ids": roots,
        "support_closure_ids": sorted(closure),
        "required_ids": required_ids,
        "unresolved_ids": unresolved,
        "orphan_required_ids": orphan_required,
        "specialist_release_status": release["status"],
        "specialist_release_scope": release["scope"],
        "permitted_wording": release["permitted_wording"],
        "binding_summary": {
            "total": len(binding_results),
            "current": sum(item["status"] == "current" for item in binding_results),
            "noncurrent": len(noncurrent),
        },
        "bindings": binding_results,
        "distinct_reviewer_identity_recorded": recorded_distinct_review,
        "reviewer_independence_established": False,
        "mathematical_correctness_established": False,
        "scientific_certification": "not-established-by-this-tool",
        "blockers": blockers,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise ProofLineageError("--project must name an existing absolute ordinary directory")
        root = root.resolve()
        record = Path(args.record)
        if not record.is_absolute():
            record = root / record
        record = record.resolve()
        if not record.is_relative_to(root) or record.is_symlink() or not record.is_file():
            raise ProofLineageError("--record must name an ordinary project file")
        result = validate(root, load(record))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if result["workflow_consumable"] else 1
    except (OSError, ProofLineageError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
