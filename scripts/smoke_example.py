#!/usr/bin/env python3
"""Exercise the synthetic quick start in an isolated temporary project."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal-paper"
CONTROLLER = (
    ROOT
    / "plugins"
    / "research-paper-workflow"
    / "skills"
    / "research-paper-workflow"
    / "scripts"
    / "workflow_state.py"
)


def invoke(*arguments: str, expected_returncodes: tuple[int, ...] = (0,)) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(CONTROLLER), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in expected_returncodes:
        raise RuntimeError(
            f"workflow controller failed ({completed.returncode}): "
            f"{completed.stderr or completed.stdout}"
        )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("workflow controller did not return a JSON object")
    return value


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="research-paper-workflow-example-") as temporary:
        project = Path(temporary) / "minimal-paper"
        shutil.copytree(EXAMPLE, project)
        initialized = invoke(
            "init",
            "--project",
            str(project),
            "--paper-type",
            "methods",
            "--simulation",
            "deferred",
            "--write",
        )
        status = invoke(
            "status",
            "--project",
            str(project),
            expected_returncodes=(0, 1),
        )
        plan = project / ".paper" / "workflow" / "plan.json"
        lock = project / ".paper" / "workflow" / ".lock"
        if initialized.get("schema") != "paper-workflow-plan.v1":
            raise RuntimeError("example initialization used an unexpected plan schema")
        if status.get("schema") != "paper-workflow-status.v1":
            raise RuntimeError("example status used an unexpected schema")
        if status.get("outcome") != "in-progress" or status.get("next_runnable") != ["framing"]:
            raise RuntimeError("example status did not preserve the expected initial gate")
        if not plan.is_file() or not lock.is_file():
            raise RuntimeError("example initialization did not create expected state files")
        print(
            json.dumps(
                {
                    "example": "minimal-paper",
                    "initialized": True,
                    "status_schema": status["schema"],
                    "paper_type": "methods",
                    "simulation": "deferred",
                    "scientific_result_claimed": False,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
