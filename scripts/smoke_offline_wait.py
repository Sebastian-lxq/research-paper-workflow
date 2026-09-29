#!/usr/bin/env python3
"""Exercise a handle-bound offline wait and dependent-work barrier."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = (
    ROOT
    / "plugins"
    / "research-paper-workflow"
    / "skills"
    / "research-paper-workflow"
    / "scripts"
    / "research_operations.py"
)


def invoke(*arguments: str, expected_returncodes: tuple[int, ...] = (0,)) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-B", str(CONTROLLER), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in expected_returncodes:
        raise RuntimeError(
            f"operations controller failed ({completed.returncode}): "
            f"{completed.stderr or completed.stdout}"
        )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("operations controller did not return a JSON object")
    return completed.returncode, value


def event(state: str, recorded_at: str, *, artifacts: list[str], wait=None) -> dict:
    return {
        "schema": "research-operation-event.v2",
        "operation_id": "synthetic-simulation-1",
        "stage": "simulation",
        "activity": "Run the synthetic frozen simulation.",
        "state": state,
        "recorded_at": recorded_at,
        "worker_id": "local-simulator",
        "usage": {
            "wall_seconds": 2.0 if state == "succeeded" else None,
            "tokens": 0 if state == "succeeded" else None,
            "cost_usd": 0 if state == "succeeded" else None,
            "compute_seconds": 1.5 if state == "succeeded" else None,
            "source": "Synthetic local smoke test." if state == "succeeded" else None,
        },
        "provider": "local",
        "artifacts": artifacts,
        "blocker": None,
        "next_action": (
            "Wait for the registered process and result manifest."
            if state in {"started", "waiting"}
            else None
        ),
        "dependencies": [],
        "wait": wait,
    }


def write_event(project: Path, name: str, value: dict) -> str:
    relative = f"events/{name}.json"
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return relative


def record(project: Path, name: str, value: dict, *, expected=(0,)) -> tuple[int, dict]:
    relative = write_event(project, name, value)
    return invoke(
        "record",
        "--project",
        str(project),
        "--event",
        relative,
        "--write",
        expected_returncodes=expected,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="research-paper-workflow-wait-") as temporary:
        project = Path(temporary) / "offline-wait"
        project.mkdir()
        (project / "simulation-plan.txt").write_text(
            "Synthetic frozen design; no scientific result.\n", encoding="utf-8"
        )
        record(
            project,
            "started",
            event(
                "started",
                "2026-09-28T09:00:00+08:00",
                artifacts=["simulation-plan.txt"],
            ),
        )
        wait = {
            "kind": "process",
            "handle": "synthetic-process-42",
            "resume_condition": "The process exits and simulation-result.json exists.",
            "dependent_actions_suspended": True,
            "next_check_at": None,
        }
        record(
            project,
            "waiting",
            event(
                "waiting",
                "2026-09-28T09:00:01+08:00",
                artifacts=["simulation-plan.txt"],
                wait=wait,
            ),
        )
        waiting_exit, waiting = invoke(
            "status",
            "--project",
            str(project),
            expected_returncodes=(1,),
        )
        if waiting["attention"][0].get("wait", {}).get("handle") != wait["handle"]:
            raise RuntimeError("waiting status lost the registered process handle")

        dependent = event(
            "started",
            "2026-09-28T09:00:02+08:00",
            artifacts=["simulation-plan.txt"],
        )
        dependent.update(
            operation_id="write-simulation-claims",
            activity="Write result-dependent simulation claims.",
            worker_id="paper-writer",
            dependencies=["synthetic-simulation-1"],
        )
        refused_exit, refused = record(
            project,
            "dependent",
            dependent,
            expected=(2,),
        )
        if "before dependency" not in refused.get("error", ""):
            raise RuntimeError("dependent result work was not refused while the simulation waited")

        (project / "simulation-result.json").write_text(
            json.dumps({"synthetic": True, "scientific_result": None}) + "\n",
            encoding="utf-8",
        )
        record(
            project,
            "succeeded",
            event(
                "succeeded",
                "2026-09-28T09:00:03+08:00",
                artifacts=["simulation-result.json"],
            ),
        )
        resumed_exit, resumed = invoke("status", "--project", str(project))
        if resumed["attention"] or resumed["stale_artifacts"]:
            raise RuntimeError("terminal simulation did not clear the wait barrier")
        print(
            json.dumps(
                {
                    "example": "offline-wait",
                    "waiting_exit": waiting_exit,
                    "registered_handle": wait["handle"],
                    "dependent_start_exit": refused_exit,
                    "dependent_start_refused": True,
                    "terminal_status_exit": resumed_exit,
                    "wait_cleared_after_terminal_event": True,
                    "scientific_result_claimed": False,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
