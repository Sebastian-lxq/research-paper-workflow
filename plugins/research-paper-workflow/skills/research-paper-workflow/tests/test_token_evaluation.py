"""Tests for paired token-savings evidence and quality non-regression."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "token_evaluation.py"
SPEC = importlib.util.spec_from_file_location("token_evaluation_under_test", SCRIPT)
TOKEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOKEN)


class TokenEvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="token-evaluation-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "research").mkdir()
        self.files = {}
        for name, content in {
            "task.md": "Frozen research task.\n",
            "rubric.md": "Check theorem scope and citation support.\n",
            "baseline.md": "Baseline passed.\n",
            "candidate.md": "Candidate passed.\n",
        }.items():
            path = self.root / "research" / name
            path.write_text(content, encoding="utf-8")
            self.files[name] = path

    def snapshot(self, name):
        path = self.files[name]
        return {
            "path": f"research/{name}",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        }

    def usage(self, total):
        return {
            "uncached_input_tokens": total - 100,
            "cached_input_tokens": 50,
            "output_tokens": 50,
            "measurement": "provider-reported",
            "accounting_key": "provider-normalized-v1",
            "source": "Saved provider response normalized to mutually exclusive buckets.",
        }

    def record(self):
        checks = [
            {"id": "theorem-scope", "status": "pass", "evidence": [self.snapshot("baseline.md")]},
            {"id": "citation-support", "status": "pass", "evidence": [self.snapshot("baseline.md")]},
        ]
        candidate_checks = copy.deepcopy(checks)
        for item in candidate_checks:
            item["evidence"] = [self.snapshot("candidate.md")]
        return {
            "schema": TOKEN.SCHEMA,
            "objective": "Reduce model tokens without weakening the frozen scientific checks.",
            "frozen_scope": {
                "inputs": [self.snapshot("task.md")],
                "rubric": [self.snapshot("rubric.md")],
            },
            "protected_checks": [
                {"id": "theorem-scope", "description": "The theorem target and assumptions remain unchanged."},
                {"id": "citation-support", "description": "Every retained literature claim remains source-supported."},
            ],
            "strategies": [
                {
                    "id": "selective-context",
                    "mechanism": "progressive-disclosure",
                    "scope": "Load only the stage-relevant references and exact evidence locators.",
                    "fidelity": "lossless",
                    "protected_checks": ["theorem-scope", "citation-support"],
                    "rollback_if": "Either protected check is not pass under the frozen rubric.",
                }
            ],
            "baseline": {
                "run_id": "baseline-run",
                "status": "completed",
                "usage": self.usage(4000),
                "checks": checks,
            },
            "candidate": {
                "run_id": "candidate-run",
                "status": "completed",
                "usage": self.usage(2500),
                "checks": candidate_checks,
            },
        }

    def test_measured_reduction_requires_both_quality_passes(self):
        result = TOKEN.validate(self.root, self.record())
        self.assertEqual(result["quality_non_regression"], "passed")
        self.assertEqual(result["saved_tokens"], 1500)
        self.assertEqual(result["conclusion"], "measured-token-reduction-with-bounded-non-regression")

    def test_candidate_quality_failure_rejects_candidate(self):
        record = self.record()
        record["candidate"]["checks"][0]["status"] = "fail"
        result = TOKEN.validate(self.root, record)
        self.assertEqual(result["quality_non_regression"], "failed")
        self.assertEqual(result["conclusion"], "reject-candidate-quality-regression")

    def test_unavailable_usage_never_becomes_zero_or_a_savings_claim(self):
        record = self.record()
        record["candidate"]["usage"] = {
            "uncached_input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "measurement": "unavailable",
            "accounting_key": None,
            "source": None,
        }
        result = TOKEN.validate(self.root, record)
        self.assertIsNone(result["candidate_total_tokens"])
        self.assertEqual(result["token_change"], "not-measured")
        self.assertEqual(result["conclusion"], "optimization-not-established")

    def test_stale_frozen_input_is_rejected(self):
        record = self.record()
        self.files["task.md"].write_text("Changed task.\n", encoding="utf-8")
        with self.assertRaisesRegex(TOKEN.TokenEvaluationError, "stale evidence"):
            TOKEN.validate(self.root, record)

    def test_bounded_lossy_strategy_must_guard_every_protected_check(self):
        record = self.record()
        record["strategies"][0]["fidelity"] = "bounded-lossy"
        record["strategies"][0]["protected_checks"] = ["theorem-scope"]
        with self.assertRaisesRegex(TOKEN.TokenEvaluationError, "guard every protected check"):
            TOKEN.validate(self.root, record)

    def test_measured_usage_requires_complete_exclusive_buckets(self):
        record = self.record()
        record["candidate"]["usage"]["cached_input_tokens"] = None
        with self.assertRaisesRegex(TOKEN.TokenEvaluationError, "all mutually exclusive"):
            TOKEN.validate(self.root, record)

    def test_different_token_accounting_keys_are_not_compared(self):
        record = self.record()
        record["candidate"]["usage"]["accounting_key"] = "different-tokenizer-v1"
        result = TOKEN.validate(self.root, record)
        self.assertFalse(result["measurement_comparable"])
        self.assertEqual(result["token_change"], "not-measured")

    def test_cli_uses_exit_one_for_valid_but_unestablished_optimization(self):
        record = self.record()
        record["candidate"]["checks"][0]["status"] = "unknown"
        path = self.root / "research" / "token-evaluation.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", str(path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reject-candidate-quality-regression", result.stdout)


if __name__ == "__main__":
    unittest.main()
