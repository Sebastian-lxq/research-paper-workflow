"""Mutation tests for repository release invariants."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_public_release.py"
PLUGIN = ROOT / "plugins" / "research-paper-workflow"
SPEC = importlib.util.spec_from_file_location("check_public_release", SCRIPT)
RELEASE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RELEASE)


class SchemaRegistryTests(unittest.TestCase):
    def candidate(self, temporary):
        root = Path(temporary) / "candidate"
        target = root / "plugins" / "research-paper-workflow"
        target.parent.mkdir(parents=True)
        shutil.copytree(
            PLUGIN,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return root, target / "schemas.json"

    def check(self, root):
        errors = []
        RELEASE.check_schemas(root, errors)
        return errors

    def test_current_registry_matches_every_implemented_named_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _ = self.candidate(temporary)
            self.assertEqual(self.check(root), [])

    def test_unregistered_implemented_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, path = self.candidate(temporary)
            data = json.loads(path.read_text(encoding="utf-8"))
            removed = data["schemas"].pop(0)["identifier"]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(
                any(
                    removed in error and "absent from schemas.json" in error
                    for error in self.check(root)
                )
            )

    def test_stale_marker_and_unknown_replacement_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, path = self.candidate(temporary)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["schemas"][0]["marker"] = "not-present-in-owner"
            data["schemas"][0]["superseded_by"] = "missing-schema.v99"
            path.write_text(json.dumps(data), encoding="utf-8")
            errors = self.check(root)
            self.assertTrue(any("marker is absent" in error for error in errors))
            self.assertTrue(any("unknown replacement" in error for error in errors))

    def test_cli_registry_requires_invalid_input_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _ = self.candidate(temporary)
            path = root / "plugins" / "research-paper-workflow" / "controllers.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["controllers"][0]["exit_codes"] = [0, 1]
            path.write_text(json.dumps(data), encoding="utf-8")
            errors = []
            RELEASE.check_controllers(root, errors)
            self.assertTrue(any("success and invalid-input exits" in error for error in errors))


class WorkflowReleaseTests(unittest.TestCase):
    def candidate(self, temporary):
        root = Path(temporary) / "candidate"
        workflows = root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        for name in ("ci.yml", "package.yml", "codeql.yml"):
            shutil.copy2(ROOT / ".github" / "workflows" / name, workflows / name)
        return root

    def test_release_workflows_include_checks_archive_and_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.candidate(temporary)
            errors = []
            RELEASE.check_workflows(root, errors)
            self.assertEqual(errors, [])

    def test_omitting_checksum_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.candidate(temporary)
            path = root / ".github" / "workflows" / "package.yml"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("            dist/*.zip.sha256\n", ""), encoding="utf-8")
            errors = []
            RELEASE.check_workflows(root, errors)
            self.assertTrue(any("dist/*.zip.sha256" in error for error in errors))


class ActionDependencyTests(unittest.TestCase):
    def candidate(self, temporary):
        root = Path(temporary) / "candidate"
        workflows = root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        for name in ("ci.yml", "package.yml", "codeql.yml", "pages.yml"):
            shutil.copy2(ROOT / ".github" / "workflows" / name, workflows / name)
        shutil.copy2(
            ROOT / ".github" / "actions-dependencies.json",
            root / ".github" / "actions-dependencies.json",
        )
        return root

    def test_every_workflow_action_is_attributed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.candidate(temporary)
            errors = []
            RELEASE.check_action_dependencies(root, errors)
            self.assertEqual(errors, [])

    def test_unattributed_action_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.candidate(temporary)
            path = root / ".github" / "workflows" / "ci.yml"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n# mutation fixture\n# uses line intentionally active below\n"
                + "uses: example/unattributed@v1\n",
                encoding="utf-8",
            )
            errors = []
            RELEASE.check_action_dependencies(root, errors)
            self.assertTrue(any("used but unattributed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
