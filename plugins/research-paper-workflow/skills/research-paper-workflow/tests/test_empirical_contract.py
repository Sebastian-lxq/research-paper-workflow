"""Known-answer tests for empirical adapter/result contracts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "empirical_contract.py"
SPEC = importlib.util.spec_from_file_location("empirical_contract_under_test", SCRIPT)
EMPIRICAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EMPIRICAL)


class EmpiricalContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="empirical-contract-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name, content in {
            "empirical/analysis-plan.md": "Frozen estimand and specification.\n",
            "empirical/config.json": "{\"cluster\": \"firm\"}\n",
            "empirical/results.json": "{\"estimate\": 0.2, \"se\": 0.05}\n",
            "empirical/known-answer.md": "Fixture reproduced the analytic coefficient.\n",
            "empirical/independent.md": "Second implementation agreed within tolerance.\n",
            "empirical/diagnostics.md": "Cluster and sample diagnostics reviewed.\n",
            "empirical/table.csv": "estimate,se\n0.2,0.05\n",
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.contract = self.fixture()

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def ref(self, name, role=None):
        result = {"path": name, "sha256": self.sha(name)}
        if role is not None:
            result["role"] = role
        return result

    def fixture(self):
        return {
            "schema": EMPIRICAL.SCHEMA,
            "result_id": "main-effect",
            "claim_ids": ["C-empirical-1"],
            "estimand": "Average treatment effect for the frozen eligible population.",
            "data": {
                "dataset_id": "authorized-panel",
                "version": "2026-09-27",
                "checksum": "source-checksum-123",
                "sample_definition": "Eligible firms observed in both required periods.",
                "n_observations": 480,
            },
            "specification": {
                "id": "primary-v1",
                "exploratory": False,
                "plan_path": "empirical/analysis-plan.md",
                "plan_sha256": self.sha("empirical/analysis-plan.md"),
                "deviations": [],
            },
            "adapter": {
                "family": "did-event-study",
                "implementation": "project-python-adapter",
                "version": "1.0",
                "command": ["python3", "analysis.py", "--config", "empirical/config.json"],
                "config_path": "empirical/config.json",
                "config_sha256": self.sha("empirical/config.json"),
                "output_path": "empirical/results.json",
                "output_sha256": self.sha("empirical/results.json"),
            },
            "inference": {
                "method": "Cluster-robust Wald interval.",
                "cluster_unit": "firm",
                "confidence_level": 0.95,
                "multiplicity": "Primary estimand only; no adjustment required by the frozen plan.",
                "assumptions": ["Parallel trends for the stated comparison", "Independent clusters"],
            },
            "estimates": [
                {"name": "ate", "value": 0.2, "standard_error": 0.05, "ci_lower": 0.102, "ci_upper": 0.298, "units": "outcome standard deviations"}
            ],
            "diagnostics": [
                {"name": "cluster-count", "status": "pass", "interpretation": "The recorded cluster count supports the planned approximation within the stated scope.", "evidence": [self.ref("empirical/diagnostics.md")]}
            ],
            "artifacts": [
                self.ref("empirical/results.json", "machine-readable estimator output"),
                self.ref("empirical/table.csv", "manuscript table input"),
            ],
            "validation": {
                "known_answer": {"status": "pass", "note": "The adapter reproduced an analytic two-period fixture.", "evidence": [self.ref("empirical/known-answer.md")]},
                "independent_comparison": {"status": "pass", "note": "A second implementation agreed within the frozen tolerance.", "evidence": [self.ref("empirical/independent.md")]},
                "warnings_reviewed": True,
            },
            "interpretation_ceiling": "Association may be interpreted causally only under the listed design assumptions.",
            "failures": [],
        }

    def test_complete_hash_bound_contract_is_eligible(self):
        result = EMPIRICAL.validate(self.root, self.contract)
        self.assertEqual(result["schema"], EMPIRICAL.STATUS_SCHEMA)
        self.assertNotEqual(EMPIRICAL.CONTRACT_SCHEMA, EMPIRICAL.STATUS_SCHEMA)
        self.assertTrue(result["release_eligible"])
        self.assertFalse(result["identification_established"])

    def test_known_answer_is_required(self):
        contract = copy.deepcopy(self.contract)
        contract["validation"]["known_answer"] = {"status": "not-run", "note": "Fixture has not run.", "evidence": []}
        result = EMPIRICAL.validate(self.root, contract)
        self.assertFalse(result["release_eligible"])
        self.assertIn("known-answer fixture", result["blockers"][0])

    def test_documented_infeasible_independent_comparison_is_not_fabricated(self):
        contract = copy.deepcopy(self.contract)
        contract["validation"]["independent_comparison"] = {"status": "not-feasible", "note": "No second verified implementation supports the exact estimator; the limitation remains explicit.", "evidence": []}
        result = EMPIRICAL.validate(self.root, contract)
        self.assertTrue(result["release_eligible"])

    def test_failed_diagnostic_and_execution_failure_block_release(self):
        contract = copy.deepcopy(self.contract)
        contract["diagnostics"][0]["status"] = "fail"
        contract["failures"] = ["The planned clustered bootstrap failed for two specifications."]
        result = EMPIRICAL.validate(self.root, contract)
        self.assertFalse(result["release_eligible"])
        self.assertEqual(result["diagnostic_failures"], ["cluster-count"])
        self.assertTrue(any("execution failures" in item for item in result["blockers"]))

    def test_stale_output_hash_is_invalid(self):
        (self.root / "empirical" / "results.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(EMPIRICAL.EmpiricalError):
            EMPIRICAL.validate(self.root, self.contract)

    def test_estimate_must_be_inside_reported_interval(self):
        contract = copy.deepcopy(self.contract)
        contract["estimates"][0]["ci_upper"] = 0.1
        with self.assertRaises(EMPIRICAL.EmpiricalError):
            EMPIRICAL.validate(self.root, contract)

    def test_empty_diagnostics_cannot_pass_vacuously(self):
        contract = copy.deepcopy(self.contract)
        contract["diagnostics"] = []
        with self.assertRaises(EMPIRICAL.EmpiricalError):
            EMPIRICAL.validate(self.root, contract)

    def test_cli_exit_codes_separate_blocked_from_invalid(self):
        path = self.root / "empirical" / "contract.json"
        path.write_text(json.dumps(self.contract), encoding="utf-8")
        ready = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", "empirical/contract.json"], capture_output=True, text=True)
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        blocked_contract = copy.deepcopy(self.contract)
        blocked_contract["validation"]["warnings_reviewed"] = False
        path.write_text(json.dumps(blocked_contract), encoding="utf-8")
        blocked = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", str(path)], capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        path.write_text("{}", encoding="utf-8")
        invalid = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", str(path)], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()
