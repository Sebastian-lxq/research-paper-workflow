#!/usr/bin/env python3
"""Audit paired token savings against frozen quality checks and file hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


SCHEMA = "research-token-evaluation.v1"
MECHANISMS = {
    "progressive-disclosure",
    "retrieval",
    "deduplication",
    "compression",
    "cache",
    "routing",
    "structured-output",
    "batching",
    "offline-execution",
    "wait-barrier",
    "parallelization",
}
FIDELITIES = {"lossless", "bounded-lossy", "execution-only"}
RUN_STATUSES = {"completed", "error"}
CHECK_STATUSES = {"pass", "fail", "unknown"}
MEASUREMENTS = {"provider-reported", "tokenizer-estimate", "unavailable"}
TOKEN_BUCKETS = ("uncached_input_tokens", "cached_input_tokens", "output_tokens")


class TokenEvaluationError(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise TokenEvaluationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(text):
    return json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(
            TokenEvaluationError(f"invalid JSON number: {item}")
        ),
    )


def exact(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise TokenEvaluationError(f"{name} must contain exactly {sorted(fields)}")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise TokenEvaluationError(f"{field} must be nonempty text")
    return value.strip()


def identifier(value, field):
    value = text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise TokenEvaluationError(f"invalid {field}: {value}")
    return value


def relative(value, field):
    value = text(value, field)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or "\\" in value
        or value == "."
        or any(part in {"", ".", ".."} for part in path.parts)
        or value.startswith(".paper/workflow/")
    ):
        raise TokenEvaluationError(f"unsafe or self-referential {field}: {value}")
    return value


def project_file(root, value, field):
    value = relative(value, field)
    path = root
    for part in PurePosixPath(value).parts:
        path /= part
        if path.is_symlink():
            raise TokenEvaluationError(f"symlink evidence is not accepted: {value}")
    if not path.is_file() or path.stat().st_nlink != 1:
        raise TokenEvaluationError(f"evidence missing or not an ordinary file: {value}")
    return value, path


def file_digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def snapshot(root, value, field):
    exact(value, {"path", "sha256", "size"}, field)
    name, path = project_file(root, value["path"], f"{field}.path")
    expected = value["sha256"]
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise TokenEvaluationError(f"{field}.sha256 must be lowercase SHA-256")
    if not isinstance(value["size"], int) or isinstance(value["size"], bool) or value["size"] < 0:
        raise TokenEvaluationError(f"{field}.size must be a nonnegative integer")
    if path.stat().st_size != value["size"] or file_digest(path) != expected:
        raise TokenEvaluationError(f"stale evidence snapshot: {name}")
    return value


def snapshot_list(root, values, field, nonempty=True):
    if not isinstance(values, list) or (nonempty and not values):
        requirement = "a nonempty array" if nonempty else "an array"
        raise TokenEvaluationError(f"{field} must be {requirement}")
    seen = set()
    for index, value in enumerate(values):
        snapshot(root, value, f"{field}[{index}]")
        if value["path"] in seen:
            raise TokenEvaluationError(f"duplicate snapshot path in {field}: {value['path']}")
        seen.add(value["path"])
    return values


def usage(value, field):
    exact(value, {*TOKEN_BUCKETS, "measurement", "accounting_key", "source"}, field)
    if value["measurement"] not in MEASUREMENTS:
        raise TokenEvaluationError(f"unsupported {field}.measurement")
    present = []
    for bucket in TOKEN_BUCKETS:
        item = value[bucket]
        if item is not None:
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise TokenEvaluationError(f"{field}.{bucket} must be null or a nonnegative integer")
            present.append(item)
    if value["measurement"] == "unavailable":
        if present or value["accounting_key"] is not None or value["source"] is not None:
            raise TokenEvaluationError(f"{field} unavailable measurement must keep counts, accounting_key, and source null")
    else:
        if len(present) != len(TOKEN_BUCKETS):
            raise TokenEvaluationError(f"{field} measured usage requires all mutually exclusive token buckets")
        identifier(value["accounting_key"], f"{field}.accounting_key")
        text(value["source"], f"{field}.source")
    return value


def check(root, value, field, protected_ids):
    exact(value, {"id", "status", "evidence"}, field)
    check_id = identifier(value["id"], f"{field}.id")
    if check_id not in protected_ids:
        raise TokenEvaluationError(f"unknown protected check: {check_id}")
    if value["status"] not in CHECK_STATUSES:
        raise TokenEvaluationError(f"unsupported {field}.status")
    snapshot_list(root, value["evidence"], f"{field}.evidence")
    return check_id


def run(root, value, field, protected_ids):
    exact(value, {"run_id", "status", "usage", "checks"}, field)
    identifier(value["run_id"], f"{field}.run_id")
    if value["status"] not in RUN_STATUSES:
        raise TokenEvaluationError(f"unsupported {field}.status")
    usage(value["usage"], f"{field}.usage")
    if not isinstance(value["checks"], list):
        raise TokenEvaluationError(f"{field}.checks must be an array")
    found = []
    for index, item in enumerate(value["checks"]):
        found.append(check(root, item, f"{field}.checks[{index}]", protected_ids))
    if len(found) != len(set(found)):
        raise TokenEvaluationError(f"{field}.checks contains duplicate ids")
    if set(found) != protected_ids:
        raise TokenEvaluationError(f"{field}.checks must cover protected checks exactly")
    if value["status"] == "error" and all(item["status"] == "pass" for item in value["checks"]):
        raise TokenEvaluationError(f"{field} error run cannot report every check as pass")
    return value


def validate(root, record):
    exact(
        record,
        {"schema", "objective", "frozen_scope", "protected_checks", "strategies", "baseline", "candidate"},
        "token evaluation",
    )
    if record["schema"] != SCHEMA:
        raise TokenEvaluationError(f"unsupported schema: {record['schema']}")
    text(record["objective"], "objective")
    exact(record["frozen_scope"], {"inputs", "rubric"}, "frozen_scope")
    snapshot_list(root, record["frozen_scope"]["inputs"], "frozen_scope.inputs")
    snapshot_list(root, record["frozen_scope"]["rubric"], "frozen_scope.rubric")

    if not isinstance(record["protected_checks"], list) or not record["protected_checks"]:
        raise TokenEvaluationError("protected_checks must be a nonempty array")
    protected_ids = set()
    for index, item in enumerate(record["protected_checks"]):
        exact(item, {"id", "description"}, f"protected_checks[{index}]")
        check_id = identifier(item["id"], f"protected_checks[{index}].id")
        if check_id in protected_ids:
            raise TokenEvaluationError(f"duplicate protected check: {check_id}")
        protected_ids.add(check_id)
        text(item["description"], f"protected_checks[{index}].description")

    if not isinstance(record["strategies"], list) or not record["strategies"]:
        raise TokenEvaluationError("strategies must be a nonempty array")
    strategy_ids = set()
    for index, item in enumerate(record["strategies"]):
        field = f"strategies[{index}]"
        exact(item, {"id", "mechanism", "scope", "fidelity", "protected_checks", "rollback_if"}, field)
        strategy_id = identifier(item["id"], f"{field}.id")
        if strategy_id in strategy_ids:
            raise TokenEvaluationError(f"duplicate strategy: {strategy_id}")
        strategy_ids.add(strategy_id)
        if item["mechanism"] not in MECHANISMS:
            raise TokenEvaluationError(f"unsupported {field}.mechanism")
        if item["fidelity"] not in FIDELITIES:
            raise TokenEvaluationError(f"unsupported {field}.fidelity")
        text(item["scope"], f"{field}.scope")
        text(item["rollback_if"], f"{field}.rollback_if")
        if not isinstance(item["protected_checks"], list):
            raise TokenEvaluationError(f"{field}.protected_checks must be an array")
        guarded = [identifier(value, f"{field}.protected_checks") for value in item["protected_checks"]]
        if len(guarded) != len(set(guarded)) or not set(guarded).issubset(protected_ids):
            raise TokenEvaluationError(f"{field}.protected_checks contains duplicates or unknown ids")
        if item["fidelity"] == "bounded-lossy" and set(guarded) != protected_ids:
            raise TokenEvaluationError(f"{field} bounded-lossy strategy must guard every protected check")

    run(root, record["baseline"], "baseline", protected_ids)
    run(root, record["candidate"], "candidate", protected_ids)
    if record["baseline"]["run_id"] == record["candidate"]["run_id"]:
        raise TokenEvaluationError("baseline and candidate require different run_id values")
    return summarize(record)


def total_tokens(run_record):
    if run_record["usage"]["measurement"] == "unavailable":
        return None
    return sum(run_record["usage"][bucket] for bucket in TOKEN_BUCKETS)


def checks_pass(run_record):
    return run_record["status"] == "completed" and all(item["status"] == "pass" for item in run_record["checks"])


def summarize(record):
    baseline_quality = checks_pass(record["baseline"])
    candidate_quality = checks_pass(record["candidate"])
    if baseline_quality and candidate_quality:
        quality = "passed"
    elif baseline_quality:
        quality = "failed"
    else:
        quality = "not-established"

    baseline_tokens = total_tokens(record["baseline"])
    candidate_tokens = total_tokens(record["candidate"])
    comparable_measurement = (
        baseline_tokens is not None
        and candidate_tokens is not None
        and record["baseline"]["usage"]["measurement"] == record["candidate"]["usage"]["measurement"]
        and record["baseline"]["usage"]["accounting_key"] == record["candidate"]["usage"]["accounting_key"]
    )
    if not comparable_measurement:
        token_change = "not-measured"
        saved = None
        ratio = None
    else:
        saved = baseline_tokens - candidate_tokens
        ratio = None if baseline_tokens == 0 else saved / baseline_tokens
        token_change = "reduced" if saved > 0 else "unchanged" if saved == 0 else "increased"

    if quality == "passed" and token_change == "reduced":
        conclusion = "measured-token-reduction-with-bounded-non-regression"
    elif quality == "failed":
        conclusion = "reject-candidate-quality-regression"
    elif token_change == "increased":
        conclusion = "reject-candidate-token-regression"
    else:
        conclusion = "optimization-not-established"
    return {
        "schema": "research-token-evaluation-status.v1",
        "valid": True,
        "quality_non_regression": quality,
        "token_change": token_change,
        "baseline_total_tokens": baseline_tokens,
        "candidate_total_tokens": candidate_tokens,
        "saved_tokens": saved,
        "saved_ratio": ratio,
        "measurement_comparable": comparable_measurement,
        "conclusion": conclusion,
        "evidence_ceiling": (
            "Applies only to the frozen inputs, rubric, protected checks, evidence snapshots, "
            "measurement basis, and two recorded runs. It does not prove general scientific quality."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--record", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise TokenEvaluationError("--project must name an existing absolute ordinary directory")
        root = root.resolve()
        record_path = Path(args.record)
        if not record_path.is_absolute():
            record_path = root / record_path
        if not record_path.resolve().is_relative_to(root) or record_path.is_symlink() or not record_path.is_file():
            raise TokenEvaluationError("--record must name an ordinary project file")
        record = parse(record_path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise TokenEvaluationError("--record must contain a JSON object")
        result = validate(root, record)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["conclusion"] == "measured-token-reduction-with-bounded-non-regression" else 1
    except (OSError, TokenEvaluationError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc), "status": "invalid"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
