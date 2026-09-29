#!/usr/bin/env python3
"""Validate idea portfolios and search frontiers without certifying novelty."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys


PORTFOLIO_SCHEMA = "research-idea-portfolio.v1"
STATUS_SCHEMA = "research-idea-portfolio-status.v1"
# Compatibility alias for callers that imported the original constant.
SCHEMA = PORTFOLIO_SCHEMA
STATUSES = {"active", "parked", "rejected", "selected"}
VERDICTS = {"recommend", "investigate", "park", "reject"}
PROBE_OUTCOMES = {"not-run", "survived", "falsified", "inconclusive"}
QUERY_MODES = {"targeted", "deanchored"}
COVERAGE_KINDS = {
    "named-method",
    "functional-deanchored",
    "citation-graph",
    "version-lineage",
    "direct-implication",
    "component-composition",
    "cross-domain",
    "contradictory-evidence",
}
COVERAGE_STATES = {"checked", "open", "not-applicable"}
STOP_STATES = {"continue", "stop"}


class PortfolioError(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise PortfolioError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda item: (_ for _ in ()).throw(
                PortfolioError(f"invalid JSON number: {item}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise PortfolioError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PortfolioError("portfolio must be a JSON object")
    return value


def exact(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise PortfolioError(f"{name} must contain exactly {sorted(fields)}")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise PortfolioError(f"{field} must be nonempty text")
    return value.strip()


def identifier(value, field="id"):
    value = text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise PortfolioError(f"invalid {field}: {value}")
    return value


def string_list(value, field, *, allow_empty=True):
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise PortfolioError(f"{field} must be an array of nonempty text")
    if not allow_empty and not value:
        raise PortfolioError(f"{field} must not be empty")
    if len(value) != len(set(value)):
        raise PortfolioError(f"{field} contains duplicates")
    return value


def relative(value, field="path"):
    value = text(value, field)
    part = PurePosixPath(value)
    if (
        part.is_absolute()
        or part.as_posix() != value
        or "\\" in value
        or value == "."
        or any(piece in {"", ".", ".."} for piece in part.parts)
    ):
        raise PortfolioError(f"unsafe {field}: {value}")
    return value


def project_path(root, name):
    name = relative(name)
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise PortfolioError(f"symlink project paths are not accepted: {name}")
    if not path.is_file() or path.stat().st_nlink != 1:
        raise PortfolioError(f"project artifact missing or not an ordinary file: {name}")
    return path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def evidence_ref(value, field, root):
    exact(value, {"path", "sha256"}, field)
    path = project_path(root, value["path"])
    observed = digest(path)
    if not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise PortfolioError(f"{field}.sha256 must be lowercase SHA-256")
    if observed != value["sha256"]:
        raise PortfolioError(f"stale evidence hash for {value['path']}")
    return value


def evidence_list(value, field, root, *, allow_empty=True):
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "nonempty " if not allow_empty else ""
        raise PortfolioError(f"{field} must be a {qualifier}array")
    seen = set()
    for index, item in enumerate(value):
        evidence_ref(item, f"{field}[{index}]", root)
        if item["path"] in seen:
            raise PortfolioError(f"{field} contains duplicate path {item['path']}")
        seen.add(item["path"])
    return value


def iso_date(value, field):
    value = text(value, field)
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise PortfolioError(f"{field} must be YYYY-MM-DD") from exc
    return value


def usage(value, field):
    exact(value, {"wall_minutes", "cost_usd", "compute_hours", "source"}, field)
    for name in ("wall_minutes", "cost_usd", "compute_hours"):
        item = value[name]
        if item is not None and (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(item)
            or item < 0
        ):
            raise PortfolioError(f"{field}.{name} must be null or finite and nonnegative")
    if all(value[name] is None for name in ("wall_minutes", "cost_usd", "compute_hours")):
        if value["source"] is not None:
            text(value["source"], f"{field}.source")
    else:
        text(value["source"], f"{field}.source")
    return value


def formation(value, field):
    exact(value, {"sources", "operations", "results", "templates"}, field)
    specs = {
        "sources": (r"S(?:[0-6])", False),
        "operations": (r"O(?:[0-9])", False),
        "results": (r"R(?:[0-6])", False),
        "templates": (r"F(?:10|[1-9])", True),
    }
    for name, (pattern, may_be_empty) in specs.items():
        entries = string_list(value[name], f"{field}.{name}", allow_empty=may_be_empty)
        for entry in entries:
            if not re.fullmatch(pattern, entry):
                raise PortfolioError(f"invalid formation code {entry} in {field}.{name}")
    return value


def validate_candidate(candidate, root):
    fields = {
        "id", "record_locator", "formation", "contribution", "status",
        "probe", "search", "decision", "budget",
    }
    exact(candidate, fields, "candidate")
    cid = identifier(candidate["id"], "candidate id")
    text(candidate["record_locator"], f"{cid}.record_locator")
    formation(candidate["formation"], f"{cid}.formation")
    contribution = exact(
        candidate["contribution"],
        {"object_information", "target", "conditions", "procedure", "new_capability"},
        f"{cid}.contribution",
    )
    for name, value in contribution.items():
        text(value, f"{cid}.contribution.{name}")
    if candidate["status"] not in STATUSES:
        raise PortfolioError(f"unsupported {cid}.status")

    probe = exact(
        candidate["probe"], {"question", "criterion", "outcome", "evidence"}, f"{cid}.probe"
    )
    text(probe["question"], f"{cid}.probe.question")
    text(probe["criterion"], f"{cid}.probe.criterion")
    if probe["outcome"] not in PROBE_OUTCOMES:
        raise PortfolioError(f"unsupported {cid}.probe.outcome")
    evidence_list(probe["evidence"], f"{cid}.probe.evidence", root)
    if probe["outcome"] != "not-run" and not probe["evidence"]:
        raise PortfolioError(f"{cid}.probe.evidence is required for an observed outcome")

    search = exact(
        candidate["search"],
        {"queries", "coverage_paths", "nearest_neighbors", "stop"},
        f"{cid}.search",
    )
    if not isinstance(search["queries"], list):
        raise PortfolioError(f"{cid}.search.queries must be an array")
    query_ids, query_modes = set(), set()
    for index, query in enumerate(search["queries"]):
        qfield = f"{cid}.search.queries[{index}]"
        exact(query, {"id", "mode", "query", "sources", "run_at", "records_checked", "outcome"}, qfield)
        qid = identifier(query["id"], f"{qfield}.id")
        if qid in query_ids:
            raise PortfolioError(f"duplicate query id {qid} for {cid}")
        query_ids.add(qid)
        if query["mode"] not in QUERY_MODES:
            raise PortfolioError(f"unsupported {qfield}.mode")
        query_modes.add(query["mode"])
        text(query["query"], f"{qfield}.query")
        string_list(query["sources"], f"{qfield}.sources", allow_empty=False)
        iso_date(query["run_at"], f"{qfield}.run_at")
        if not isinstance(query["records_checked"], int) or isinstance(query["records_checked"], bool) or query["records_checked"] < 0:
            raise PortfolioError(f"{qfield}.records_checked must be a nonnegative integer")
        text(query["outcome"], f"{qfield}.outcome")

    if not isinstance(search["coverage_paths"], list):
        raise PortfolioError(f"{cid}.search.coverage_paths must be an array")
    coverage = {}
    for index, item in enumerate(search["coverage_paths"]):
        pfield = f"{cid}.search.coverage_paths[{index}]"
        exact(item, {"kind", "state", "material", "reason", "evidence"}, pfield)
        if item["kind"] not in COVERAGE_KINDS or item["kind"] in coverage:
            raise PortfolioError(f"invalid or duplicate {pfield}.kind")
        if item["state"] not in COVERAGE_STATES or type(item["material"]) is not bool:
            raise PortfolioError(f"invalid state or material flag in {pfield}")
        text(item["reason"], f"{pfield}.reason")
        evidence_list(item["evidence"], f"{pfield}.evidence", root)
        if item["state"] == "checked" and not item["evidence"]:
            raise PortfolioError(f"checked {pfield} requires evidence")
        coverage[item["kind"]] = item

    if not isinstance(search["nearest_neighbors"], list):
        raise PortfolioError(f"{cid}.search.nearest_neighbors must be an array")
    neighbor_ids = set()
    for index, neighbor in enumerate(search["nearest_neighbors"]):
        nfield = f"{cid}.search.nearest_neighbors[{index}]"
        exact(neighbor, {"id", "source", "version", "locator", "role", "comparison", "evidence"}, nfield)
        nid = identifier(neighbor["id"], f"{nfield}.id")
        if nid in neighbor_ids:
            raise PortfolioError(f"duplicate nearest-neighbor id {nid} for {cid}")
        neighbor_ids.add(nid)
        for name in ("source", "version", "locator", "role", "comparison"):
            text(neighbor[name], f"{nfield}.{name}")
        evidence_list(neighbor["evidence"], f"{nfield}.evidence", root, allow_empty=False)

    stop = exact(search["stop"], {"status", "reason", "unresolved_material_paths"}, f"{cid}.search.stop")
    if stop["status"] not in STOP_STATES:
        raise PortfolioError(f"unsupported {cid}.search.stop.status")
    text(stop["reason"], f"{cid}.search.stop.reason")
    unresolved = string_list(stop["unresolved_material_paths"], f"{cid}.search.stop.unresolved_material_paths")
    unknown = set(unresolved) - set(coverage)
    if unknown:
        raise PortfolioError(f"{cid}.search.stop names unknown coverage paths: {sorted(unknown)}")
    actual_open = {kind for kind, item in coverage.items() if item["material"] and item["state"] == "open"}
    if set(unresolved) != actual_open:
        raise PortfolioError(f"{cid}.search.stop unresolved paths do not match material open paths")

    decision = exact(candidate["decision"], {"verdict", "reason", "evidence", "reopen_if"}, f"{cid}.decision")
    if decision["verdict"] not in VERDICTS:
        raise PortfolioError(f"unsupported {cid}.decision.verdict")
    text(decision["reason"], f"{cid}.decision.reason")
    evidence_list(decision["evidence"], f"{cid}.decision.evidence", root)
    string_list(decision["reopen_if"], f"{cid}.decision.reopen_if")
    budget = exact(candidate["budget"], {"planned", "actual"}, f"{cid}.budget")
    usage(budget["planned"], f"{cid}.budget.planned")
    usage(budget["actual"], f"{cid}.budget.actual")

    blockers = []
    expected_verdict = {
        "active": "investigate",
        "parked": "park",
        "rejected": "reject",
        "selected": "recommend",
    }[candidate["status"]]
    if decision["verdict"] != expected_verdict:
        blockers.append(
            f"status {candidate['status']} is inconsistent with verdict {decision['verdict']}"
        )
    if candidate["status"] == "selected":
        if probe["outcome"] != "survived":
            blockers.append("selected candidate has not survived its discriminating probe")
        if not probe["evidence"] or not decision["evidence"]:
            blockers.append("selected candidate lacks probe or decision evidence")
        if not {"targeted", "deanchored"}.issubset(query_modes):
            blockers.append("selected candidate lacks targeted and deanchored executed queries")
        if not search["nearest_neighbors"]:
            blockers.append("selected candidate has no verified nearest neighbor")
        missing_paths = COVERAGE_KINDS - set(coverage)
        if missing_paths:
            blockers.append(f"selected candidate lacks coverage paths: {sorted(missing_paths)}")
        for required in ("functional-deanchored", "version-lineage", "direct-implication"):
            if required in coverage and coverage[required]["state"] != "checked":
                blockers.append(f"selected candidate has not checked {required}")
        if actual_open or stop["status"] != "stop":
            blockers.append("selected candidate has an open material frontier or no stop decision")
    if candidate["status"] in {"parked", "rejected"} and not decision["reopen_if"]:
        blockers.append("parked/rejected candidate has no evidence-based reopen condition")
    return {
        "id": cid,
        "status": candidate["status"],
        "verdict": decision["verdict"],
        "blockers": blockers,
        "query_modes": sorted(query_modes),
        "material_open_paths": sorted(actual_open),
        "formation_signature": "+".join(candidate["formation"]["operations"] + candidate["formation"]["results"]),
    }


def validate(root, record):
    exact(record, {"schema", "as_of", "record", "candidates"}, "portfolio")
    if record["schema"] != SCHEMA:
        raise PortfolioError(f"unsupported schema: {record['schema']}")
    iso_date(record["as_of"], "as_of")
    evidence_ref(record["record"], "record", root)
    if not isinstance(record["candidates"], list) or not record["candidates"]:
        raise PortfolioError("candidates must be a nonempty array")
    reports = [validate_candidate(candidate, root) for candidate in record["candidates"]]
    ids = [report["id"] for report in reports]
    if len(ids) != len(set(ids)):
        raise PortfolioError("candidate ids must be unique")
    selected = [report for report in reports if report["status"] == "selected"]
    if len(selected) > 1:
        raise PortfolioError("at most one candidate may be selected")
    signatures = {report["formation_signature"] for report in reports}
    blockers = [f"{report['id']}: {item}" for report in reports for item in report["blockers"]]
    active = [report["id"] for report in reports if report["status"] == "active"]
    if selected and active:
        blockers.append(
            f"selected candidate coexists with unresolved active candidates: {active}"
        )
    return {
        "schema": STATUS_SCHEMA,
        "valid": True,
        "candidate_count": len(reports),
        "selected": [item["id"] for item in selected],
        "recommendation_eligible": bool(selected) and not blockers,
        "blockers": blockers,
        "coverage": reports,
        "diversity": {
            "distinct_formation_signatures": len(signatures),
            "advisory": "Generate independent mechanisms when useful; diversity is not a scientific score.",
        },
        "scientific_certification": "not-established-by-this-tool",
        "novelty_guarantee": False,
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
            raise PortfolioError("--project must name an existing absolute ordinary directory")
        root = root.resolve()
        path = Path(args.record)
        if not path.is_absolute():
            path = project_path(root, args.record)
        elif not path.resolve().is_relative_to(root):
            raise PortfolioError("--record must be inside the project")
        path = path.resolve()
        if path.is_symlink() or not path.is_file():
            raise PortfolioError("--record must name an ordinary project file")
        result = validate(root, load_json(path))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if result["recommendation_eligible"] else 1
    except (OSError, PortfolioError, KeyError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
