#!/usr/bin/env python3
"""Continuous paper-revision controller; orchestration state is not scientific proof."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


CYCLE_SCHEMA = "paper-revision-cycle.v1"
CONTRACT_SCHEMA_V1 = "paper-revision-contract.v1"
CONTRACT_SCHEMA_V2 = "paper-revision-contract.v2"
# Backward-compatible import name; all newly initialized cycles use v2.
CONTRACT_SCHEMA = CONTRACT_SCHEMA_V2
ISSUES_SCHEMA = "paper-revision-issues.v1"
ISSUES_SCHEMA_V2 = "paper-revision-issues.v2"
EVENT_SCHEMA = "paper-revision-event.v1"
REVIEW_SCHEMA = "paper-revision-review.v1"
RETROSPECTIVE_SCHEMA = "paper-revision-retrospective.v1"
NON_REGRESSION_REPORT_SCHEMA = "paper-non-regression-report.v1"

TARGET = "manuscript-ready-for-author-review"
SEVERITIES = ("P0", "P1", "P2", "P3")
SEVERITY_ORDER = {value: index for index, value in enumerate(SEVERITIES)}
AREAS = {
    "research-positioning",
    "theory",
    "method",
    "simulation",
    "empirical",
    "notation",
    "writing",
    "integration",
}
ISSUE_STATUSES = {
    "queued",
    "active",
    "verifying",
    "blocked_author",
    "accepted",
    "deferred",
}
FINAL_ISSUE_STATUSES = {"accepted", "deferred"}
SOURCE_KINDS = {
    "direct-user",
    "user-relayed-mentor",
    "publication",
    "independent-review",
    "workflow-audit",
}
CAUSES = {
    "skill-gap",
    "execution-miss",
    "tool-failure",
    "input-insufficient",
    "scientific-unknown",
}
ADMISSION_BASES = {
    "direct-user",
    "dependency",
    "release-requirement",
    "material-research-effect",
}
AUTHORIZED_OPERATIONS = {
    "edit-manuscript",
    "edit-proof",
    "edit-simulation-code",
    "run-local-compute",
    "update-project-state",
}
PAUSE_CODES = {
    "research-target-change",
    "evidence-insufficient-choice",
    "compute-budget-exceeded",
    "external-or-confidentiality-change",
    "external-action",
    "repeated-blocker",
    "expert-panel-reconfirmation",
}
STOP_CONDITIONS = [
    "no-open-p0-p1",
    "required-workflow-stages-ready",
    "current-artifacts-bound",
    "two-independent-clean-reviews",
    "p2-p3-closed-or-deferred",
]
PAUSE_CONDITIONS = [
    "research-target-change",
    "evidence-insufficient-choice",
    "compute-budget-exceeded",
    "external-or-confidentiality-change",
    "external-action",
    "repeated-blocker",
]


class CycleError(ValueError):
    pass


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise CycleError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_text(value):
    return json.loads(
        value,
        object_pairs_hook=pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(
            CycleError(f"invalid JSON number: {item}")
        ),
    )


def load_json(path):
    value = parse_text(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CycleError(f"{path} must contain a JSON object")
    return value


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise CycleError(f"{field} must be nonempty text")
    return value.strip()


def identifier(value, field="identifier"):
    value = nonempty(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise CycleError(f"invalid {field}: {value}")
    return value


def string_list(value, field, *, nonempty_list=False, unique=True):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise CycleError(f"{field} must be an array of nonempty text")
    if nonempty_list and not value:
        raise CycleError(f"{field} must not be empty")
    if unique and len(value) != len(set(value)):
        raise CycleError(f"{field} contains duplicates")
    return value


def relative(value, field="path"):
    value = nonempty(value, field)
    part = PurePosixPath(value)
    if (
        part.is_absolute()
        or part.as_posix() != value
        or "\\" in value
        or value == "."
        or any(piece in {"", ".", ".."} for piece in part.parts)
    ):
        raise CycleError(f"unsafe {field}: {value}")
    return value


def safe_path(root, name, *, must_exist=False, ordinary=True):
    name = relative(name)
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise CycleError(f"symlinks are not allowed: {name}")
    if must_exist and not path.exists():
        raise CycleError(f"required project file is missing: {name}")
    if must_exist and ordinary and (not path.is_file() or path.stat().st_nlink != 1):
        raise CycleError(f"project input must be an ordinary single-link file: {name}")
    return path


def snapshot(root, name):
    name = relative(name)
    path = safe_path(root, name, must_exist=True)
    return {"path": name, "sha256": file_digest(path), "size": path.stat().st_size}


def atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def workflow_module():
    path = Path(__file__).resolve().with_name("workflow_state.py")
    spec = importlib.util.spec_from_file_location("revision_cycle_workflow_state", path)
    if spec is None or spec.loader is None:
        raise CycleError("cannot load workflow_state.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_root(value):
    root = Path(value)
    if not root.is_absolute() or not root.is_dir():
        raise CycleError("--project must name an existing absolute project directory")
    return root.resolve()


def paths(root):
    folder = safe_path(root, ".paper/workflow", must_exist=True, ordinary=False)
    if not folder.is_dir() or folder.is_symlink():
        raise CycleError(".paper/workflow must be an existing ordinary directory")
    ledger = safe_path(root, ".paper/revisions.yaml", must_exist=True)
    state = safe_path(root, ".paper/workflow/revision-cycle.json")
    lock = safe_path(root, ".paper/workflow/.revision-cycle.lock")
    return ledger, state, lock


def validate_non_regression_contract(spec):
    required = {
        "primary_objectives",
        "protected_invariants",
        "allowed_tradeoffs",
        "paired_evidence_requirements",
        "rollback",
        "whole_candidate_dimensions",
        "report_path",
    }
    if not isinstance(spec, dict) or set(spec) != required:
        raise CycleError(f"non_regression must contain exactly {sorted(required)}")

    def rows(field, expected, *, required_rows):
        value = spec[field]
        if not isinstance(value, list) or (required_rows and not value):
            qualifier = "nonempty " if required_rows else ""
            raise CycleError(f"non_regression {field} must be a {qualifier}array")
        ids = []
        for row in value:
            if not isinstance(row, dict) or set(row) != expected:
                raise CycleError(f"non_regression {field} entries must contain exactly {sorted(expected)}")
            ids.append(identifier(row["id"], f"{field} id"))
            for key in expected - {"id"}:
                nonempty(row[key], f"{field} {key}")
        if len(ids) != len(set(ids)):
            raise CycleError(f"non_regression {field} contains duplicate ids")

    rows(
        "primary_objectives",
        {"id", "description", "baseline_locator", "improvement_criterion"},
        required_rows=True,
    )
    rows(
        "protected_invariants",
        {"id", "description", "baseline_locator", "preservation_check"},
        required_rows=True,
    )
    rows(
        "allowed_tradeoffs",
        {"id", "benefit", "allowed_cost", "bound", "evidence_requirement"},
        required_rows=False,
    )
    rows(
        "paired_evidence_requirements",
        {"id", "baseline_locator", "candidate_locator", "criterion"},
        required_rows=True,
    )
    rollback = spec["rollback"]
    expected_rollback = {"trigger_conditions", "restore_locator", "required_action"}
    if not isinstance(rollback, dict) or set(rollback) != expected_rollback:
        raise CycleError(f"non_regression rollback must contain exactly {sorted(expected_rollback)}")
    string_list(rollback["trigger_conditions"], "rollback trigger_conditions", nonempty_list=True, unique=False)
    nonempty(rollback["restore_locator"], "rollback restore_locator")
    if rollback["required_action"] not in {"rework", "restore", "pause-author"}:
        raise CycleError("rollback required_action must be rework, restore or pause-author")
    dimensions = string_list(
        spec["whole_candidate_dimensions"],
        "whole_candidate_dimensions",
        nonempty_list=True,
    )
    if set(dimensions) - AREAS:
        raise CycleError("whole_candidate_dimensions contains an unknown review area")
    spec["report_path"] = relative(spec["report_path"], "non_regression report_path")
    return spec


def validate_contract(contract, root, *, allow_legacy=True):
    required = {
        "schema",
        "cycle_id",
        "mode",
        "objective",
        "manuscript",
        "scope",
        "resources",
        "confidentiality",
        "target",
        "expert_authorization",
        "stop_conditions",
        "pause_conditions",
    }
    schema = contract.get("schema") if isinstance(contract, dict) else None
    if schema == CONTRACT_SCHEMA_V2:
        required = required | {"non_regression"}
    if not isinstance(contract, dict) or set(contract) != required:
        raise CycleError(f"contract must contain exactly {sorted(required)}")
    if schema not in {CONTRACT_SCHEMA_V1, CONTRACT_SCHEMA_V2} or contract["mode"] != "continuous-revision":
        raise CycleError("unsupported revision contract schema or mode")
    if not allow_legacy and schema != CONTRACT_SCHEMA_V2:
        raise CycleError("new revision cycles require paper-revision-contract.v2")
    identifier(contract["cycle_id"], "cycle_id")
    nonempty(contract["objective"], "objective")
    if contract["target"] != TARGET:
        raise CycleError(f"continuous revision target must be {TARGET}")
    if contract["stop_conditions"] != STOP_CONDITIONS:
        raise CycleError("contract stop_conditions must use the frozen conditions")
    if contract["pause_conditions"] != PAUSE_CONDITIONS:
        raise CycleError("contract pause_conditions must use the frozen conditions")

    manuscript = contract["manuscript"]
    if not isinstance(manuscript, dict) or set(manuscript) != {"path", "version"}:
        raise CycleError("manuscript must contain path and version")
    manuscript["path"] = relative(manuscript["path"], "manuscript path")
    nonempty(manuscript["version"], "manuscript version")
    safe_path(root, manuscript["path"], must_exist=True)

    scope = contract["scope"]
    if not isinstance(scope, dict) or set(scope) != {"allowed_paths", "locked_paths", "authorized_operations"}:
        raise CycleError("scope must contain allowed_paths, locked_paths and authorized_operations")
    allowed = string_list(scope["allowed_paths"], "allowed_paths", nonempty_list=True)
    locked = string_list(scope["locked_paths"], "locked_paths")
    for item in allowed + locked:
        relative(item, "scope path")
    if not any(
        manuscript["path"] == item or manuscript["path"].startswith(item.rstrip("/") + "/")
        for item in allowed
    ):
        raise CycleError("active manuscript is outside allowed_paths")
    operations = string_list(scope["authorized_operations"], "authorized_operations", nonempty_list=True)
    if set(operations) - AUTHORIZED_OPERATIONS:
        raise CycleError("contract contains an unsupported authorized operation")

    resources = contract["resources"]
    if not isinstance(resources, dict) or set(resources) != {"compute_limit", "data_access", "external_access"}:
        raise CycleError("resources must contain compute_limit, data_access and external_access")
    nonempty(resources["compute_limit"], "compute_limit")
    string_list(resources["data_access"], "data_access")
    if type(resources["external_access"]) is not bool:
        raise CycleError("external_access must be boolean")
    if contract["confidentiality"] not in {"local-only", "approved-external"}:
        raise CycleError("unknown confidentiality mode")
    if contract["confidentiality"] == "local-only" and resources["external_access"]:
        raise CycleError("local-only confidentiality conflicts with external_access")

    expert = contract["expert_authorization"]
    expected = {"status", "primary", "roundtable_members", "source_locator", "one_round_per_issue"}
    if not isinstance(expert, dict) or set(expert) != expected:
        raise CycleError(f"expert_authorization must contain exactly {sorted(expected)}")
    if expert["status"] not in {"confirmed", "disabled"}:
        raise CycleError("expert_authorization status must be confirmed or disabled")
    if expert["status"] == "confirmed":
        primary = identifier(expert["primary"], "primary expert")
        members = string_list(expert["roundtable_members"], "roundtable_members", nonempty_list=True)
        if len(members) > 3 or any(identifier(x, "roundtable member") != x for x in members):
            raise CycleError("roundtable must freeze one to three named members")
        if primary not in members:
            raise CycleError("primary expert must be included in roundtable_members")
        nonempty(expert["source_locator"], "expert authorization source_locator")
        if expert["one_round_per_issue"] is not True:
            raise CycleError("expert authorization is limited to one round per issue")
    elif expert["primary"] is not None or expert["roundtable_members"] != []:
        raise CycleError("disabled expert authorization cannot name a panel")
    if schema == CONTRACT_SCHEMA_V2:
        validate_non_regression_contract(contract["non_regression"])
    return contract


def validate_evidence_snapshots(value, root, field):
    if not isinstance(value, list) or not value:
        raise CycleError(f"{field} evidence must be a nonempty array")
    seen = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise CycleError(f"{field} evidence entries must contain path and sha256")
        path = relative(item["path"], f"{field} evidence path")
        if path in seen:
            raise CycleError(f"{field} evidence contains duplicate paths")
        seen.add(path)
        if not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"])):
            raise CycleError(f"{field} evidence sha256 is invalid")
        actual = file_digest(safe_path(root, path, must_exist=True))
        if actual != item["sha256"]:
            raise CycleError(f"{field} evidence is stale: {path}")


def validate_non_regression_report(report, root, contract, current_manuscript):
    required = {
        "schema",
        "contract_sha256",
        "candidate_sha256",
        "objectives",
        "invariants",
        "tradeoffs",
        "paired_evidence",
        "whole_candidate",
        "decision",
    }
    if not isinstance(report, dict) or set(report) != required:
        raise CycleError(f"non-regression report must contain exactly {sorted(required)}")
    if report["schema"] != NON_REGRESSION_REPORT_SCHEMA:
        raise CycleError("unsupported non-regression report schema")
    if report["contract_sha256"] != digest(contract):
        raise CycleError("non-regression report is not bound to the frozen contract")
    if report["candidate_sha256"] != current_manuscript["sha256"]:
        raise CycleError("non-regression report is not bound to the current manuscript")
    spec = contract["non_regression"]

    def result_rows(field, expected_ids, allowed_statuses, passing_status, *, key="id"):
        value = report[field]
        if not isinstance(value, list):
            raise CycleError(f"non-regression report {field} must be an array")
        actual_ids = []
        passed = True
        for row in value:
            if not isinstance(row, dict) or set(row) != {key, "status", "evidence"}:
                raise CycleError(f"non-regression report {field} entries have unsupported fields")
            actual_ids.append(row[key])
            if row["status"] not in allowed_statuses:
                raise CycleError(f"non-regression report {field} has an invalid status")
            validate_evidence_snapshots(row["evidence"], root, f"{field}:{row[key]}")
            passed = passed and row["status"] == passing_status
        if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_ids):
            raise CycleError(f"non-regression report {field} must cover the frozen contract exactly")
        return passed

    results = {
        "objectives_improved": result_rows(
            "objectives",
            [item["id"] for item in spec["primary_objectives"]],
            {"improved", "not-improved", "unknown"},
            "improved",
        ),
        "invariants_preserved": result_rows(
            "invariants",
            [item["id"] for item in spec["protected_invariants"]],
            {"preserved", "regressed", "unknown"},
            "preserved",
        ),
        "tradeoffs_within_bounds": result_rows(
            "tradeoffs",
            [item["id"] for item in spec["allowed_tradeoffs"]],
            {"within-bound", "exceeded", "unknown"},
            "within-bound",
        ),
        "paired_evidence_passed": result_rows(
            "paired_evidence",
            [item["id"] for item in spec["paired_evidence_requirements"]],
            {"pass", "fail", "unknown"},
            "pass",
        ),
        "whole_candidate_passed": result_rows(
            "whole_candidate",
            spec["whole_candidate_dimensions"],
            {"pass", "fail", "unknown"},
            "pass",
            key="dimension",
        ),
    }
    if report["decision"] not in {"retain", "rework", "rollback"}:
        raise CycleError("non-regression report decision is invalid")
    satisfied = report["decision"] == "retain" and all(results.values())
    return {"required": True, "satisfied": satisfied, "decision": report["decision"], "checks": results}


def non_regression_status(root, contract, current_manuscript):
    if contract["schema"] == CONTRACT_SCHEMA_V1:
        return {
            "required": False,
            "satisfied": True,
            "legacy_contract": True,
            "note": "Legacy v1 cycle remains readable; no machine-enforced non-regression report exists.",
        }
    report_path = contract["non_regression"]["report_path"]
    try:
        path = safe_path(root, report_path, must_exist=True)
        report = load_json(path)
        result = validate_non_regression_report(report, root, contract, current_manuscript)
        result["report"] = snapshot(root, report_path)
        return result
    except (OSError, ValueError, TypeError, KeyError, CycleError) as error:
        return {
            "required": True,
            "satisfied": False,
            "report_path": report_path,
            "error": str(error),
        }


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1:
        raise CycleError("revisions.yaml must be a schema_version 1 object")
    if not isinstance(ledger.get("revisions"), list) or any(not isinstance(x, dict) for x in ledger["revisions"]):
        raise CycleError("revisions.yaml revisions must be an array of objects")
    ids = [str(item.get("id", "")).strip() for item in ledger["revisions"]]
    present = [item for item in ids if item]
    if len(present) != len(set(present)):
        raise CycleError("revisions.yaml contains duplicate revision ids")
    return ledger


def load_ledger(path):
    return validate_ledger(load_json(path))


def cycle_issues(ledger, cycle_id):
    return [item for item in ledger["revisions"] if item.get("cycle_id") == cycle_id]


def validate_issue(issue, cycle_id):
    required = {
        "id",
        "cycle_id",
        "problem",
        "severity",
        "area",
        "source",
        "manuscript_version",
        "affected_objects",
        "depends_on",
        "acceptance_criteria",
        "author_gate",
        "status",
        "implementation",
        "verification",
        "reopen_if",
        "root_cause",
    }
    focus_fields = {
        "objective_link",
        "consequence_if_unresolved",
        "admission_basis",
    }
    fields = set(issue)
    if fields not in (required, required | focus_fields):
        raise CycleError(f"cycle issue {issue.get('id', '<missing>')} must contain exactly {sorted(required)}")
    identifier(issue["id"], "issue id")
    if issue["cycle_id"] != cycle_id:
        raise CycleError("issue cycle_id does not match active cycle")
    nonempty(issue["problem"], "issue problem")
    if issue["severity"] not in SEVERITIES or issue["area"] not in AREAS:
        raise CycleError("unknown issue severity or area")
    source = issue["source"]
    if not isinstance(source, dict) or set(source) != {"kind", "locator"}:
        raise CycleError("issue source must contain kind and locator")
    if source["kind"] not in SOURCE_KINDS:
        raise CycleError("unknown issue source kind")
    nonempty(source["locator"], "issue source locator")
    nonempty(issue["manuscript_version"], "manuscript_version")
    string_list(issue["affected_objects"], "affected_objects", nonempty_list=True)
    string_list(issue["depends_on"], "depends_on")
    string_list(issue["acceptance_criteria"], "acceptance_criteria", nonempty_list=True, unique=False)
    if type(issue["author_gate"]) is not bool or issue["status"] not in ISSUE_STATUSES:
        raise CycleError("invalid author_gate or issue status")
    if issue["severity"] in {"P0", "P1"} and issue["status"] == "deferred":
        raise CycleError("P0/P1 issues cannot be deferred")
    string_list(issue["reopen_if"], "reopen_if", unique=False)
    if issue["root_cause"] is not None and issue["root_cause"] not in CAUSES:
        raise CycleError("unknown root_cause")
    if focus_fields <= fields:
        nonempty(issue["objective_link"], "objective_link")
        nonempty(issue["consequence_if_unresolved"], "consequence_if_unresolved")
        if issue["admission_basis"] not in ADMISSION_BASES:
            raise CycleError("unknown admission_basis")
    implementation = issue["implementation"]
    if not isinstance(implementation, dict) or set(implementation) != {"worker_id", "locators", "attempts"}:
        raise CycleError("implementation must contain worker_id, locators and attempts")
    if implementation["worker_id"] is not None:
        identifier(implementation["worker_id"], "worker_id")
    string_list(implementation["locators"], "implementation locators")
    if not isinstance(implementation["attempts"], int) or implementation["attempts"] < 0:
        raise CycleError("implementation attempts must be a nonnegative integer")
    verification = issue["verification"]
    required_verification = {
        "review_path",
        "review_sha256",
        "verdict",
        "reviewer_id",
        "reviewer_context_id",
        "candidate_sha256",
    }
    if not isinstance(verification, dict) or set(verification) != required_verification:
        raise CycleError("verification record has unsupported fields")
    for field in required_verification:
        if verification[field] is not None and not isinstance(verification[field], str):
            raise CycleError(f"verification {field} must be text or null")
    return issue


def validate_issue_graph(items):
    by_id = {item["id"]: item for item in items}
    if len(by_id) != len(items):
        raise CycleError("cycle contains duplicate issue ids")
    for item in items:
        for dependency in item["depends_on"]:
            if dependency not in by_id:
                raise CycleError(f"issue {item['id']} depends on unknown issue {dependency}")
            if dependency == item["id"]:
                raise CycleError("an issue cannot depend on itself")
    visiting, visited = set(), set()

    def walk(issue_id):
        if issue_id in visiting:
            raise CycleError("issue dependency graph contains a cycle")
        if issue_id in visited:
            return
        visiting.add(issue_id)
        for dependency in by_id[issue_id]["depends_on"]:
            walk(dependency)
        visiting.remove(issue_id)
        visited.add(issue_id)

    for issue_id in by_id:
        walk(issue_id)
    return by_id


def validate_cycle_issues(ledger, state):
    items = cycle_issues(ledger, state["cycle_id"])
    for item in items:
        validate_issue(item, state["cycle_id"])
    by_id = validate_issue_graph(items)
    return items, by_id


def queue_order(items):
    by_id = {item["id"]: item for item in items}
    remaining = {item["id"] for item in items if item["status"] == "queued"}
    original = {item["id"]: index for index, item in enumerate(items)}
    ordered = []
    while remaining:
        ready = [
            issue_id
            for issue_id in remaining
            if not (set(by_id[issue_id]["depends_on"]) & remaining)
        ]
        if not ready:
            raise CycleError("queued issue dependency graph cannot be ordered")
        ready.sort(key=lambda item: (SEVERITY_ORDER[by_id[item]["severity"]], original[item]))
        chosen = ready[0]
        ordered.append(chosen)
        remaining.remove(chosen)
    return ordered


def validate_state(state):
    required = {
        "schema",
        "cycle_id",
        "contract",
        "contract_sha256",
        "manuscript",
        "queue",
        "active_issue_id",
        "clean_reviews",
        "escalations",
        "pause",
        "candidate_worker_ids",
        "revision_ledger_sha256",
        "created_at",
        "updated_at",
    }
    fields = set(state) if isinstance(state, dict) else set()
    if (not isinstance(state, dict) or fields not in (required, required | {"issue_schema"})
            or state.get("schema") != CYCLE_SCHEMA):
        raise CycleError("revision-cycle.json has an unsupported schema")
    if "issue_schema" in state and state["issue_schema"] != ISSUES_SCHEMA_V2:
        raise CycleError("new revision cycles must use paper-revision-issues.v2")
    identifier(state["cycle_id"], "cycle_id")
    if state["contract_sha256"] != digest(state["contract"]):
        raise CycleError("cycle contract binding is invalid")
    string_list(state["queue"], "queue")
    if state["active_issue_id"] is not None:
        identifier(state["active_issue_id"], "active_issue_id")
    if state["active_issue_id"] in state["queue"]:
        raise CycleError("active issue must not remain in the queue")
    if not isinstance(state["clean_reviews"], list) or not isinstance(state["escalations"], list):
        raise CycleError("clean_reviews and escalations must be arrays")
    string_list(state["candidate_worker_ids"], "candidate_worker_ids")
    if state["pause"] is not None and not isinstance(state["pause"], dict):
        raise CycleError("pause must be null or an object")
    return state


def load_state(path):
    return validate_state(load_json(path))


def ledger_sha(ledger):
    return hashlib.sha256(encoded(ledger)).hexdigest()


def workflow_status(root):
    try:
        module = workflow_module()
        plan, events = module.load(root, "main")
        return module.analyze(root, plan, events)
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"outcome": "invalid-state", "error": str(error), "stages": {}}


def review_snapshot_current(root, item):
    try:
        path = safe_path(root, item["path"], must_exist=True)
        return file_digest(path) == item["sha256"]
    except (OSError, CycleError):
        return False


def status_report(root, state, ledger):
    validate_contract(copy.deepcopy(state["contract"]), root)
    items, by_id = validate_cycle_issues(ledger, state)
    expected_queue = queue_order(items)
    current_manuscript = snapshot(root, state["contract"]["manuscript"]["path"])
    ledger_current = state["revision_ledger_sha256"] == file_digest(paths(root)[0])
    active = [item["id"] for item in items if item["status"] in {"active", "verifying", "blocked_author"}]
    p01_open = [item["id"] for item in items if item["severity"] in {"P0", "P1"} and item["status"] != "accepted"]
    unresolved = [
        item["id"]
        for item in items
        if (item["severity"] in {"P0", "P1"} and item["status"] != "accepted")
        or (item["severity"] in {"P2", "P3"} and item["status"] not in FINAL_ISSUE_STATUSES)
    ]
    p23_bad = [item["id"] for item in items if item["severity"] in {"P2", "P3"} and item["status"] not in FINAL_ISSUE_STATUSES]
    non_regression = non_regression_status(root, state["contract"], current_manuscript)

    clean = state["clean_reviews"][-2:]
    clean_current = (
        len(clean) == 2
        and all(item.get("candidate_sha256") == current_manuscript["sha256"] for item in clean)
        and len({item.get("reviewer_id") for item in clean}) == 2
        and len({item.get("reviewer_context_id") for item in clean}) == 2
        and not ({item.get("reviewer_id") for item in clean} & set(state["candidate_worker_ids"]))
        and all(review_snapshot_current(root, item) for item in clean)
        and (
            state["contract"]["schema"] == CONTRACT_SCHEMA_V1
            or all(
                item.get("non_regression_report_sha256")
                == non_regression.get("report", {}).get("sha256")
                for item in clean
            )
        )
    )
    workflow = workflow_status(root)
    required_stages = ("manuscript", "verification", "review", "revision", "delivery")
    workflow_ready = (
        workflow.get("outcome") in {TARGET, "submission-candidate"}
        and all(workflow.get("stages", {}).get(stage) == "ready" for stage in required_stages)
    )
    panel_status = state["contract"]["expert_authorization"]["status"]
    checks = {
        "ledger_binding_current": ledger_current,
        "queue_matches_revision_ledger": state["queue"] == expected_queue,
        "single_active_issue": len(active) <= 1 and state["active_issue_id"] == (active[0] if active else None),
        "no_open_p0_p1": not p01_open,
        "p2_p3_closed_or_deferred": not p23_bad,
        "all_cycle_issues_resolved": not unresolved,
        "manuscript_hash_current": current_manuscript == state["manuscript"],
        "non_regression_contract_satisfied": non_regression["satisfied"],
        "two_independent_clean_reviews": clean_current,
        "workflow_author_review_ready": workflow_ready,
        "not_paused": state["pause"] is None,
        "expert_authorization_frozen": panel_status in {"confirmed", "disabled"},
    }
    ready = all(checks.values())
    if ready:
        next_action = "Deliver the frozen manuscript-ready-for-author-review package and cycle summary."
    elif state["pause"] is not None:
        next_action = "Resolve the single recorded author gate, then record a resume event."
    elif active:
        next_action = f"Complete and verify active issue {active[0]}."
    elif state["queue"]:
        next_action = "Select the next dependency-ready issue."
    elif not non_regression["satisfied"]:
        next_action = "Complete the frozen before/after non-regression report for the current manuscript."
    elif not clean_current:
        next_action = "Obtain two fresh independent full-candidate reviews bound to the manuscript and non-regression report."
    elif not workflow_ready:
        next_action = "Complete the manuscript-to-delivery workflow receipts for the frozen candidate."
    else:
        next_action = "Synchronize stale cycle bindings before continuing."
    return {
        "schema": "paper-revision-cycle-status.v1",
        "cycle_id": state["cycle_id"],
        "outcome": TARGET if ready else ("paused" if state["pause"] else "in-progress"),
        "ready": ready,
        "checks": checks,
        "active_issue_id": state["active_issue_id"],
        "queue": state["queue"],
        "open_p0_p1": p01_open,
        "unresolved_issue_ids": unresolved,
        "manuscript": current_manuscript,
        "non_regression": non_regression,
        "workflow": workflow,
        "pause": state["pause"],
        "next_action": next_action,
        "scientific_certification": "not-established-by-this-controller",
    }


def persist(root, ledger, state):
    ledger_path, state_path, _ = paths(root)
    ledger_payload = encoded(ledger)
    state["revision_ledger_sha256"] = hashlib.sha256(ledger_payload).hexdigest()
    state["updated_at"] = utc_now()
    atomic(ledger_path, ledger_payload)
    atomic(state_path, encoded(state))


def mutation(root, callback, write, *, allow_stale_ledger=False):
    ledger_path, state_path, lock_path = paths(root)
    if not state_path.is_file():
        raise CycleError("revision cycle is not initialized")
    if write:
        lock_path.touch(exist_ok=True)
        with lock_path.open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            ledger = load_ledger(ledger_path)
            state = load_state(state_path)
            if not allow_stale_ledger and state["revision_ledger_sha256"] != file_digest(ledger_path):
                raise CycleError("revisions.yaml changed outside the controller; run sync first")
            result = callback(ledger, state)
            persist(root, ledger, state)
            result["written"] = True
            return result
    ledger = copy.deepcopy(load_ledger(ledger_path))
    state = copy.deepcopy(load_state(state_path))
    if not allow_stale_ledger and state["revision_ledger_sha256"] != file_digest(ledger_path):
        raise CycleError("revisions.yaml changed outside the controller; run sync first")
    result = callback(ledger, state)
    result["written"] = False
    return result


def initialize(root, contract, write):
    ledger_path, state_path, lock_path = paths(root)
    contract = validate_contract(copy.deepcopy(contract), root, allow_legacy=False)
    workflow = workflow_status(root)
    if workflow.get("outcome") == "invalid-state":
        raise CycleError(f"workflow state is not usable: {workflow.get('error', 'unknown error')}")

    def build():
        ledger = load_ledger(ledger_path)
        if cycle_issues(ledger, contract["cycle_id"]):
            raise CycleError("revisions.yaml already contains this cycle_id")
        now = utc_now()
        state = {
            "schema": CYCLE_SCHEMA,
            "cycle_id": contract["cycle_id"],
            "issue_schema": ISSUES_SCHEMA_V2,
            "contract": contract,
            "contract_sha256": digest(contract),
            "manuscript": snapshot(root, contract["manuscript"]["path"]),
            "queue": [],
            "active_issue_id": None,
            "clean_reviews": [],
            "escalations": [],
            "pause": None,
            "candidate_worker_ids": [],
            "revision_ledger_sha256": ledger_sha(ledger),
            "created_at": now,
            "updated_at": now,
        }
        return ledger, state

    if write:
        lock_path.touch(exist_ok=True)
        with lock_path.open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if state_path.exists():
                raise CycleError("revision cycle already exists; resume it instead of reinitializing")
            ledger, state = build()
            persist(root, ledger, state)
    else:
        if state_path.exists():
            raise CycleError("revision cycle already exists; resume it instead of reinitializing")
        ledger, state = build()
    return {"cycle_id": state["cycle_id"], "manuscript": state["manuscript"], "written": write}


def issue_from_input(raw, state):
    required = {
        "id",
        "problem",
        "severity",
        "area",
        "source",
        "affected_objects",
        "depends_on",
        "acceptance_criteria",
        "author_gate",
        "reopen_if",
        "root_cause",
    }
    focus_fields = {
        "objective_link",
        "consequence_if_unresolved",
        "admission_basis",
    }
    if not isinstance(raw, dict) or set(raw) not in (required, required | focus_fields):
        raise CycleError(f"new issue must contain exactly {sorted(required)} for v1 or add {sorted(focus_fields)} for v2")
    issue = {
        **copy.deepcopy(raw),
        "cycle_id": state["cycle_id"],
        "manuscript_version": state["contract"]["manuscript"]["version"],
        "status": "queued",
        "implementation": {"worker_id": None, "locators": [], "attempts": 0},
        "verification": {
            "review_path": None,
            "review_sha256": None,
            "verdict": None,
            "reviewer_id": None,
            "reviewer_context_id": None,
            "candidate_sha256": None,
        },
    }
    validate_issue(issue, state["cycle_id"])
    return issue


def add_issues(root, package, write):
    if set(package) != {"schema", "issues"} or package.get("schema") not in {ISSUES_SCHEMA, ISSUES_SCHEMA_V2}:
        raise CycleError("issue package must use paper-revision-issues.v1 or paper-revision-issues.v2")
    if not isinstance(package["issues"], list) or not package["issues"]:
        raise CycleError("issue package must contain at least one issue")
    if package["schema"] == ISSUES_SCHEMA_V2:
        required_focus = {"objective_link", "consequence_if_unresolved", "admission_basis"}
        if any(not required_focus <= set(item) for item in package["issues"] if isinstance(item, dict)):
            raise CycleError("v2 issues require objective_link, consequence_if_unresolved and admission_basis")

    def apply(ledger, state):
        if state.get("issue_schema") == ISSUES_SCHEMA_V2 and package["schema"] != ISSUES_SCHEMA_V2:
            raise CycleError("this revision cycle requires paper-revision-issues.v2")
        existing_ids = {str(item.get("id", "")) for item in ledger["revisions"]}
        new = [issue_from_input(item, state) for item in package["issues"]]
        if any(item["id"] in existing_ids for item in new):
            raise CycleError("new issue id collides with an existing revision")
        ledger["revisions"].extend(new)
        items, _ = validate_cycle_issues(ledger, state)
        state["queue"] = queue_order(items)
        state["clean_reviews"] = []
        return {"added_issue_ids": [item["id"] for item in new], "queue": state["queue"]}

    return mutation(root, apply, write)


def select_next(root, write):
    def apply(ledger, state):
        if state["pause"] is not None:
            raise CycleError("cycle is paused")
        items, by_id = validate_cycle_issues(ledger, state)
        active = [item for item in items if item["status"] in {"active", "verifying", "blocked_author"}]
        if active:
            if len(active) != 1:
                raise CycleError("multiple active cycle issues")
            return {"selected_issue_id": active[0]["id"], "already_active": True}
        ready = [
            issue_id
            for issue_id in state["queue"]
            if all(by_id[dependency]["status"] == "accepted" for dependency in by_id[issue_id]["depends_on"])
        ]
        if not ready:
            raise CycleError("no dependency-ready queued issue")
        selected = ready[0]
        by_id[selected]["status"] = "active"
        state["active_issue_id"] = selected
        state["queue"] = [item for item in state["queue"] if item != selected]
        return {"selected_issue_id": selected, "already_active": False}

    return mutation(root, apply, write)


def descendants(by_id, issue_id):
    found, frontier = set(), [issue_id]
    while frontier:
        current = frontier.pop()
        for candidate in by_id.values():
            if current in candidate["depends_on"] and candidate["id"] not in found:
                found.add(candidate["id"])
                frontier.append(candidate["id"])
    return found


def clear_verification(issue):
    issue["verification"] = {
        "review_path": None,
        "review_sha256": None,
        "verdict": None,
        "reviewer_id": None,
        "reviewer_context_id": None,
        "candidate_sha256": None,
    }


def apply_event(root, event, write):
    if event.get("schema") != EVENT_SCHEMA or not isinstance(event.get("action"), str):
        raise CycleError("event must use paper-revision-event.v1")

    def apply(ledger, state):
        items, by_id = validate_cycle_issues(ledger, state)
        action = event["action"]
        issue_id = event.get("issue_id")
        issue = by_id.get(issue_id) if issue_id is not None else None
        if issue_id is not None and issue is None:
            raise CycleError("event names an unknown cycle issue")

        if action == "implemented":
            required = {"schema", "action", "issue_id", "worker_id", "locators"}
            if set(event) != required or issue is None or issue["status"] != "active" or state["active_issue_id"] != issue_id:
                raise CycleError("implemented event must target the active issue")
            worker = identifier(event["worker_id"], "worker_id")
            locators = string_list(event["locators"], "implementation locators", nonempty_list=True)
            issue["implementation"] = {
                "worker_id": worker,
                "locators": locators,
                "attempts": issue["implementation"]["attempts"] + 1,
            }
            clear_verification(issue)
            issue["status"] = "verifying"
            state["candidate_worker_ids"] = [worker]
            state["manuscript"] = snapshot(root, state["contract"]["manuscript"]["path"])
            state["clean_reviews"] = []
            return {"issue_id": issue_id, "status": "verifying", "manuscript": state["manuscript"]}

        if action == "candidate":
            required = {"schema", "action", "worker_id", "change_locator", "material"}
            if set(event) != required or state["active_issue_id"] is not None:
                raise CycleError("candidate event requires no active issue")
            worker = identifier(event["worker_id"], "worker_id")
            nonempty(event["change_locator"], "change_locator")
            if type(event["material"]) is not bool:
                raise CycleError("material must be boolean")
            current = snapshot(root, state["contract"]["manuscript"]["path"])
            if event["material"] or current != state["manuscript"]:
                state["clean_reviews"] = []
            state["manuscript"] = current
            state["candidate_worker_ids"] = [worker]
            return {"manuscript": current, "clean_reviews_reset": not state["clean_reviews"]}

        if action == "pause":
            required = {"schema", "action", "issue_id", "reason_code", "reason", "source_locator"}
            if set(event) != required or event["reason_code"] not in PAUSE_CODES:
                raise CycleError("pause event has unsupported fields or reason_code")
            if state["pause"] is not None:
                raise CycleError("cycle is already paused")
            if event["reason_code"] == "repeated-blocker":
                if issue is None or issue["implementation"]["attempts"] < 3:
                    raise CycleError("repeated-blocker requires three recorded implementation attempts")
            nonempty(event["reason"], "pause reason")
            nonempty(event["source_locator"], "pause source_locator")
            if issue is not None and issue["status"] in {"active", "verifying"}:
                issue["status"] = "blocked_author"
            state["pause"] = {
                "reason_code": event["reason_code"],
                "reason": event["reason"],
                "issue_id": issue_id,
                "source_locator": event["source_locator"],
                "recorded_at": utc_now(),
            }
            state["clean_reviews"] = []
            return {"pause": state["pause"]}

        if action == "resume":
            required = {"schema", "action", "resolution_locator"}
            if set(event) != required or state["pause"] is None:
                raise CycleError("resume requires one recorded pause")
            nonempty(event["resolution_locator"], "resolution_locator")
            blocked_id = state["pause"].get("issue_id")
            if blocked_id is not None and by_id[blocked_id]["status"] == "blocked_author":
                by_id[blocked_id]["status"] = "active"
            state["pause"] = None
            return {"resumed": True, "active_issue_id": state["active_issue_id"]}

        if action == "defer":
            required = {"schema", "action", "issue_id", "reason", "source_locator", "nonblocking"}
            if (
                set(event) != required
                or issue is None
                or issue["severity"] in {"P0", "P1"}
                or issue["status"] not in {"queued", "active", "verifying", "blocked_author"}
            ):
                raise CycleError("only P2/P3 issues can be deferred")
            if event["nonblocking"] is not True:
                raise CycleError("deferred issue must be explicitly nonblocking")
            nonempty(event["reason"], "defer reason")
            nonempty(event["source_locator"], "defer source_locator")
            issue["status"] = "deferred"
            if state["active_issue_id"] == issue_id:
                state["active_issue_id"] = None
            state["queue"] = [item for item in state["queue"] if item != issue_id]
            state["clean_reviews"] = []
            return {"issue_id": issue_id, "status": "deferred"}

        if action == "reopen":
            required = {"schema", "action", "issue_id", "reason", "source_locator"}
            if (
                set(event) != required
                or issue is None
                or issue["status"] not in FINAL_ISSUE_STATUSES
                or state["active_issue_id"] is not None
            ):
                raise CycleError("reopen must target an accepted or deferred issue")
            nonempty(event["reason"], "reopen reason")
            nonempty(event["source_locator"], "reopen source_locator")
            reopened = {issue_id} | descendants(by_id, issue_id)
            for target in reopened:
                if by_id[target]["status"] in FINAL_ISSUE_STATUSES:
                    by_id[target]["status"] = "queued"
                    clear_verification(by_id[target])
            state["active_issue_id"] = None
            state["queue"] = queue_order(items)
            state["clean_reviews"] = []
            return {"reopened_issue_ids": sorted(reopened), "queue": state["queue"]}

        if action == "escalate":
            required = {"schema", "action", "issue_id", "packet_path"}
            if set(event) != required or issue is None or issue["severity"] not in {"P0", "P1"}:
                raise CycleError("expert escalation is limited to P0/P1 issues")
            expert = state["contract"]["expert_authorization"]
            if expert["status"] != "confirmed":
                raise CycleError("no confirmed named-expert authorization")
            if issue["implementation"]["attempts"] < 1 or issue["verification"]["verdict"] not in {"rework", "rejected"}:
                raise CycleError("escalation requires one substantive repair and adverse re-review")
            if any(item["issue_id"] == issue_id for item in state["escalations"]):
                raise CycleError("this issue already used its one expert escalation")
            packet = snapshot(root, event["packet_path"])
            record = {"issue_id": issue_id, "packet": packet, "panel": expert["roundtable_members"], "recorded_at": utc_now()}
            state["escalations"].append(record)
            return {"escalation": record}

        raise CycleError(f"unsupported event action: {action}")

    return mutation(root, apply, write)


def validate_review(review, root):
    required = {
        "schema",
        "review_id",
        "review_scope",
        "issue_id",
        "reviewer_id",
        "reviewer_context_id",
        "candidate_sha256",
        "severity",
        "locator",
        "evidence",
        "verdict",
        "next_action",
    }
    if set(review) != required or review.get("schema") != REVIEW_SCHEMA:
        raise CycleError(f"review must contain exactly {sorted(required)}")
    identifier(review["review_id"], "review_id")
    if review["review_scope"] not in {"issue", "full"}:
        raise CycleError("review_scope must be issue or full")
    if review["issue_id"] is not None:
        identifier(review["issue_id"], "issue_id")
    identifier(review["reviewer_id"], "reviewer_id")
    identifier(review["reviewer_context_id"], "reviewer_context_id")
    if not re.fullmatch(r"[0-9a-f]{64}", str(review["candidate_sha256"])):
        raise CycleError("candidate_sha256 must be a SHA-256 hex digest")
    if review["severity"] not in {"none", *SEVERITIES}:
        raise CycleError("review severity is invalid")
    nonempty(review["locator"], "review locator")
    evidence = string_list(review["evidence"], "review evidence", nonempty_list=True)
    for item in evidence:
        safe_path(root, item, must_exist=True)
    if review["verdict"] not in {"accepted", "rework", "rejected"}:
        raise CycleError("review verdict is invalid")
    if not isinstance(review["next_action"], str):
        raise CycleError("next_action must be text")
    if review["verdict"] != "accepted" and not review["next_action"].strip():
        raise CycleError("an adverse review needs a concrete next_action")
    if review["review_scope"] == "issue" and review["issue_id"] is None:
        raise CycleError("issue review requires issue_id")
    if review["review_scope"] == "full" and review["verdict"] == "accepted":
        if review["issue_id"] is not None or review["severity"] != "none":
            raise CycleError("a clean full review must have no linked issue or severity")
    if review["review_scope"] == "full" and review["verdict"] != "accepted" and review["issue_id"] is None:
        raise CycleError("an adverse full review must link a recorded issue")
    return review


def record_review(root, review_path, write):
    review_path = relative(review_path, "review path")
    review_file = safe_path(root, review_path, must_exist=True)
    review = validate_review(load_json(review_file), root)
    expected_review_sha256 = file_digest(review_file)

    def apply(ledger, state):
        if file_digest(review_file) != expected_review_sha256:
            raise CycleError("review artifact changed while it was being recorded")
        items, by_id = validate_cycle_issues(ledger, state)
        current = snapshot(root, state["contract"]["manuscript"]["path"])
        if current != state["manuscript"] or review["candidate_sha256"] != current["sha256"]:
            raise CycleError("review is not bound to the current frozen manuscript")
        if review["reviewer_id"] in state["candidate_worker_ids"]:
            raise CycleError("reviewer must be distinct from candidate workers")
        non_regression_report_sha256 = None
        if review["review_scope"] == "full" and review["verdict"] == "accepted":
            non_regression = non_regression_status(root, state["contract"], current)
            if not non_regression["satisfied"]:
                raise CycleError("a clean full review requires a satisfied non-regression report")
            if state["contract"]["schema"] == CONTRACT_SCHEMA_V2:
                report_path = state["contract"]["non_regression"]["report_path"]
                if report_path not in review["evidence"]:
                    raise CycleError("a clean full review must include the non-regression report as evidence")
                non_regression_report_sha256 = non_regression["report"]["sha256"]
        review_record = {
            "path": review_path,
            "sha256": file_digest(review_file),
            "reviewer_id": review["reviewer_id"],
            "reviewer_context_id": review["reviewer_context_id"],
            "candidate_sha256": review["candidate_sha256"],
        }
        if non_regression_report_sha256 is not None:
            review_record["non_regression_report_sha256"] = non_regression_report_sha256
        issue_id = review["issue_id"]
        if review["review_scope"] == "issue":
            if issue_id not in by_id or state["active_issue_id"] != issue_id or by_id[issue_id]["status"] != "verifying":
                raise CycleError("issue review must target the active verifying issue")
            issue = by_id[issue_id]
            issue["verification"] = {
                "review_path": review_path,
                "review_sha256": review_record["sha256"],
                "verdict": review["verdict"],
                "reviewer_id": review["reviewer_id"],
                "reviewer_context_id": review["reviewer_context_id"],
                "candidate_sha256": review["candidate_sha256"],
            }
            if review["verdict"] == "accepted":
                issue["status"] = "accepted"
                state["active_issue_id"] = None
                state["queue"] = queue_order(items)
            else:
                issue["status"] = "active"
                state["clean_reviews"] = []
            return {
                "issue_id": issue_id,
                "status": issue["status"],
                "expert_escalation_eligible": (
                    issue["severity"] in {"P0", "P1"}
                    and issue["implementation"]["attempts"] >= 1
                    and review["verdict"] in {"rework", "rejected"}
                ),
            }

        if review["verdict"] == "accepted":
            if state["active_issue_id"] is not None or any(item["status"] not in FINAL_ISSUE_STATUSES for item in items):
                raise CycleError("clean full review requires all cycle issues resolved")
            if any(item["reviewer_context_id"] == review["reviewer_context_id"] for item in state["clean_reviews"]):
                raise CycleError("full reviews require fresh reviewer contexts")
            if any(item["reviewer_id"] == review["reviewer_id"] for item in state["clean_reviews"]):
                raise CycleError("the two clean reviews require distinct reviewers")
            state["clean_reviews"].append(review_record)
            state["clean_reviews"] = state["clean_reviews"][-2:]
            return {"clean_review_count": len(state["clean_reviews"]), "review": review_record}

        if state["active_issue_id"] is not None:
            raise CycleError("full-candidate review requires no active issue")
        if issue_id not in by_id:
            raise CycleError("adverse full review must link an existing issue")
        reopened = {issue_id} | descendants(by_id, issue_id)
        for target in reopened:
            if by_id[target]["status"] in FINAL_ISSUE_STATUSES:
                by_id[target]["status"] = "queued"
                clear_verification(by_id[target])
        state["queue"] = queue_order(items)
        state["active_issue_id"] = None
        state["clean_reviews"] = []
        return {"reopened_issue_ids": sorted(reopened), "queue": state["queue"]}

    return mutation(root, apply, write)


def sync(root, write):
    def apply(ledger, state):
        items, _ = validate_cycle_issues(ledger, state)
        active = [item["id"] for item in items if item["status"] in {"active", "verifying", "blocked_author"}]
        if len(active) > 1:
            raise CycleError("cannot sync multiple active cycle issues")
        state["active_issue_id"] = active[0] if active else None
        state["queue"] = queue_order(items)
        state["clean_reviews"] = []
        return {"active_issue_id": state["active_issue_id"], "queue": state["queue"], "clean_reviews_reset": True}

    return mutation(root, apply, write, allow_stale_ledger=True)


def retrospective(root):
    ledger_path, state_path, _ = paths(root)
    ledger = load_ledger(ledger_path)
    state = load_state(state_path)
    items, _ = validate_cycle_issues(ledger, state)
    groups = {}
    for item in items:
        cause = item["root_cause"] or "unclassified"
        groups.setdefault(cause, {"issue_ids": [], "areas": set()})
        groups[cause]["issue_ids"].append(item["id"])
        groups[cause]["areas"].add(item["area"])
    patterns = [
        {
            "root_cause": cause,
            "issue_ids": values["issue_ids"],
            "areas": sorted(values["areas"]),
            "count_in_this_project": len(values["issue_ids"]),
            "global_skill_candidate": False,
            "reason": "Cross-project recurrence or a reproducible severe holdout is still required.",
        }
        for cause, values in sorted(groups.items())
    ]
    return {
        "schema": RETROSPECTIVE_SCHEMA,
        "cycle_id": state["cycle_id"],
        "project_specific_content_included": False,
        "patterns": patterns,
        "manager_handoff": {
            "required_for_global_change": True,
            "minimum_evidence": "recurrence in at least two projects, or one reproducible severe failure plus an independent holdout",
            "automatic_skill_update": False,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "select", "sync", "retrospective"):
        command = sub.add_parser(name)
        command.add_argument("--project", required=True)
        if name in {"select", "sync"}:
            command.add_argument("--write", action="store_true")
    init = sub.add_parser("init")
    init.add_argument("--project", required=True)
    init.add_argument("--contract", required=True)
    init.add_argument("--write", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("--project", required=True)
    add.add_argument("--issues", required=True)
    add.add_argument("--write", action="store_true")
    transition = sub.add_parser("transition")
    transition.add_argument("--project", required=True)
    transition.add_argument("--event", required=True)
    transition.add_argument("--write", action="store_true")
    review = sub.add_parser("review")
    review.add_argument("--project", required=True)
    review.add_argument("--review", required=True, help="Project-relative structured review artifact")
    review.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = project_root(args.project)
        if args.command == "init":
            result = initialize(root, load_json(args.contract), args.write)
        elif args.command == "add":
            result = add_issues(root, load_json(args.issues), args.write)
        elif args.command == "select":
            result = select_next(root, args.write)
        elif args.command == "transition":
            result = apply_event(root, load_json(args.event), args.write)
        elif args.command == "review":
            result = record_review(root, args.review, args.write)
        elif args.command == "sync":
            result = sync(root, args.write)
        elif args.command == "retrospective":
            result = retrospective(root)
        else:
            ledger_path, state_path, _ = paths(root)
            result = status_report(root, load_state(state_path), load_ledger(ledger_path))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "status":
            return 0 if result["ready"] else 1
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error), "outcome": "invalid-state"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
