import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "research-paper-workflow" / "scripts" / "check_companions.py"
PACKAGE_SCRIPT = ROOT / "scripts" / "package_plugin.py"
VERIFY_SCRIPT = ROOT / "scripts" / "verify_release.py"
SPEC = importlib.util.spec_from_file_location("check_companions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompanionCheckTests(unittest.TestCase):
    def test_discovers_frontmatter_name_and_marks_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            present = root / "provider-folder"
            present.mkdir()
            (present / "SKILL.md").write_text(
                "---\nname: available-provider\ndescription: Test provider.\n---\n",
                encoding="utf-8",
            )
            manifest = {
                "first_party_companion_interfaces": [
                    {"name": "available-provider", "capability": "available capability"},
                    {"name": "missing-provider", "capability": "missing capability"},
                ],
                "third_party_skill_integrations": [],
            }
            discovered = MODULE.discover([root])
            records = MODULE.records(manifest, discovered)
            self.assertEqual(records[0]["status"], "available")
            self.assertEqual(records[1]["status"], "missing")
            self.assertTrue(records[0]["path"].endswith("provider-folder"))
            self.assertEqual(records[0]["scientific_validation"], "not assessed")

    def test_cli_json_is_machine_readable_and_missing_is_not_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "skills.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "first_party_companion_interfaces": [
                            {"name": "not-installed", "capability": "test"}
                        ],
                        "third_party_skill_integrations": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest_path),
                    "--skill-root",
                    str(root / "empty"),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["missing"], 1)
            self.assertEqual(payload["companions"][0]["status"], "missing")
            self.assertIn("scientific validity is not assessed", payload["scope_note"])

    def test_package_contains_portable_and_compatibility_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "plugin.zip"
            second_archive = Path(temporary) / "plugin-second.zip"
            completed = subprocess.run(
                [sys.executable, str(PACKAGE_SCRIPT), "--output", str(archive), "--skip-validation"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            second = subprocess.run(
                [sys.executable, str(PACKAGE_SCRIPT), "--output", str(second_archive), "--skip-validation"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(archive.read_bytes(), second_archive.read_bytes())
            checksum = archive.with_name(f"{archive.name}.sha256")
            self.assertTrue(checksum.is_file())
            self.assertRegex(checksum.read_text(encoding="utf-8"), r"^[0-9a-f]{64}  plugin\.zip\n$")
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
                self.assertIn("research-paper-workflow/plugin.json", names)
                self.assertIn("research-paper-workflow/.codex-plugin/plugin.json", names)
                self.assertIn(
                    "research-paper-workflow/skills/research-paper-workflow/SKILL.md",
                    names,
                )
                self.assertIn("research-paper-workflow/LICENSE", names)
                self.assertIn("research-paper-workflow/schemas.json", names)
                manifest_name = "research-paper-workflow/MANIFEST.sha256"
                self.assertIn(manifest_name, names)
                manifest = bundle.read(manifest_name).decode("utf-8").splitlines()
                self.assertTrue(manifest)
                listed = set()
                for line in manifest:
                    digest, relative = line.split("  ", 1)
                    member = f"research-paper-workflow/{relative}"
                    self.assertRegex(digest, r"^[0-9a-f]{64}$")
                    self.assertIn(member, names)
                    self.assertEqual(hashlib.sha256(bundle.read(member)).hexdigest(), digest)
                    listed.add(member)
                self.assertEqual(listed, names - {manifest_name})
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
            verified = subprocess.run(
                [sys.executable, str(VERIFY_SCRIPT), str(archive)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertTrue(json.loads(verified.stdout)["valid"])

    def test_release_verifier_rejects_a_rehashed_tampered_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "plugin.zip"
            built = subprocess.run(
                [sys.executable, str(PACKAGE_SCRIPT), "--output", str(archive), "--skip-validation"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            tampered = root / "tampered.zip"
            with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w") as target:
                for item in source.infolist():
                    content = source.read(item.filename)
                    if item.filename == "research-paper-workflow/plugin.json":
                        content += b" "
                    target.writestr(item, content)
            checksum = tampered.with_name(f"{tampered.name}.sha256")
            checksum.write_text(
                f"{hashlib.sha256(tampered.read_bytes()).hexdigest()}  {tampered.name}\n",
                encoding="utf-8",
            )
            verified = subprocess.run(
                [sys.executable, str(VERIFY_SCRIPT), str(tampered)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verified.returncode, 1, verified.stdout + verified.stderr)
            self.assertIn("internal manifest digest mismatch", json.loads(verified.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
