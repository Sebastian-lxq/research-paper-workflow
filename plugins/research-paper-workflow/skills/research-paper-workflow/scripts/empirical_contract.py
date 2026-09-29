#!/usr/bin/env python3
"""Validate hash-bound empirical result contracts; this does not establish identification."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys


CONTRACT_SCHEMA = "empirical-result-contract.v1"
STATUS_SCHEMA = "empirical-result-contract-status.v1"
# Compatibility alias for callers that imported the original constant.
SCHEMA = CONTRACT_SCHEMA
FAMILIES = {"ols-fe", "iv-gmm", "did-event-study", "rdd", "synthetic-control", "ml-prediction", "other"}
DIAGNOSTIC_STATES = {"pass", "fail", "warn", "not-applicable"}
VALIDATION_STATES = {"pass", "fail", "not-run", "not-feasible"}


class EmpiricalError(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise EmpiricalError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(
            EmpiricalError(f"invalid JSON number: {item}")
        ),
    )
    if not isinstance(value, dict):
        raise EmpiricalError("contract must be a JSON object")
    return value


def exact(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise EmpiricalError(f"{field} must contain exactly {sorted(fields)}")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise EmpiricalError(f"{field} must be nonempty text")
    return value.strip()


def identifier(value, field):
    value = text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise EmpiricalError(f"invalid {field}: {value}")
    return value


def finite(value, field, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EmpiricalError(f"{field} must be finite numeric data")
    if nonnegative and value < 0:
        raise EmpiricalError(f"{field} must be nonnegative")
    return value


def string_list(value, field, *, allow_empty=True):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise EmpiricalError(f"{field} must be an array of nonempty text")
    if not allow_empty and not value:
        raise EmpiricalError(f"{field} must not be empty")
    if len(value) != len(set(value)):
        raise EmpiricalError(f"{field} contains duplicates")
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
        or value.startswith(".paper/workflow/")
    ):
        raise EmpiricalError(f"unsafe or self-referential {field}: {value}")
    return value


def project_file(root, name):
    name = relative(name)
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise EmpiricalError(f"symlink project paths are not accepted: {name}")
    if not path.is_file() or path.stat().st_nlink != 1:
        raise EmpiricalError(f"project artifact missing or not an ordinary file: {name}")
    return path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def bound_file(root, path, expected, field):
    path = relative(path, f"{field}.path")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise EmpiricalError(f"{field}.sha256 must be lowercase SHA-256")
    observed = digest(project_file(root, path))
    if observed != expected:
        raise EmpiricalError(f"stale hash for {path}")
    return path


def evidence(root, value, field, *, role=False):
    fields = {"path", "sha256", "role"} if role else {"path", "sha256"}
    exact(value, fields, field)
    bound_file(root, value["path"], value["sha256"], field)
    if role:
        text(value["role"], f"{field}.role")
    return value


def evidence_list(root, value, field, *, nonempty=False, role=False):
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "nonempty " if nonempty else ""
        raise EmpiricalError(f"{field} must be a {qualifier}array")
    seen = set()
    for index, item in enumerate(value):
        evidence(root, item, f"{field}[{index}]", role=role)
        if item["path"] in seen:
            raise EmpiricalError(f"{field} contains duplicate path {item['path']}")
        seen.add(item["path"])
    return value


def validate(root, contract):
    exact(
        contract,
        {
            "schema", "result_id", "claim_ids", "estimand", "data", "specification",
            "adapter", "inference", "estimates", "diagnostics", "artifacts",
            "validation", "interpretation_ceiling", "failures",
        },
        "contract",
    )
    if contract["schema"] != SCHEMA:
        raise EmpiricalError(f"unsupported schema: {contract['schema']}")
    result_id = identifier(contract["result_id"], "result_id")
    string_list(contract["claim_ids"], "claim_ids", allow_empty=False)
    text(contract["estimand"], "estimand")

    data = exact(
        contract["data"],
        {"dataset_id", "version", "checksum", "sample_definition", "n_observations"},
        "data",
    )
    for name in ("dataset_id", "version", "checksum", "sample_definition"):
        text(data[name], f"data.{name}")
    if not isinstance(data["n_observations"], int) or isinstance(data["n_observations"], bool) or data["n_observations"] <= 0:
        raise EmpiricalError("data.n_observations must be a positive integer")

    specification = exact(
        contract["specification"],
        {"id", "exploratory", "plan_path", "plan_sha256", "deviations"},
        "specification",
    )
    identifier(specification["id"], "specification.id")
    if type(specification["exploratory"]) is not bool:
        raise EmpiricalError("specification.exploratory must be boolean")
    bound_file(root, specification["plan_path"], specification["plan_sha256"], "specification.plan")
    string_list(specification["deviations"], "specification.deviations")

    adapter = exact(
        contract["adapter"],
        {"family", "implementation", "version", "command", "config_path", "config_sha256", "output_path", "output_sha256"},
        "adapter",
    )
    if adapter["family"] not in FAMILIES:
        raise EmpiricalError(f"unsupported adapter.family: {adapter['family']}")
    text(adapter["implementation"], "adapter.implementation")
    text(adapter["version"], "adapter.version")
    string_list(adapter["command"], "adapter.command", allow_empty=False)
    bound_file(root, adapter["config_path"], adapter["config_sha256"], "adapter.config")
    bound_file(root, adapter["output_path"], adapter["output_sha256"], "adapter.output")

    inference = exact(
        contract["inference"],
        {"method", "cluster_unit", "confidence_level", "multiplicity", "assumptions"},
        "inference",
    )
    text(inference["method"], "inference.method")
    if inference["cluster_unit"] is not None:
        text(inference["cluster_unit"], "inference.cluster_unit")
    confidence = finite(inference["confidence_level"], "inference.confidence_level")
    if not 0 < confidence < 1:
        raise EmpiricalError("inference.confidence_level must be between zero and one")
    text(inference["multiplicity"], "inference.multiplicity")
    string_list(inference["assumptions"], "inference.assumptions", allow_empty=False)

    if not isinstance(contract["estimates"], list) or not contract["estimates"]:
        raise EmpiricalError("estimates must be a nonempty array")
    names = set()
    for index, estimate in enumerate(contract["estimates"]):
        field = f"estimates[{index}]"
        exact(estimate, {"name", "value", "standard_error", "ci_lower", "ci_upper", "units"}, field)
        name = identifier(estimate["name"], f"{field}.name")
        if name in names:
            raise EmpiricalError(f"duplicate estimate name: {name}")
        names.add(name)
        value = finite(estimate["value"], f"{field}.value")
        finite(estimate["standard_error"], f"{field}.standard_error", nonnegative=True)
        lower = finite(estimate["ci_lower"], f"{field}.ci_lower")
        upper = finite(estimate["ci_upper"], f"{field}.ci_upper")
        if lower > value or value > upper:
            raise EmpiricalError(f"{field} confidence interval must contain the estimate")
        text(estimate["units"], f"{field}.units")

    if not isinstance(contract["diagnostics"], list) or not contract["diagnostics"]:
        raise EmpiricalError("diagnostics must be a nonempty array")
    diagnostic_failures = []
    diagnostic_names = set()
    for index, diagnostic in enumerate(contract["diagnostics"]):
        field = f"diagnostics[{index}]"
        exact(diagnostic, {"name", "status", "interpretation", "evidence"}, field)
        name = identifier(diagnostic["name"], f"{field}.name")
        if name in diagnostic_names:
            raise EmpiricalError(f"duplicate diagnostic name: {name}")
        diagnostic_names.add(name)
        if diagnostic["status"] not in DIAGNOSTIC_STATES:
            raise EmpiricalError(f"unsupported {field}.status")
        text(diagnostic["interpretation"], f"{field}.interpretation")
        evidence_list(root, diagnostic["evidence"], f"{field}.evidence", nonempty=diagnostic["status"] != "not-applicable")
        if diagnostic["status"] == "fail":
            diagnostic_failures.append(name)

    evidence_list(root, contract["artifacts"], "artifacts", nonempty=True, role=True)
    validation = exact(
        contract["validation"],
        {"known_answer", "independent_comparison", "warnings_reviewed"},
        "validation",
    )
    if type(validation["warnings_reviewed"]) is not bool:
        raise EmpiricalError("validation.warnings_reviewed must be boolean")
    validation_reports = {}
    for name in ("known_answer", "independent_comparison"):
        item = exact(validation[name], {"status", "note", "evidence"}, f"validation.{name}")
        if item["status"] not in VALIDATION_STATES:
            raise EmpiricalError(f"unsupported validation.{name}.status")
        text(item["note"], f"validation.{name}.note")
        evidence_list(root, item["evidence"], f"validation.{name}.evidence", nonempty=item["status"] == "pass")
        validation_reports[name] = item["status"]

    text(contract["interpretation_ceiling"], "interpretation_ceiling")
    string_list(contract["failures"], "failures")
    blockers = []
    if diagnostic_failures:
        blockers.append(f"failed diagnostics: {diagnostic_failures}")
    if validation_reports["known_answer"] != "pass":
        blockers.append("known-answer fixture has not passed")
    if validation_reports["independent_comparison"] not in {"pass", "not-feasible"}:
        blockers.append("independent comparison is unresolved")
    if not validation["warnings_reviewed"]:
        blockers.append("runtime warnings have not been reviewed")
    if contract["failures"]:
        blockers.append("unresolved execution failures remain")
    return {
        "schema": STATUS_SCHEMA,
        "result_id": result_id,
        "valid": True,
        "release_eligible": not blockers,
        "blockers": blockers,
        "diagnostic_failures": diagnostic_failures,
        "scientific_certification": "not-established-by-this-tool",
        "identification_established": False,
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
            raise EmpiricalError("--project must name an existing absolute ordinary directory")
        root = root.resolve()
        record = Path(args.record)
        if not record.is_absolute():
            record = root / record
        record = record.resolve()
        if not record.is_relative_to(root) or record.is_symlink() or not record.is_file():
            raise EmpiricalError("--record must name an ordinary project file")
        result = validate(root, load(record))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if result["release_eligible"] else 1
    except (OSError, EmpiricalError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
