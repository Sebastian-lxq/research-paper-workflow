#!/usr/bin/env python3
"""Fail closed when a repository candidate violates its public-release contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote


PLUGIN_NAME = "research-paper-workflow"
PORTABLE_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
TEXT_SUFFIXES = {".cff", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv"}

REQUIRED_ROOT = {
    ".agents/plugins/marketplace.json",
    ".github/workflows/ci.yml",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "PRIVACY.md",
    "README.md",
    "README.zh-CN.md",
    "SECURITY.md",
    "SUPPORT.md",
    "TERMS.md",
    "THIRD_PARTY.md",
}

FORBIDDEN_NAMES = {".DS_Store", "Thumbs.db"}
FORBIDDEN_FRAGMENTS = {
    "portfolio-snapshot.json": "dated personal portfolio snapshot",
    "song-xiaojun-mentor": "private mentor adapter",
    "xiaohong-chen-research-mentor": "private mentor adapter",
    "juan-carlos-escanciano-research-mentor": "private mentor adapter",
    "victor-chernozhukov-research-mentor": "private mentor adapter",
}
SECRET_PATTERNS = {
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "private key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
}
ABSOLUTE_PATH_PATTERNS = {
    "macOS user path": re.compile(r"/Users/[A-Za-z0-9_.-]+/"),
    "Linux user path": re.compile(r"/home/[A-Za-z0-9_.-]+/"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+"),
}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SCHEMA_LITERAL = re.compile(r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*\.v[0-9]+)[\"']")


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return {}
    return value


def iter_public_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        yield path


def check_required_files(root: Path, errors: list[str]) -> None:
    for relative in sorted(REQUIRED_ROOT):
        if not (root / relative).is_file():
            errors.append(f"missing required release file: {relative}")


def check_manifests(root: Path, errors: list[str]) -> str | None:
    plugin_root = root / "plugins" / PLUGIN_NAME
    portable_path = plugin_root / "plugin.json"
    compat_path = plugin_root / ".codex-plugin" / "plugin.json"
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    for path in (portable_path, compat_path, marketplace_path):
        if not path.is_file():
            errors.append(f"missing manifest: {path.relative_to(root)}")
    if errors:
        return None

    portable = load_json(portable_path, errors)
    compat = load_json(compat_path, errors)
    marketplace = load_json(marketplace_path, errors)

    if portable.get("$schema") != PORTABLE_SCHEMA:
        errors.append("portable plugin manifest has the wrong or missing $schema")
    if portable.get("name") != PLUGIN_NAME or compat.get("name") != PLUGIN_NAME:
        errors.append("plugin names do not match the package directory")
    version = portable.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        errors.append("portable plugin version is not semantic")
        version = None
    if compat.get("version") != version:
        errors.append("portable and compatibility manifest versions differ")
    if portable.get("license") != "MIT" or compat.get("license") != "MIT":
        errors.append("both plugin manifests must declare the MIT license")

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append("repo marketplace must contain exactly one plugin entry")
    else:
        entry = entries[0]
        if entry.get("name") != PLUGIN_NAME:
            errors.append("marketplace plugin name differs from the manifest")
        source = entry.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            errors.append("marketplace source must be a local source object")
        else:
            raw_path = source.get("path")
            if not isinstance(raw_path, str) or not raw_path.startswith("./"):
                errors.append("marketplace source.path must start with ./")
            elif (root / raw_path[2:]).resolve() != plugin_root.resolve():
                errors.append("marketplace source.path does not resolve to the plugin root")
        policy = entry.get("policy")
        if not isinstance(policy, dict) or policy.get("installation") != "AVAILABLE":
            errors.append("marketplace installation policy must be AVAILABLE")
        if not isinstance(policy, dict) or policy.get("authentication") != "ON_INSTALL":
            errors.append("marketplace authentication policy must be ON_INSTALL")

    return version


def check_version_bindings(root: Path, version: str | None, errors: list[str]) -> None:
    if version is None:
        return
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        errors.append(f"CHANGELOG.md has no release heading for {version}")
    if not re.search(rf"(?m)^version:\s*[\"']?{re.escape(version)}[\"']?\s*$", citation):
        errors.append(f"CITATION.cff version does not match {version}")
    if (root / "LICENSE").read_bytes() != (root / "plugins" / PLUGIN_NAME / "LICENSE").read_bytes():
        errors.append("repository and packaged LICENSE files differ")


def check_skill(root: Path, errors: list[str]) -> None:
    skill_root = root / "plugins" / PLUGIN_NAME / "skills" / PLUGIN_NAME
    skill_path = skill_root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("packaged skill is missing SKILL.md")
        return
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        errors.append("SKILL.md is missing YAML frontmatter")
        return
    frontmatter = match.group(1)
    if not re.search(rf"(?m)^name:\s*{re.escape(PLUGIN_NAME)}\s*$", frontmatter):
        errors.append("SKILL.md frontmatter name is incorrect")
    if not re.search(r"(?m)^description:\s*\S", frontmatter):
        errors.append("SKILL.md frontmatter description is missing")


def check_dependencies(root: Path, errors: list[str]) -> None:
    plugin_root = root / "plugins" / PLUGIN_NAME
    dependency_path = plugin_root / "dependencies" / "skills.json"
    if not dependency_path.is_file():
        errors.append("missing machine-readable companion-skill inventory")
        return
    data = load_json(dependency_path, errors)
    integrations = data.get("third_party_skill_integrations")
    if not isinstance(integrations, list) or not integrations:
        errors.append("third-party integration inventory is empty")
        return
    notice = (plugin_root / "THIRD_PARTY.md").read_text(encoding="utf-8")
    for index, item in enumerate(integrations):
        if not isinstance(item, dict):
            errors.append(f"third-party integration {index} is not an object")
            continue
        name = item.get("name")
        if not isinstance(name, str) or name not in notice:
            errors.append(f"third-party integration {name!r} is missing from packaged attribution")
        if not str(item.get("repository", "")).startswith("https://github.com/"):
            errors.append(f"third-party integration {name!r} lacks a GitHub source")
        if not re.fullmatch(r"[0-9a-f]{40}", str(item.get("revision", ""))):
            errors.append(f"third-party integration {name!r} lacks a pinned commit")
        if not item.get("license"):
            errors.append(f"third-party integration {name!r} lacks a license record")
        if item.get("bundled") is not False:
            errors.append(f"third-party integration {name!r} must explicitly record bundled=false")


def check_controllers(root: Path, errors: list[str]) -> None:
    plugin_root = root / "plugins" / PLUGIN_NAME
    registry_path = plugin_root / "controllers.json"
    if not registry_path.is_file():
        errors.append("missing controller registry")
        return
    data = load_json(registry_path, errors)
    if set(data) != {"schema_version", "controllers"} or data.get("schema_version") != 1:
        errors.append("controller registry must be a schema_version 1 object")
    controllers = data.get("controllers")
    if not isinstance(controllers, list) or not controllers:
        errors.append("controller registry is empty")
        return
    names: set[str] = set()
    for index, item in enumerate(controllers):
        if not isinstance(item, dict):
            errors.append(f"controller record {index} is not an object")
            continue
        expected_fields = {"name", "path", "kind", "purpose", "exit_codes"}
        if set(item) != expected_fields:
            errors.append(
                f"controller record {index} must contain exactly {sorted(expected_fields)}"
            )
        name = item.get("name")
        relative = item.get("path")
        kind = item.get("kind")
        if not isinstance(name, str) or not name:
            errors.append(f"controller record {index} has no name")
            continue
        if name in names:
            errors.append(f"duplicate controller name: {name}")
        names.add(name)
        if not isinstance(relative, str) or not relative.endswith(".py"):
            errors.append(f"controller {name} has an invalid Python path")
            continue
        path = (plugin_root / relative).resolve()
        try:
            path.relative_to(plugin_root.resolve())
        except ValueError:
            errors.append(f"controller {name} escapes the plugin root")
            continue
        if not path.is_file():
            errors.append(f"controller {name} path does not exist: {relative}")
            continue
        if kind not in {"cli", "library"}:
            errors.append(f"controller {name} has unknown kind: {kind!r}")
            continue
        purpose = item.get("purpose")
        if not isinstance(purpose, str) or not purpose.strip():
            errors.append(f"controller {name} has no purpose")
        exit_codes = item.get("exit_codes")
        if (
            not isinstance(exit_codes, list)
            or any(type(code) is not int for code in exit_codes)
            or len(exit_codes) != len(set(exit_codes))
            or exit_codes != sorted(exit_codes)
            or any(code not in {0, 1, 2, 124} for code in exit_codes)
        ):
            errors.append(f"controller {name} has invalid exit_codes")
        elif kind == "cli" and not {0, 2}.issubset(exit_codes):
            errors.append(f"CLI controller {name} must declare success and invalid-input exits")
        elif kind == "library" and exit_codes:
            errors.append(f"library controller {name} cannot declare process exit codes")
        if kind == "cli":
            try:
                completed = subprocess.run(
                    [sys.executable, str(path), "--help"],
                    cwd=plugin_root,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                errors.append(f"controller {name} help failed to execute: {exc}")
                continue
            if completed.returncode != 0 or "usage:" not in completed.stdout.lower():
                errors.append(f"controller {name} has a broken --help entrypoint")


def check_schemas(root: Path, errors: list[str]) -> None:
    plugin_root = root / "plugins" / PLUGIN_NAME
    registry_path = plugin_root / "schemas.json"
    if not registry_path.is_file():
        errors.append("missing state-schema registry")
        return
    data = load_json(registry_path, errors)
    if set(data) != {"schema_version", "release_series", "policy", "schemas", "local_integer_formats"}:
        errors.append("schema registry has missing or unknown root fields")
    if data.get("schema_version") != 1:
        errors.append("schema registry must use schema_version 1")
    if not isinstance(data.get("release_series"), str) or not re.fullmatch(r"\d+\.\d+\.x", data["release_series"]):
        errors.append("schema registry release_series must look like 0.1.x")
    if data.get("policy") != "preview-no-silent-mutation":
        errors.append("schema registry has an unknown compatibility policy")

    named = data.get("schemas")
    local = data.get("local_integer_formats")
    if not isinstance(named, list) or not named:
        errors.append("schema registry has no named schemas")
        named = []
    if not isinstance(local, list) or not local:
        errors.append("schema registry has no local integer formats")
        local = []

    fields = {
        "identifier", "owner", "marker", "role", "lifecycle",
        "compatibility", "superseded_by",
    }
    roles = {"input-contract", "persistent-state", "derived-report", "internal-control"}
    lifecycles = {"current", "legacy-compatible", "internal"}
    identifiers: set[str] = set()
    owners: dict[str, str] = {}
    for index, item in enumerate([*named, *local]):
        label = f"schema record {index}"
        if not isinstance(item, dict) or set(item) != fields:
            errors.append(f"{label} must contain exactly {sorted(fields)}")
            continue
        identifier = item["identifier"]
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{label} has no identifier")
            continue
        if identifier in identifiers:
            errors.append(f"duplicate schema identifier: {identifier}")
        identifiers.add(identifier)
        if item["role"] not in roles:
            errors.append(f"schema {identifier} has unknown role: {item['role']!r}")
        if item["lifecycle"] not in lifecycles:
            errors.append(f"schema {identifier} has unknown lifecycle: {item['lifecycle']!r}")
        if not isinstance(item["compatibility"], str) or not item["compatibility"]:
            errors.append(f"schema {identifier} has no compatibility mode")
        replacement = item["superseded_by"]
        if replacement is not None and not isinstance(replacement, str):
            errors.append(f"schema {identifier} has an invalid superseded_by value")
        if item["lifecycle"] == "legacy-compatible" and replacement is None:
            errors.append(f"legacy schema {identifier} must name its replacement")
        owner = item["owner"]
        marker = item["marker"]
        if not isinstance(owner, str) or not owner.endswith(".py"):
            errors.append(f"schema {identifier} has an invalid owner path")
            continue
        path = (plugin_root / owner).resolve()
        try:
            path.relative_to(plugin_root.resolve())
        except ValueError:
            errors.append(f"schema {identifier} owner escapes the plugin root")
            continue
        if not path.is_file():
            errors.append(f"schema {identifier} owner does not exist: {owner}")
            continue
        owners[identifier] = path.read_text(encoding="utf-8")
        if not isinstance(marker, str) or marker not in owners[identifier]:
            errors.append(f"schema {identifier} marker is absent from its owner")

    for item in [*named, *local]:
        if not isinstance(item, dict):
            continue
        replacement = item.get("superseded_by")
        if replacement is not None and replacement not in identifiers:
            errors.append(f"schema {item.get('identifier')!r} names an unknown replacement: {replacement}")

    script_root = plugin_root / "skills" / PLUGIN_NAME / "scripts"
    discovered: set[str] = set()
    for path in script_root.glob("*.py"):
        discovered.update(SCHEMA_LITERAL.findall(path.read_text(encoding="utf-8")))
    registered_named = {
        item.get("identifier") for item in named if isinstance(item, dict)
    }
    for identifier in sorted(discovered - registered_named):
        errors.append(f"named schema is implemented but absent from schemas.json: {identifier}")
    for identifier in sorted(registered_named - discovered):
        errors.append(f"named schema is registered but absent from controller sources: {identifier}")


def check_workflows(root: Path, errors: list[str]) -> None:
    requirements = {
        ".github/workflows/ci.yml": (
            "python3 scripts/run_checks.py",
        ),
        ".github/workflows/package.yml": (
            '"v*"',
            "python3 scripts/run_checks.py",
            "python3 scripts/package_plugin.py",
            "actions/attest@v4",
            "subject-path: dist/*.zip",
            "id-token: write",
            "attestations: write",
            "dist/*.zip",
            "dist/*.zip.sha256",
            "if-no-files-found: error",
        ),
        ".github/workflows/codeql.yml": (
            "github/codeql-action/init@",
            "github/codeql-action/analyze@",
        ),
    }
    for relative, markers in requirements.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative} is missing release requirement: {marker}")


def check_action_dependencies(root: Path, errors: list[str]) -> None:
    inventory_path = root / ".github" / "actions-dependencies.json"
    if not inventory_path.is_file():
        errors.append("missing GitHub Actions dependency inventory")
        return
    data = load_json(inventory_path, errors)
    if set(data) != {"schema_version", "dependencies"} or data.get("schema_version") != 1:
        errors.append("GitHub Actions inventory must be a schema_version 1 object")
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        errors.append("GitHub Actions dependency inventory is empty")
        dependencies = []
    declared: set[str] = set()
    fields = {"uses", "repository", "license", "scope"}
    for index, item in enumerate(dependencies):
        if not isinstance(item, dict) or set(item) != fields:
            errors.append(f"GitHub Action dependency {index} has invalid fields")
            continue
        uses = item["uses"]
        if not isinstance(uses, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?@v[0-9]+", uses
        ):
            errors.append(f"GitHub Action dependency {index} has an invalid uses value")
            continue
        if uses in declared:
            errors.append(f"duplicate GitHub Action dependency: {uses}")
        declared.add(uses)
        if item["repository"] != f"https://github.com/{uses.split('@', 1)[0].rsplit('/', 1)[0] if uses.count('/') == 2 else uses.split('@', 1)[0]}":
            errors.append(f"GitHub Action dependency {uses} has a mismatched repository")
        if item["license"] != "MIT" or item["scope"] != "ci-only":
            errors.append(f"GitHub Action dependency {uses} lacks the expected license/scope")

    observed: set[str] = set()
    for path in (root / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        observed.update(re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text))
    for uses in sorted(observed - declared):
        errors.append(f"workflow action is used but unattributed: {uses}")
    for uses in sorted(declared - observed):
        errors.append(f"GitHub Action dependency is declared but unused: {uses}")


def check_hygiene(root: Path, errors: list[str]) -> None:
    for path in iter_public_files(root):
        relative = path.relative_to(root)
        if path.name in FORBIDDEN_NAMES or path.suffix == ".pyc":
            errors.append(f"generated or platform file must not be released: {relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"declared text file is not UTF-8: {relative}")
            continue
        if relative != Path("scripts/check_public_release.py"):
            for fragment, reason in FORBIDDEN_FRAGMENTS.items():
                if fragment in text or fragment in relative.as_posix():
                    errors.append(f"{relative}: contains {reason} marker {fragment!r}")
            for label, pattern in ABSOLUTE_PATH_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{relative}: contains a {label}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{relative}: contains a possible {label}")


def check_markdown_links(root: Path, errors: list[str]) -> None:
    for path in iter_public_files(root):
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "codex://")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(root)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(root)}: broken local link: {target}")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    check_required_files(root, errors)
    version = check_manifests(root, errors)
    if all((root / path).is_file() for path in ("CHANGELOG.md", "CITATION.cff", "LICENSE")):
        check_version_bindings(root, version, errors)
    check_skill(root, errors)
    check_dependencies(root, errors)
    check_controllers(root, errors)
    check_schemas(root, errors)
    check_workflows(root, errors)
    check_action_dependencies(root, errors)
    check_hygiene(root, errors)
    check_markdown_links(root, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        print(f"public release validation failed with {len(errors)} finding(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("public release validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
