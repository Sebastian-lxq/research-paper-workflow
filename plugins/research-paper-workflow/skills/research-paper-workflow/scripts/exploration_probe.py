#!/usr/bin/env python3
"""Run one explicitly authorized local probe; this is not a security sandbox.

Commands are argv, never extracted from documents. Hashes identify inputs, not
scientific validity. Decisions are human judgments; no scores or usage inferred.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_path(value, base=None):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    if ".." in path.parts:
        raise ValueError("parent traversal is not accepted")
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError(f"symlink path is not accepted: {part}")
    return path.resolve()


def project_file(value, project):
    path = clean_path(value, project)
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError(f"input must be an existing regular file within project: {value}")
    return path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_record(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def stop_group(process):
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait()


def run_probe(project, probe_id, baselines, question, criterion, timeout, output, command):
    project = clean_path(project)
    if not project.is_dir():
        raise ValueError("project must be an existing directory")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", probe_id):
        raise ValueError("id must be 1–80 letters, digits, underscores, dots or hyphens")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if not question.strip() or not criterion.strip() or not command or not baselines:
        raise ValueError("question, criterion, command and baseline inputs are required")
    inputs = list(dict.fromkeys(project_file(item, project) for item in baselines))
    output = clean_path(output)
    if output.exists() or not output.parent.is_dir():
        raise ValueError("output must be a new directory with an existing parent")
    if any(item.is_relative_to(output) for item in inputs):
        raise ValueError("output must not contain baseline inputs")
    output.mkdir()  # Exclusive creation; an old record is never reused.
    snapshots = output / "inputs"
    snapshots.mkdir()
    records = []
    for index, path in enumerate(inputs):
        snapshot = snapshots / f"{index:04d}.bin"
        hasher = hashlib.sha256()
        with path.open("rb") as source, snapshot.open("xb") as target:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                target.write(chunk)
                hasher.update(chunk)
        records.append({"path": str(path.relative_to(project)),
                        "snapshot": str(snapshot.relative_to(output)),
                        "sha256_before": hasher.hexdigest()})
    record = {"schema_version": 1, "id": probe_id, "project": str(project),
              "command": list(command), "question": question, "criterion": criterion,
              "timeout_seconds": timeout, "started_at": timestamp(),
              "baselines": records, "scientific_score": None,
              "usage": {"tokens": None, "cost": None, "source": None},
              "status": "launch_error", "returncode": None, "error": None}
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        start = time.monotonic()
        process = None
        try:
            process = subprocess.Popen(command, cwd=project, stdout=stdout, stderr=stderr,
                                       stdin=subprocess.DEVNULL, start_new_session=os.name == "posix")
            try:
                process.wait(timeout=timeout)
                record["status"] = "succeeded" if process.returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                record["status"] = "timed_out"
                record["error"] = f"command exceeded {timeout} seconds"
        except OSError as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if process is not None:
                # Stop remaining work in this process group after the parent ends.
                stop_group(process)
                record["returncode"] = process.returncode
            record["wall_seconds"] = time.monotonic() - start
            record["finished_at"] = timestamp()
    for entry in records:
        try:
            entry["sha256_after"] = digest(project_file(entry["path"], project))
            entry["after_error"] = None
        except (OSError, ValueError) as exc:
            entry["sha256_after"] = None
            entry["after_error"] = f"{type(exc).__name__}: {exc}"
        entry["changed"] = entry["sha256_before"] != entry["sha256_after"]
    clean_path(output)  # Do not follow a replacement symlink created by a command.
    write_record(output / "run.json", record)
    return record


def decide(output, decision, reason, evidence=()):
    output = clean_path(output)
    run_path = clean_path(output / "run.json")
    with run_path.open(encoding="utf-8") as stream:
        record = json.load(stream)
    if record.get("schema_version") != 1:
        raise ValueError("unsupported run schema")
    if decision not in {"retain", "revise", "discard", "inconclusive"} or not reason.strip():
        raise ValueError("a supported decision and nonempty reason are required")
    project = clean_path(record["project"])
    support = []
    for item in evidence:
        path = project_file(item, project)
        support.append({"path": str(path.relative_to(project)), "sha256": digest(path)})
    event = {"schema_version": 1, "recorded_at": timestamp(), "decision": decision,
             "reason": reason, "evidence": support}
    path = clean_path(output / "decisions.jsonl")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        if os.name == "posix":
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    for name in ("project", "id", "question", "criterion", "output"):
        run.add_argument(f"--{name}", required=True)
    run.add_argument("--baseline", action="append", required=True)
    run.add_argument("--timeout", type=float, required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    decision = sub.add_parser("decide")
    decision.add_argument("output")
    decision.add_argument("--decision", choices=("retain", "revise", "discard", "inconclusive"), required=True)
    decision.add_argument("--reason", required=True)
    decision.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.action == "run":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            result = run_probe(args.project, args.id, args.baseline, args.question,
                               args.criterion, args.timeout, args.output, command)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["status"] == "succeeded" else 124 if result["status"] == "timed_out" else 1
        print(json.dumps(decide(args.output, args.decision, args.reason, args.evidence), ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
