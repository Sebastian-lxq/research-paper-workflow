#!/usr/bin/env python3
"""Run the repository checks used locally and in CI."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "research-paper-workflow" / "skills" / "research-paper-workflow"


def run(label: str, command: list[str], *, cwd: Path = ROOT) -> None:
    print(f"==> {label}", flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def compile_python_sources() -> None:
    print("==> Python syntax", flush=True)
    failures: list[str] = []
    for base in (
        ROOT / "scripts",
        ROOT / "tests",
        ROOT / "plugins" / "research-paper-workflow" / "scripts",
        SKILL_ROOT / "scripts",
        SKILL_ROOT / "tests",
    ):
        for path in sorted(base.glob("*.py")):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, SyntaxError) as exc:
                failures.append(f"{path.relative_to(ROOT)}: {exc}")
    if failures:
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Python syntax: OK")


def main() -> int:
    run("Public release contract", [sys.executable, "scripts/check_public_release.py"])
    compile_python_sources()
    run(
        "Workflow unit tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=SKILL_ROOT,
    )
    run(
        "Repository integration tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=ROOT,
    )
    run("Synthetic example smoke test", [sys.executable, "scripts/smoke_example.py"])
    run("Offline wait smoke test", [sys.executable, "scripts/smoke_offline_wait.py"])
    if (ROOT / ".git").is_dir():
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if head.returncode == 0:
            run("Git whitespace check", ["git", "diff", "--check", "HEAD"], cwd=ROOT)
        else:
            run("Git unstaged whitespace check", ["git", "diff", "--check"], cwd=ROOT)
            run("Git staged whitespace check", ["git", "diff", "--cached", "--check"], cwd=ROOT)
    print("all repository checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
