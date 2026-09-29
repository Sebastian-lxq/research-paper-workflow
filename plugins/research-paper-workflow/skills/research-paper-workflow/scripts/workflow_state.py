#!/usr/bin/env python3
"""Project-local paper workflow receipts; readiness is not scientific certification."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


STAGES = {
    "framing": ["scope"],
    "ideas": ["feasibility", "falsifiers"],
    "literature": ["source_claims", "nearest_neighbors"],
    "design": ["identification", "evidence_plan"],
    "theory": ["proof_scope", "independent_proof_review"],
    "empirical": ["data_lineage", "inference", "result_reproduction"],
    "simulation_design": ["runnable_handoff", "implementation_checks"],
    "simulation_run": ["actual_results", "calibration", "mc_precision"],
    "manuscript": ["wording", "citations", "appendices"],
    "verification": [
        "cross_file",
        "handoff_integrity",
        "reproducibility",
        "rendered_candidate",
    ],
    "review": ["independent_scientific_review"],
    "revision": ["findings_resolved", "semantic_sync"],
    "delivery": ["scope_label", "handoff_complete"],
    "submission": ["journal_policy", "release_candidate", "author_approval"],
}
STATES = {"ready", "blocked", "deferred", "active"}


class WorkflowError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise WorkflowError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def parse(text):
    return json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            WorkflowError(f"invalid JSON number: {value}")
        ),
    )


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError(f"{field} must be nonempty text")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value
    ):
        raise WorkflowError("invalid actor identifier")
    return value


def relative(value):
    text(value, "artifact path")
    part = PurePosixPath(value)
    if (
        part.is_absolute()
        or part.as_posix() != value
        or "\\" in value
        or any(x in {".", ".."} for x in part.parts)
        or value == "."
        or value.startswith(".paper/workflow/")
    ):
        raise WorkflowError(f"unsafe or self-referential artifact path: {value}")
    return value


def safe_path(root, name):
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        if path.is_symlink():
            raise WorkflowError(
                f"symlinks are not allowed in receipts or state: {name}"
            )
    return path


def snapshot(root, name):
    name = relative(name)
    path = safe_path(root, name)
    if not path.is_file():
        raise WorkflowError(f"artifact missing or not a regular file: {name}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": name, "sha256": h.hexdigest(), "size": path.stat().st_size}


def directory(root, track="main"):
    identifier(track)
    suffix = "" if track == "main" else f"/tracks/{track}"
    return safe_path(root, f".paper/workflow{suffix}")


def check_state_files(root, track="main"):
    folder = directory(root, track)
    for name in ("plan.json", "events.jsonl", ".lock"):
        path = safe_path(root, (folder / name).relative_to(root).as_posix())
        if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
            raise WorkflowError(
                f"state file must be an ordinary single-link file: {name}"
            )
    return folder


def make_plan(kind="methods", simulation="deferred", empirical=None):
    if kind not in {"methods", "theory", "empirical", "hybrid"}:
        raise WorkflowError("unknown paper type")
    if simulation not in {"run", "deferred", "not-applicable"}:
        raise WorkflowError("unknown simulation mode")
    if empirical is None:
        empirical = kind in {"empirical", "hybrid"}
    if type(empirical) is not bool:
        raise WorkflowError("empirical must be boolean")
    if kind in {"empirical", "hybrid"} and not empirical:
        raise WorkflowError(
            "an empirical or hybrid paper requires its empirical branch"
        )
    theory = kind in {"methods", "theory", "hybrid"}
    deps = {
        "framing": [],
        "ideas": ["framing"],
        "literature": ["ideas"],
        "design": ["literature"],
        "theory": ["design"],
        "empirical": ["design"],
        "simulation_design": ["design"] + (["theory"] if theory else []),
        "simulation_run": ["simulation_design"],
        "manuscript": ["design"]
        + (["theory"] if theory else [])
        + (["empirical"] if empirical else [])
        + (["simulation_design"] if simulation != "not-applicable" else []),
        "verification": ["manuscript"],
        "review": ["verification"],
        "revision": ["review"],
        "delivery": ["revision"],
        "submission": ["delivery"]
        + (["simulation_run"] if simulation != "not-applicable" else []),
    }
    inactive = ([] if theory else ["theory"]) + ([] if empirical else ["empirical"])
    if simulation == "not-applicable":
        inactive += ["simulation_design", "simulation_run"]
    plan = {
        "schema": "paper-workflow-plan.v1",
        "paper_type": kind,
        "simulation": simulation,
        "empirical": empirical,
        "inactive": inactive,
        "dependencies": deps,
        "required_checks": STAGES,
    }
    plan["sha256"] = digest(plan)
    return plan


def load(root, track="main"):
    folder = check_state_files(root, track)
    plan = parse((folder / "plan.json").read_text())
    if not isinstance(plan, dict):
        raise WorkflowError("plan must be an object")
    expected = make_plan(plan["paper_type"], plan["simulation"], plan["empirical"])
    if plan != expected:
        raise WorkflowError("plan changed or does not match the versioned workflow")
    path = folder / "events.jsonl"
    events = []
    if path.exists():
        for line in path.read_text().splitlines():
            event = parse(line)
            if not isinstance(event, dict):
                raise WorkflowError("event must be an object")
            body = {k: v for k, v in event.items() if k != "sha256"}
            if (
                event.get("sha256") != digest(body)
                or event.get("sequence") != len(events) + 1
                or event.get("previous") != (events[-1]["sha256"] if events else None)
                or event.get("plan_sha256") != plan["sha256"]
            ):
                raise WorkflowError("event hash chain or plan binding is invalid")
            if event.get("stage") not in STAGES or event.get("state") not in STATES:
                raise WorkflowError("event stage or state is invalid")
            if event["stage"] in plan["inactive"] or (
                event["state"] == "deferred" and event["stage"] != "simulation_run"
            ):
                raise WorkflowError("event falls outside the frozen scope")
            validate_receipt(event["receipt"], event["stage"], event["state"])
            if set(event["upstream"]) != set(plan["dependencies"][event["stage"]]):
                raise WorkflowError("event dependency binding is incomplete")
            observed = (
                {"simulation_run"}
                if event["stage"] == "manuscript"
                and "simulation_run" not in plan["inactive"]
                else set()
            )
            if set(event.get("observed", {})) != observed:
                raise WorkflowError("event result-arrival binding is incomplete")
            if {a["path"] for a in event["artifacts"]} != set(
                event["receipt"]["artifacts"]
            ):
                raise WorkflowError("event artifact binding is incomplete")
            events.append(event)
    return plan, events


def validate_receipt(receipt, stage, state):
    if not isinstance(receipt, dict):
        raise WorkflowError("receipt must be an object")
    required = {
        "summary",
        "artifacts",
        "checks",
        "worker_id",
        "reviewer_id",
        "next_action",
    }
    if set(receipt) != required:
        raise WorkflowError(f"receipt must contain exactly {sorted(required)}")
    text(receipt["summary"], "summary")
    identifier(receipt["worker_id"])
    if receipt["reviewer_id"] is not None:
        identifier(receipt["reviewer_id"])
    if not isinstance(receipt["next_action"], str):
        raise WorkflowError("next_action must be text")
    paths = receipt["artifacts"]
    if not isinstance(paths, list) or any(not isinstance(x, str) for x in paths):
        raise WorkflowError("artifacts must be an array of relative paths")
    if len(set(paths)) != len(paths):
        raise WorkflowError("duplicate artifact")
    for path in paths:
        relative(path)
    checks = receipt["checks"]
    if not isinstance(checks, dict) or set(checks) - set(STAGES[stage]):
        raise WorkflowError("unknown stage check")
    for key, check in checks.items():
        if not isinstance(check, dict) or set(check) != {"state", "evidence", "note"}:
            raise WorkflowError(f"check {key} needs state/evidence/note")
        if check["state"] not in {"pass", "partial", "fail", "not-applicable"}:
            raise WorkflowError("unknown check state")
        text(check["note"], "check note")
        if not isinstance(check["evidence"], list) or any(
            p not in paths for p in check["evidence"]
        ):
            raise WorkflowError("check evidence must refer to snapshotted artifacts")
        if check["state"] == "pass" and not check["evidence"]:
            raise WorkflowError("a pass check needs actual evidence artifacts")
    if state == "ready":
        if not paths or set(checks) != set(STAGES[stage]):
            raise WorkflowError("ready stage needs artifacts and all required checks")
        if any(check["state"] != "pass" for check in checks.values()):
            raise WorkflowError(
                "ready cannot contain partial, failed, or inapplicable required checks"
            )
        if stage in {"theory", "review", "submission"}:
            if (
                receipt["reviewer_id"] is None
                or receipt["reviewer_id"] == receipt["worker_id"]
            ):
                raise WorkflowError("this ready stage requires a distinct reviewer")
    elif not receipt["next_action"].strip():
        raise WorkflowError("unfinished stages need a concrete next_action")


def analyze(root, plan, events):
    latest = {event["stage"]: event for event in events}
    states, reasons = {}, {}
    for stage in STAGES:
        if stage in plan["inactive"]:
            states[stage] = "not-applicable"
            reasons[stage] = []
            continue
        event = latest.get(stage)
        if event is None:
            states[stage] = (
                "deferred"
                if stage == "simulation_run" and plan["simulation"] == "deferred"
                else "pending"
            )
            reasons[stage] = []
            continue
        problems = []
        for artifact in event["artifacts"]:
            try:
                if snapshot(root, artifact["path"]) != artifact:
                    problems.append(f"artifact changed: {artifact['path']}")
            except WorkflowError as error:
                problems.append(str(error))
        for dep in plan["dependencies"][stage]:
            current = latest.get(dep)
            if event["upstream"].get(dep) != (current["sha256"] if current else None):
                problems.append(f"new prerequisite receipt: {dep}")
            if event["state"] == "ready" and states[dep] != "ready":
                problems.append(f"prerequisite {dep} is {states[dep]}")
        for observed, bound in event["observed"].items():
            current = latest.get(observed)
            if bound != (current["sha256"] if current else None):
                problems.append(
                    f"result availability changed; revise dependent prose: {observed}"
                )
            elif current is not None and states[observed] == "stale":
                problems.append(f"consumed result evidence is stale: {observed}")
        states[stage] = "stale" if problems else event["state"]
        reasons[stage] = problems
    sim_done = states["simulation_run"] in {"ready", "not-applicable"}
    if states["submission"] == "ready" and sim_done:
        outcome = "submission-candidate"
    elif states["delivery"] == "ready" and not sim_done:
        outcome = "manuscript-ready-except-simulations"
    elif states["delivery"] == "ready":
        outcome = "manuscript-ready-for-author-review"
    else:
        outcome = "in-progress"
    runnable = [
        stage
        for stage in STAGES
        if states[stage] in {"pending", "active", "stale", "blocked"}
        and all(states[dep] == "ready" for dep in plan["dependencies"][stage])
    ]
    return {
        "schema": "paper-workflow-status.v1",
        "outcome": outcome,
        "stages": states,
        "reasons": reasons,
        "next_runnable": runnable,
        "deferred": [s for s in STAGES if states[s] == "deferred"],
        "next_actions": {
            s: e["receipt"]["next_action"]
            for s, e in latest.items()
            if e["receipt"]["next_action"]
        },
        "scientific_certification": "not-established-by-this-tool",
        "trust": "local-controller-attested-receipts-not-external-signatures",
    }


def event_for(root, plan, events, stage, state, receipt):
    if stage in plan["inactive"]:
        raise WorkflowError(
            "stage is outside this frozen plan; initialize a separate scoped workflow"
        )
    if state == "deferred" and stage != "simulation_run":
        raise WorkflowError(
            "only production simulation can be deferred; other missing work is blocked"
        )
    validate_receipt(receipt, stage, state)
    current = analyze(root, plan, events)
    if state == "ready" and any(
        current["stages"][d] != "ready" for d in plan["dependencies"][stage]
    ):
        raise WorkflowError("required prerequisite is not ready")
    latest = {e["stage"]: e for e in events}
    event = {
        "sequence": len(events) + 1,
        "previous": events[-1]["sha256"] if events else None,
        "plan_sha256": plan["sha256"],
        "stage": stage,
        "state": state,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "receipt": receipt,
        "artifacts": [snapshot(root, p) for p in sorted(receipt["artifacts"])],
        "upstream": {
            d: latest[d]["sha256"] if d in latest else None
            for d in plan["dependencies"][stage]
        },
        "observed": {
            "simulation_run": latest["simulation_run"]["sha256"]
            if "simulation_run" in latest
            else None
        }
        if stage == "manuscript" and "simulation_run" not in plan["inactive"]
        else {},
    }
    event["sha256"] = digest(event)
    return event


def atomic(path, content):
    fd, name = tempfile.mkstemp(prefix=".workflow-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project", required=True)
    init.add_argument(
        "--track", default="main", help="Separate immutable scope track; default: main"
    )
    init.add_argument(
        "--paper-type",
        choices=["methods", "theory", "empirical", "hybrid"],
        default="methods",
    )
    init.add_argument(
        "--simulation",
        choices=["run", "deferred", "not-applicable"],
        default="deferred",
    )
    init.add_argument("--empirical", choices=["required", "not-applicable"])
    init.add_argument("--write", action="store_true")
    rec = sub.add_parser("record")
    rec.add_argument("--project", required=True)
    rec.add_argument("--track", default="main")
    rec.add_argument("--stage", choices=list(STAGES), required=True)
    rec.add_argument("--state", choices=sorted(STATES), required=True)
    rec.add_argument("--receipt", required=True)
    rec.add_argument("--write", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--project", required=True)
    status.add_argument("--track", default="main")
    args = parser.parse_args(argv)
    try:
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir():
            raise WorkflowError(
                "--project must name an existing absolute project directory"
            )
        root = root.resolve()
        folder = check_state_files(root, args.track)
        if args.command == "init":
            tracks_only_container = (
                args.track == "main"
                and folder.is_dir()
                and {child.name for child in folder.iterdir()} <= {"tracks"}
            )
            if folder.exists() and not tracks_only_container:
                raise WorkflowError(
                    "workflow already exists; read status and resume instead of reinitializing"
                )
            empirical = None if args.empirical is None else args.empirical == "required"
            result = make_plan(args.paper_type, args.simulation, empirical)
            if args.write:
                folder.mkdir(parents=True, exist_ok=tracks_only_container)
                with (folder / ".lock").open("a") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    check_state_files(root, args.track)
                    if (folder / "plan.json").exists():
                        raise WorkflowError(
                            "workflow was initialized concurrently; resume it"
                        )
                    atomic(folder / "plan.json", json.dumps(result, indent=2) + "\n")
        elif args.command == "record":
            plan, events = load(root, args.track)
            receipt = parse(Path(args.receipt).read_text())
            result = event_for(root, plan, events, args.stage, args.state, receipt)
            if args.write:
                with (folder / ".lock").open("a") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    check_state_files(root, args.track)
                    plan, events = load(root, args.track)
                    result = event_for(
                        root, plan, events, args.stage, args.state, receipt
                    )
                    atomic(
                        folder / "events.jsonl",
                        "".join(canonical(e) + "\n" for e in events + [result]),
                    )
        else:
            plan, events = load(root, args.track)
            result = analyze(root, plan, events)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "status":
            return 0 if result["outcome"] == "submission-candidate" else 1
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error), "outcome": "invalid-state"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
