#!/usr/bin/env python3
"""Report companion-skill availability without treating installation as validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PLUGIN_ROOT / "dependencies" / "skills.json"
NAME_PATTERN = re.compile(r"(?m)^name:\s*[\"']?([^\s\"']+)[\"']?\s*$")


def skill_name(path: Path) -> str | None:
    try:
        prefix = path.read_text(encoding="utf-8")[:4096]
    except (OSError, UnicodeDecodeError):
        return None
    if not prefix.startswith("---\n"):
        return None
    end = prefix.find("\n---\n", 4)
    if end < 0:
        return None
    match = NAME_PATTERN.search(prefix[4:end])
    return match.group(1) if match else None


def discover(roots: list[Path]) -> dict[str, str]:
    found: dict[str, str] = {}
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            if any(part.startswith(".") and part not in {".codex", ".agents"} for part in path.parts):
                continue
            name = skill_name(path)
            if name and name not in found:
                found[name] = str(path.parent)
    return found


def load_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("dependency manifest root must be an object")
    return value


def records(manifest: dict, discovered: dict[str, str]) -> list[dict]:
    output: list[dict] = []
    groups = (
        ("first_party_companion_interfaces", "first-party companion"),
        ("third_party_skill_integrations", "third-party integration"),
    )
    for key, relation in groups:
        items = manifest.get(key, [])
        if not isinstance(items, list):
            raise ValueError(f"{key} must be a list")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValueError(f"invalid dependency record in {key}")
            name = item["name"]
            output.append(
                {
                    "name": name,
                    "relation": relation,
                    "capability": item.get("capability"),
                    "status": "available" if name in discovered else "missing",
                    "path": discovered.get(name),
                    "scientific_validation": "not assessed",
                }
            )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--skill-root",
        action="append",
        type=Path,
        dest="skill_roots",
        help="Skill root to scan; repeat for multiple roots.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    roots = args.skill_roots or [Path("~/.codex/skills"), Path("~/.agents/skills")]
    try:
        manifest = load_manifest(args.manifest.resolve())
        found = discover(roots)
        result = records(manifest, found)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"companion check failed: {exc}", file=sys.stderr)
        return 2

    payload = {
        "schema_version": 1,
        "skill_roots": [str(path.expanduser().resolve()) for path in roots],
        "companions": result,
        "available": sum(item["status"] == "available" for item in result),
        "missing": sum(item["status"] == "missing" for item in result),
        "scope_note": "Availability is operational only; scientific validity is not assessed.",
    }
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in result:
            location = f" ({item['path']})" if item["path"] else ""
            print(f"{item['status']:9} {item['name']}: {item['capability']}{location}")
        print(payload["scope_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
