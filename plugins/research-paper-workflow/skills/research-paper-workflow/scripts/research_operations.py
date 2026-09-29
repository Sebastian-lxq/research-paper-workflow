#!/usr/bin/env python3
"""Append and summarize observed research operations; unknown usage stays unknown."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


SCHEMA_V1 = "research-operation-event.v1"
SCHEMA_V2 = "research-operation-event.v2"
# Kept for callers that imported the original constant. New wait-aware records
# should use SCHEMA_V2 explicitly.
SCHEMA = SCHEMA_V1
STATES = {"started", "waiting", "succeeded", "failed", "blocked", "cancelled"}
TRANSITIONS = {
    "started": {"waiting", "succeeded", "failed", "blocked", "cancelled"},
    "waiting": {"started", "succeeded", "failed", "blocked", "cancelled"},
    "failed": {"started", "cancelled"},
    "blocked": {"started", "cancelled"},
    "succeeded": set(),
    "cancelled": set(),
}
METRICS = ("wall_seconds", "tokens", "cost_usd", "compute_seconds")
WAIT_KINDS = {"process", "thread", "batch", "scheduler", "external"}


class OperationsError(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise OperationsError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(text):
    return json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(
            OperationsError(f"invalid JSON number: {item}")
        ),
    )


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def exact(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise OperationsError(f"{name} must contain exactly {sorted(fields)}")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise OperationsError(f"{field} must be nonempty text")
    return value.strip()


def identifier(value, field):
    value = text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise OperationsError(f"invalid {field}: {value}")
    return value


def timestamp(value, field):
    value = text(value, field)
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationsError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise OperationsError(f"{field} must include a timezone")
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
        raise OperationsError(f"unsafe or self-referential {field}: {value}")
    return value


def project_file(root, name):
    name = relative(name)
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise OperationsError(f"symlink artifact is not accepted: {name}")
    if not path.is_file() or path.stat().st_nlink != 1:
        raise OperationsError(f"artifact missing or not an ordinary file: {name}")
    return path


def usage(value):
    exact(value, {*METRICS, "source"}, "usage")
    observed = False
    for name in METRICS:
        item = value[name]
        if item is not None:
            if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(item)
                or item < 0
            ):
                raise OperationsError(f"usage.{name} must be null or finite and nonnegative")
            observed = True
    if observed:
        text(value["source"], "usage.source")
    elif value["source"] is not None:
        text(value["source"], "usage.source")
    return value


def dependencies(value, field="dependencies"):
    if not isinstance(value, list):
        raise OperationsError(f"{field} must be an array")
    seen = set()
    for index, item in enumerate(value):
        operation_id = identifier(item, f"{field}[{index}]")
        if operation_id in seen:
            raise OperationsError(f"duplicate dependency: {operation_id}")
        seen.add(operation_id)
    return value


def wait_contract(value, state, field="wait"):
    if state != "waiting":
        if value is not None:
            raise OperationsError(f"{state} event cannot carry a wait contract")
        return value
    exact(
        value,
        {"kind", "handle", "resume_condition", "dependent_actions_suspended", "next_check_at"},
        field,
    )
    if value["kind"] not in WAIT_KINDS:
        raise OperationsError(f"unsupported wait kind: {value['kind']}")
    text(value["handle"], f"{field}.handle")
    text(value["resume_condition"], f"{field}.resume_condition")
    if value["dependent_actions_suspended"] is not True:
        raise OperationsError(f"{field}.dependent_actions_suspended must be true")
    if value["next_check_at"] is not None:
        timestamp(value["next_check_at"], f"{field}.next_check_at")
    return value


def schema_fields(schema, stored=False):
    fields = {
        "schema", "operation_id", "stage", "activity", "state", "recorded_at",
        "worker_id", "usage", "provider", "artifacts", "blocker", "next_action",
    }
    if schema == SCHEMA_V2:
        fields.update({"dependencies", "wait"})
    elif schema != SCHEMA_V1:
        raise OperationsError(f"unsupported schema: {schema}")
    if stored:
        fields.update({"sequence", "previous", "sha256"})
    return fields


def validate_input(root, event):
    if not isinstance(event, dict):
        raise OperationsError("operation event must be an object")
    schema = event.get("schema")
    exact(event, schema_fields(schema), "operation event")
    identifier(event["operation_id"], "operation_id")
    identifier(event["stage"], "stage")
    text(event["activity"], "activity")
    if event["state"] not in STATES:
        raise OperationsError(f"unsupported state: {event['state']}")
    if schema == SCHEMA_V1 and event["state"] == "waiting":
        raise OperationsError("waiting requires research-operation-event.v2")
    timestamp(event["recorded_at"], "recorded_at")
    identifier(event["worker_id"], "worker_id")
    usage(event["usage"])
    if schema == SCHEMA_V2:
        dependencies(event["dependencies"])
        wait_contract(event["wait"], event["state"])
    if event["provider"] is not None:
        text(event["provider"], "provider")
    if not isinstance(event["artifacts"], list):
        raise OperationsError("artifacts must be an array")
    seen = set()
    snapshots = []
    for index, item in enumerate(event["artifacts"]):
        path = relative(item, f"artifacts[{index}]")
        if path in seen:
            raise OperationsError(f"duplicate artifact path: {path}")
        seen.add(path)
        actual = project_file(root, path)
        snapshots.append({"path": path, "sha256": file_digest(actual), "size": actual.stat().st_size})
    if event["state"] in {"failed", "blocked"}:
        text(event["blocker"], "blocker")
        text(event["next_action"], "next_action")
    else:
        if event["blocker"] is not None:
            raise OperationsError(f"{event['state']} event cannot carry a blocker")
        if event["next_action"] is not None:
            text(event["next_action"], "next_action")
        if event["state"] == "waiting" and event["next_action"] is None:
            raise OperationsError("waiting event requires next_action")
    result = dict(event)
    result["artifacts"] = snapshots
    return result


def validate_stored(event):
    if not isinstance(event, dict):
        raise OperationsError("stored operation event must be an object")
    schema = event.get("schema")
    exact(event, schema_fields(schema, stored=True), "stored operation event")
    identifier(event["operation_id"], "operation_id")
    identifier(event["stage"], "stage")
    text(event["activity"], "activity")
    if event["state"] not in STATES:
        raise OperationsError(f"unsupported stored state: {event['state']}")
    if schema == SCHEMA_V1 and event["state"] == "waiting":
        raise OperationsError("stored waiting event requires research-operation-event.v2")
    timestamp(event["recorded_at"], "recorded_at")
    identifier(event["worker_id"], "worker_id")
    usage(event["usage"])
    if schema == SCHEMA_V2:
        dependencies(event["dependencies"], "stored dependencies")
        wait_contract(event["wait"], event["state"], "stored wait")
    if event["provider"] is not None:
        text(event["provider"], "provider")
    if not isinstance(event["artifacts"], list):
        raise OperationsError("stored artifacts must be an array")
    seen = set()
    for index, artifact in enumerate(event["artifacts"]):
        exact(artifact, {"path", "sha256", "size"}, f"stored artifacts[{index}]")
        path = relative(artifact["path"], f"stored artifacts[{index}].path")
        if path in seen:
            raise OperationsError(f"duplicate stored artifact path: {path}")
        seen.add(path)
        if not isinstance(artifact["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise OperationsError(f"invalid stored artifact hash: {path}")
        if not isinstance(artifact["size"], int) or isinstance(artifact["size"], bool) or artifact["size"] < 0:
            raise OperationsError(f"invalid stored artifact size: {path}")
    if event["state"] in {"failed", "blocked"}:
        text(event["blocker"], "blocker")
        text(event["next_action"], "next_action")
    elif event["blocker"] is not None:
        raise OperationsError(f"{event['state']} event cannot carry a blocker")
    elif event["next_action"] is not None:
        text(event["next_action"], "next_action")
    if event["state"] == "waiting" and event["next_action"] is None:
        raise OperationsError("stored waiting event requires next_action")
    if not isinstance(event["sequence"], int) or isinstance(event["sequence"], bool) or event["sequence"] <= 0:
        raise OperationsError("stored sequence must be a positive integer")
    if event["previous"] is not None and (
        not isinstance(event["previous"], str) or not re.fullmatch(r"[0-9a-f]{64}", event["previous"])
    ):
        raise OperationsError("stored previous must be null or lowercase SHA-256")
    if not isinstance(event["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", event["sha256"]):
        raise OperationsError("stored sha256 must be lowercase SHA-256")
    return event


def state_paths(root):
    folder = root / ".paper" / "workflow"
    if folder.exists() and (not folder.is_dir() or folder.is_symlink()):
        raise OperationsError(".paper/workflow must be an ordinary directory")
    return folder, folder / "operations.jsonl", folder / ".operations.lock"


def load(root):
    _, path, _ = state_paths(root)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise OperationsError("operations.jsonl must be an ordinary single-link file")
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        event = parse(line)
        if not isinstance(event, dict):
            raise OperationsError(f"operation event line {line_number} is not an object")
        validate_stored(event)
        body = {key: value for key, value in event.items() if key != "sha256"}
        if event.get("sha256") != digest(body):
            raise OperationsError(f"operation event hash mismatch at line {line_number}")
        if event.get("sequence") != line_number:
            raise OperationsError(f"operation sequence mismatch at line {line_number}")
        previous = events[-1]["sha256"] if events else None
        if event.get("previous") != previous:
            raise OperationsError(f"operation hash chain mismatch at line {line_number}")
        events.append(event)
    validate_lifecycles(events)
    return events


def validate_lifecycles(events):
    latest = {}
    for event in events:
        operation_id = event["operation_id"]
        if operation_id in latest:
            prior = latest[operation_id]
            for name in ("schema", "stage", "activity", "worker_id"):
                if event[name] != prior[name]:
                    raise OperationsError(f"{operation_id} changed immutable field {name}")
            if event["schema"] == SCHEMA_V2 and event["dependencies"] != prior["dependencies"]:
                raise OperationsError(f"{operation_id} changed immutable field dependencies")
            if event["state"] not in TRANSITIONS[prior["state"]]:
                raise OperationsError(
                    f"invalid transition for {operation_id}: {prior['state']} -> {event['state']}"
                )
        latest[operation_id] = event
        if event["schema"] == SCHEMA_V2:
            for dependency in event["dependencies"]:
                if dependency == operation_id:
                    raise OperationsError(f"{operation_id} cannot depend on itself")
                if dependency not in latest:
                    raise OperationsError(f"{operation_id} has unknown or forward dependency {dependency}")
                if event["state"] in {"started", "succeeded"} and latest[dependency]["state"] != "succeeded":
                    raise OperationsError(
                        f"{operation_id} cannot be {event['state']} before dependency {dependency} succeeds"
                    )
    return latest


def next_event(root, supplied, events):
    event = validate_input(root, supplied)
    operation_id = event["operation_id"]
    latest = validate_lifecycles(events)
    if operation_id in latest:
        prior = latest[operation_id]
        for name in ("schema", "stage", "activity", "worker_id"):
            if event[name] != prior[name]:
                raise OperationsError(f"{operation_id} changed immutable field {name}")
        if event["schema"] == SCHEMA_V2 and event["dependencies"] != prior["dependencies"]:
            raise OperationsError(f"{operation_id} changed immutable field dependencies")
        if event["state"] not in TRANSITIONS[prior["state"]]:
            raise OperationsError(
                f"invalid transition for {operation_id}: {prior['state']} -> {event['state']}"
            )
    if event["schema"] == SCHEMA_V2:
        for dependency in event["dependencies"]:
            if dependency == operation_id:
                raise OperationsError(f"{operation_id} cannot depend on itself")
            if dependency not in latest:
                raise OperationsError(f"{operation_id} has unknown dependency {dependency}")
            if event["state"] in {"started", "succeeded"} and latest[dependency]["state"] != "succeeded":
                raise OperationsError(
                    f"{operation_id} cannot be {event['state']} before dependency {dependency} succeeds"
                )
    body = dict(event)
    body.update(
        {
            "sequence": len(events) + 1,
            "previous": events[-1]["sha256"] if events else None,
        }
    )
    body["sha256"] = digest(body)
    return body


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def freshness(root, event):
    stale = []
    for artifact in event["artifacts"]:
        try:
            path = project_file(root, artifact["path"])
            if file_digest(path) != artifact["sha256"]:
                stale.append({"operation_id": event["operation_id"], "path": artifact["path"], "reason": "hash-changed"})
        except OperationsError:
            stale.append({"operation_id": event["operation_id"], "path": artifact["path"], "reason": "missing-or-invalid"})
    return stale


def summarize(root, events):
    latest = validate_lifecycles(events)
    totals = {metric: 0 for metric in METRICS}
    known = {metric: 0 for metric in METRICS}
    unknown = {metric: 0 for metric in METRICS}
    by_stage = {}
    stale = []
    for event in latest.values():
        stage = by_stage.setdefault(event["stage"], {state: 0 for state in STATES})
        stage[event["state"]] += 1
        for metric in METRICS:
            value = event["usage"][metric]
            if value is None:
                unknown[metric] += 1
            else:
                totals[metric] += value
                known[metric] += 1
        stale.extend(freshness(root, event))
    attention = sorted(
        (
            {
                "operation_id": event["operation_id"],
                "stage": event["stage"],
                "state": event["state"],
                "blocker": event["blocker"],
                "next_action": event["next_action"],
                "wait": event.get("wait"),
            }
            for event in latest.values()
            if event["state"] in {"started", "waiting", "failed", "blocked"}
        ),
        key=lambda item: (item["stage"], item["operation_id"]),
    )
    return {
        "schema": "research-operations-status.v2" if any(event["schema"] == SCHEMA_V2 for event in events) else "research-operations-status.v1",
        "event_count": len(events),
        "operation_count": len(latest),
        "by_stage": by_stage,
        "usage": {
            metric: {"observed_total": totals[metric], "known_operations": known[metric], "unknown_operations": unknown[metric]}
            for metric in METRICS
        },
        "attention": attention,
        "stale_artifacts": stale,
        "scientific_certification": "not-established-by-this-tool",
    }


def markdown(status):
    lines = ["# Research operations status", "", f"Operations: {status['operation_count']} ({status['event_count']} events)", "", "## Usage"]
    for metric, item in status["usage"].items():
        lines.append(f"- {metric}: observed total {item['observed_total']}; known {item['known_operations']}; unknown {item['unknown_operations']}")
    lines.extend(["", "## Attention"])
    if not status["attention"]:
        lines.append("- None recorded.")
    for item in status["attention"]:
        if item["state"] == "waiting":
            detail = f"waiting on {item['wait']['kind']} handle {item['wait']['handle']}"
        else:
            detail = item["blocker"] or "in progress"
        next_action = f"; next: {item['next_action']}" if item["next_action"] else ""
        lines.append(f"- {item['operation_id']} [{item['stage']}/{item['state']}]: {detail}{next_action}")
    lines.extend(["", "This status reports recorded operations, not scientific validity."])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--project", required=True)
    record.add_argument("--event", required=True)
    record.add_argument("--write", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--project", required=True)
    status.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise OperationsError("--project must name an existing absolute ordinary directory")
        root = root.resolve()
        folder, path, lock_path = state_paths(root)
        if args.command == "record":
            event_path = Path(args.event)
            if not event_path.is_absolute():
                event_path = root / event_path
            if not event_path.resolve().is_relative_to(root) or event_path.is_symlink() or not event_path.is_file():
                raise OperationsError("--event must name an ordinary project file")
            supplied = parse(event_path.read_text(encoding="utf-8"))
            if not isinstance(supplied, dict):
                raise OperationsError("--event must contain a JSON object")
            events = load(root)
            result = next_event(root, supplied, events)
            if args.write:
                folder.mkdir(parents=True, exist_ok=True)
                with lock_path.open("a", encoding="utf-8") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    events = load(root)
                    result = next_event(root, supplied, events)
                    atomic(path, "".join(canonical(item) + "\n" for item in events + [result]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        result = summarize(root, load(root))
        if args.format == "markdown":
            print(markdown(result), end="")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["attention"] or result["stale_artifacts"] else 0
    except (OSError, OperationsError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc), "status": "invalid"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
