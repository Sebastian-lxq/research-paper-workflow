#!/usr/bin/env python3
"""Build a bounded, evidence-first re-review handoff (standard library only).

CLI:
  prepare SPEC_JSON OUTDIR
  criteria OUTDIR RESULT_JSON
  evidence OUTDIR RESULT_JSON
  reveal OUTDIR
  verify OUTDIR

SPEC_JSON has exactly these fields:
  {"schema_version":"review-handoff-spec.v1", "project_root":"/absolute/root",
   "issues":[{"issue_id":"R1", "criterion":"Acceptance criterion to assess"}],
   "old":["old.md"], "new":["new.md"], "evidence":["checks.txt"],
   "response":["reply.md"]}
All four file arrays and issues are nonempty; IDs are unique nonempty strings.
Paths are project-relative regular files, without '..', absolute paths, or
symlink escapes. Different source entries cannot alias the same physical file.
The spec and result JSON files are outside OUTDIR; OUTDIR must not exist.

Criteria RESULT_JSON has exactly:
  {"schema_version":"review-handoff-criteria.v1",
   "issues":[{"issue_id":"R1", "criterion":"Frozen operational criterion"}]}
Evidence RESULT_JSON has exactly:
  {"schema_version":"review-handoff-evidence.v1", "issues":[{
    "issue_id":"R1", "status":"resolved", "reason":"Reason for verdict",
    "evidence_locators":[{"path":"new.md", "locator":"section 2, lines 8-12"}]
  }]}
Both results must cover exactly the spec issue IDs, once each. Evidence status
is resolved or unresolved; every issue requires a reason and at least one
locator. Locator paths must belong to registered old/new/evidence files; locator
text is recorded, not semantically checked. An unresolved finding can identify
the inspected passage and explain the missing evidence in its reason.

Only send the relevant stage directory to a worker:
  stage1/packet.json: issue IDs and input criteria only.
  stage2/: frozen criteria and copies of old/new/evidence (no response).
  stage3/: frozen evidence verdict and response copies.
The controller must retain .controller privately; its source paths may identify
the response. Evidence seals the verdict and creates stage3. reveal only checks
and returns that existing packet. No command overwrites an existing stage.
Source bytes (including spec and submitted result files), frozen results, and
all generated files are hashed. Every advance and verify checks them. verify is
read-only. Failed/incomplete stages require a new OUTDIR, not an in-place reset.
Concurrent controllers are unsupported; directory creation refuses collisions.

This is a derived review bundle, not a claims database or a security sandbox.
Hashes detect changed bytes against local seals, not coordinated rewriting of
all seals by an attacker. It cannot authenticate a fresh context, reviewer
independence, actual non-exposure, or scientific validity. The controller must
start separate appropriate review contexts and supply only the specified stage.
Exit 0 means structural/integrity checks passed; exit 2 means refusal/error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


SCOPE = ("Derived packet and byte integrity only; fresh context, independence, "
         "non-exposure, and scientific validity are not authenticated.")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, fields, label):
    require(isinstance(value, dict) and set(value) == set(fields),
            f"{label} must contain exactly {sorted(fields)}")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, f"duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def scoped(root, relative):
    require(nonempty(relative), "source path must be a nonempty string")
    rel = Path(relative)
    require(not rel.is_absolute() and ".." not in rel.parts and str(rel) == relative,
            f"noncanonical/escaping path: {relative}")
    target = (root / rel).resolve(strict=True)
    require(target.is_relative_to(root) and target.is_file(),
            f"path is not a regular file within project root: {relative}")
    return target


def source_record(path):
    path = Path(path).absolute()
    require(path.is_file(), f"missing source: {path}")
    return {"path": str(path), "resolved": str(path.resolve(strict=True)),
            "sha256": digest(path.read_bytes())}


def check_source(record):
    current = source_record(record["path"])
    require(current == record, f"source changed: {record['path']}")


def issue_records(data, schema, fields, wanted=None):
    exact(data, {"schema_version", "issues"}, "result")
    require(data["schema_version"] == schema, f"expected {schema}")
    issues = data["issues"]
    require(isinstance(issues, list) and issues, "issues must be nonempty")
    seen = set()
    for issue in issues:
        exact(issue, fields, "issue")
        require(nonempty(issue["issue_id"]), "issue_id must be nonempty")
        require(issue["issue_id"] not in seen, "duplicate issue_id")
        seen.add(issue["issue_id"])
        if "criterion" in fields:
            require(nonempty(issue["criterion"]), "criterion must be nonempty")
    if wanted is not None:
        require(seen == set(wanted), "result must cover exactly the registered issue IDs")
    return issues


def seal(out, stage, sources, files):
    payload = {"stage": stage, "sources": sources, "files": {
        name: digest((out / name).read_bytes()) for name in sorted(files)}}
    write_new(out / ".controller" / f"stage{stage}.json",
              encoded({"payload": payload, "sha256": digest(encoded(payload))}))


def read_seal(out, stage):
    item = load(out / ".controller" / f"stage{stage}.json")
    exact(item, {"payload", "sha256"}, "seal")
    require(digest(encoded(item["payload"])) == item["sha256"], "seal changed")
    payload = item["payload"]
    exact(payload, {"stage", "sources", "files"}, "seal payload")
    require(payload["stage"] == stage, "incorrect seal stage")
    return payload


def verify(outdir):
    """Read-only verification of every existing stage; raise on drift."""
    out = Path(outdir).absolute()
    require(out.is_dir() and not out.is_symlink(), "invalid bundle directory")
    manifest = load(out / ".controller" / "manifest.json")
    tracked = set()
    sources = []
    last = 0
    for stage in (1, 2, 3):
        directory = out / f"stage{stage}"
        receipt = out / ".controller" / f"stage{stage}.json"
        if not directory.exists() and not receipt.exists():
            continue
        require(stage == last + 1, "noncontiguous stages")
        require(directory.is_dir() and receipt.is_file(), "incomplete stage")
        payload = read_seal(out, stage)
        for name, expected in payload["files"].items():
            require(name not in tracked, "duplicate sealed path")
            file = scoped(out.resolve(), name)
            require(not (out / name).is_symlink(), "symlink in sealed bundle")
            require(digest(file.read_bytes()) == expected, f"frozen file changed: {name}")
            tracked.add(name)
        sources.extend(payload["sources"])
        tracked.add(f".controller/stage{stage}.json")
        last = stage
    require(last >= 1 and ".controller/manifest.json" in tracked, "missing initial seal")
    actual = set()
    for file in out.rglob("*"):
        require(not file.is_symlink(), "symlink in bundle")
        if file.is_file():
            actual.add(file.relative_to(out).as_posix())
    require(actual == tracked, "unexpected or unsealed bundle files")
    root = Path(manifest["project_root"])
    require(root.resolve(strict=True) == root, "project root changed")
    for role in ("old", "new", "evidence", "response"):
        for relative in manifest["roles"][role]:
            scoped(root, relative)
    for record in sources:
        check_source(record)
    return {"valid": True, "stage": last, "scope": SCOPE}


def prepare(spec_path, outdir):
    spec_path = Path(spec_path).absolute()
    spec_record = source_record(spec_path)
    spec = load(spec_path)
    roles = ("old", "new", "evidence", "response")
    exact(spec, {"schema_version", "project_root", "issues", *roles}, "spec")
    require(spec["schema_version"] == "review-handoff-spec.v1", "wrong spec schema")
    require(nonempty(spec["project_root"]) and Path(spec["project_root"]).is_absolute(),
            "project_root must be absolute")
    root = Path(spec["project_root"]).resolve(strict=True)
    require(root.is_dir(), "project_root must be a directory")
    issues = issue_records({"schema_version": "review-handoff-criteria.v1",
                            "issues": spec["issues"]}, "review-handoff-criteria.v1",
                           {"issue_id", "criterion"})
    out = Path(outdir).absolute()
    require(not out.exists() and not out.is_symlink(), "OUTDIR already exists")
    require(not spec_path.resolve().is_relative_to(out.resolve()), "spec inside OUTDIR")
    records = [spec_record]
    identities = set()
    for role in roles:
        require(isinstance(spec[role], list) and spec[role], f"{role} must be nonempty")
        for relative in spec[role]:
            file = scoped(root, relative)
            require(not file.is_relative_to(out.resolve()), "source inside OUTDIR")
            identity = (file.stat().st_dev, file.stat().st_ino)
            require(identity not in identities, "source roles contain aliased files")
            identities.add(identity)
            records.append(source_record(root / relative))
    for record in records:
        check_source(record)
    out.mkdir(parents=True, exist_ok=False)
    (out / ".controller").mkdir(mode=0o700)
    manifest = {"schema_version": "review-handoff-controller.v1",
                "project_root": str(root), "issues": issues,
                "roles": {role: spec[role] for role in roles}, "sources": records,
                "scope": SCOPE}
    write_new(out / ".controller/manifest.json", encoded(manifest))
    write_new(out / "stage1/packet.json", encoded({"stage": 1, "issues": issues,
        "task": "Freeze criteria for each issue before seeing manuscripts or responses.",
        "scope": SCOPE}))
    seal(out, 1, records, [".controller/manifest.json", "stage1/packet.json"])
    return verify(out)


def advance(outdir, result_path, stage):
    out = Path(outdir).absolute()
    state = verify(out)
    require(state["stage"] == stage - 1, "stage already exists or prerequisite missing")
    manifest = load(out / ".controller/manifest.json")
    root = Path(manifest["project_root"])
    result_path = Path(result_path).absolute()
    require(not result_path.resolve().is_relative_to(out.resolve()), "result must be outside OUTDIR")
    result_record = source_record(result_path)
    result = load(result_path)
    wanted = [issue["issue_id"] for issue in manifest["issues"]]
    if stage == 2:
        issue_records(result, "review-handoff-criteria.v1", {"issue_id", "criterion"}, wanted)
        roles = ("old", "new", "evidence")
        packet = {"stage": 2, "frozen_criteria": result,
                  "task": "Judge every issue from old/new/evidence before reading the response.",
                  "scope": SCOPE}
    else:
        issues = issue_records(result, "review-handoff-evidence.v1",
            {"issue_id", "status", "reason", "evidence_locators"}, wanted)
        allowed = {path for role in ("old", "new", "evidence") for path in manifest["roles"][role]}
        for issue in issues:
            require(issue["status"] in ("resolved", "unresolved"), "invalid evidence status")
            require(nonempty(issue["reason"]), "reason must be nonempty")
            locators = issue["evidence_locators"]
            require(isinstance(locators, list) and locators, "evidence_locators must be nonempty")
            for locator in locators:
                exact(locator, {"path", "locator"}, "evidence locator")
                require(isinstance(locator["path"], str) and locator["path"] in allowed,
                        "locator path is not a registered evidence source")
                require(nonempty(locator["locator"]), "locator must be nonempty")
        roles = ("response",)
        packet = {"stage": 3, "frozen_evidence_verdict": result,
                  "task": "Compare the response with the sealed evidence verdict; report discrepancies.",
                  "scope": SCOPE}
    # Read all payloads before mutation, then recheck inputs against their seals.
    payloads = {f"stage{stage}/result.json": encoded(result)}
    packet["files"] = {}
    for role in roles:
        packet["files"][role] = []
        for relative in manifest["roles"][role]:
            name = f"stage{stage}/files/{role}/{relative}"
            payloads[name] = scoped(root, relative).read_bytes()
            packet["files"][role].append({"source_path": relative,
                                          "packet_path": f"files/{role}/{relative}"})
    payloads[f"stage{stage}/packet.json"] = encoded(packet)
    verify(out)
    check_source(result_record)
    (out / f"stage{stage}").mkdir(exist_ok=False)
    for name, data in payloads.items():
        write_new(out / name, data)
    seal(out, stage, [result_record], list(payloads))
    return verify(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("spec", type=Path)
    prepare_parser.add_argument("outdir", type=Path)
    for name in ("criteria", "evidence"):
        child = sub.add_parser(name)
        child.add_argument("outdir", type=Path)
        child.add_argument("result", type=Path)
    for name in ("verify", "reveal"):
        sub.add_parser(name).add_argument("outdir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            report = prepare(args.spec, args.outdir)
        elif args.command in ("criteria", "evidence"):
            report = advance(args.outdir, args.result, 2 if args.command == "criteria" else 3)
        else:
            report = verify(args.outdir)
            if args.command == "reveal":
                require(report["stage"] == 3, "response remains sealed until evidence result")
                report["packet"] = str(args.outdir.absolute() / "stage3/packet.json")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc), "scope": SCOPE}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
