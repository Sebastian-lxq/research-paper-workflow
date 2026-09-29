"""Known-answer tests for idea portfolio and search-frontier validation."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "idea_portfolio.py"
SPEC = importlib.util.spec_from_file_location("idea_portfolio_under_test", SCRIPT)
PORTFOLIO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PORTFOLIO)


class IdeaPortfolioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="idea-portfolio-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "research").mkdir()
        self.write("research/idea-mining.md", "# Candidate I1\nEvidence-bearing idea record.\n")
        self.write("research/search.md", "Search log with source locators.\n")
        self.write("research/probe.md", "Probe survived the stated falsifier.\n")
        self.write("research/decision.md", "Decision and bounded novelty language.\n")
        self.record = self.fixture()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def ref(self, name):
        data = (self.root / name).read_bytes()
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    def fixture(self):
        coverage = []
        for kind in sorted(PORTFOLIO.COVERAGE_KINDS):
            coverage.append(
                {
                    "kind": kind,
                    "state": "checked",
                    "material": kind in {"functional-deanchored", "version-lineage", "direct-implication"},
                    "reason": f"Checked {kind} against the recorded sources.",
                    "evidence": [self.ref("research/search.md")],
                }
            )
        candidate = {
            "id": "I1",
            "record_locator": "## Candidate I1",
            "formation": {"sources": ["S2"], "operations": ["O4", "O5"], "results": ["R3"], "templates": ["F5"]},
            "contribution": {
                "object_information": "Observed outcomes and estimated nuisance functions.",
                "target": "Uniformly calibrated specification test.",
                "conditions": "Weakly regular nuisance estimation with sample splitting.",
                "procedure": "Bias-aware calibration embedded in the baseline test.",
                "new_capability": "Valid inference under a stated slow-learning regime.",
            },
            "status": "selected",
            "probe": {
                "question": "Does the correction survive the boundary fixture?",
                "criterion": "The analytic discrepancy has the required sign and order.",
                "outcome": "survived",
                "evidence": [self.ref("research/probe.md")],
            },
            "search": {
                "queries": [
                    {"id": "Q1", "mode": "targeted", "query": "bias aware calibration specification test", "sources": ["OpenAlex"], "run_at": "2026-09-27", "records_checked": 14, "outcome": "No direct core overlap in the checked records."},
                    {"id": "Q2", "mode": "deanchored", "query": "uniform testing slow nuisance estimation", "sources": ["Semantic Scholar"], "run_at": "2026-09-27", "records_checked": 18, "outcome": "Located and compared a differently named nearest neighbor."},
                ],
                "coverage_paths": coverage,
                "nearest_neighbors": [
                    {"id": "N1", "source": "doi:10.example/neighbor", "version": "journal-v1", "locator": "Theorem 2 and Appendix B", "role": "mechanism neighbor", "comparison": "Shares calibration but not the target information restriction.", "evidence": [self.ref("research/search.md")]}
                ],
                "stop": {"status": "stop", "reason": "All recorded material paths were checked and further queries did not change the decision.", "unresolved_material_paths": []},
            },
            "decision": {
                "verdict": "recommend",
                "reason": "The core probe survived and no core overlap was identified within the dated scope.",
                "evidence": [self.ref("research/decision.md")],
                "reopen_if": ["A later paper proves the same guarantee under the same information set."],
            },
            "budget": {
                "planned": {"wall_minutes": 90, "cost_usd": None, "compute_hours": 0.1, "source": "Author-set exploration budget."},
                "actual": {"wall_minutes": 64, "cost_usd": None, "compute_hours": 0.05, "source": "Observed search and probe log."},
            },
        }
        return {"schema": PORTFOLIO.SCHEMA, "as_of": "2026-09-27", "record": self.ref("research/idea-mining.md"), "candidates": [candidate]}

    def test_selected_candidate_with_bound_coverage_is_eligible(self):
        result = PORTFOLIO.validate(self.root, self.record)
        self.assertEqual(result["schema"], PORTFOLIO.STATUS_SCHEMA)
        self.assertNotEqual(PORTFOLIO.PORTFOLIO_SCHEMA, PORTFOLIO.STATUS_SCHEMA)
        self.assertTrue(result["recommendation_eligible"])
        self.assertEqual(result["selected"], ["I1"])
        self.assertFalse(result["novelty_guarantee"])

    def test_open_material_frontier_blocks_recommendation(self):
        record = copy.deepcopy(self.record)
        path = next(item for item in record["candidates"][0]["search"]["coverage_paths"] if item["kind"] == "direct-implication")
        path["state"] = "open"
        path["evidence"] = []
        record["candidates"][0]["search"]["stop"] = {"status": "continue", "reason": "A direct implication remains unresolved.", "unresolved_material_paths": ["direct-implication"]}
        result = PORTFOLIO.validate(self.root, record)
        self.assertFalse(result["recommendation_eligible"])
        self.assertTrue(any("open material frontier" in item for item in result["blockers"]))

    def test_deanchored_query_is_a_real_gate_for_selected_candidate(self):
        record = copy.deepcopy(self.record)
        record["candidates"][0]["search"]["queries"] = record["candidates"][0]["search"]["queries"][:1]
        result = PORTFOLIO.validate(self.root, record)
        self.assertFalse(result["recommendation_eligible"])
        self.assertTrue(any("deanchored" in item for item in result["blockers"]))

    def test_rejected_candidate_requires_reopen_condition(self):
        record = copy.deepcopy(self.record)
        candidate = record["candidates"][0]
        candidate["status"] = "rejected"
        candidate["decision"]["verdict"] = "reject"
        candidate["decision"]["reopen_if"] = []
        result = PORTFOLIO.validate(self.root, record)
        self.assertTrue(any("reopen condition" in item for item in result["blockers"]))

    def test_selected_candidate_cannot_hide_an_active_competitor(self):
        record = copy.deepcopy(self.record)
        active = copy.deepcopy(record["candidates"][0])
        active["id"] = "I2"
        active["status"] = "active"
        active["decision"]["verdict"] = "investigate"
        record["candidates"].append(active)
        result = PORTFOLIO.validate(self.root, record)
        self.assertFalse(result["recommendation_eligible"])
        self.assertTrue(any("active candidates" in item for item in result["blockers"]))

    def test_stale_evidence_hash_is_invalid_not_merely_blocked(self):
        self.write("research/search.md", "Changed search record.\n")
        with self.assertRaises(PORTFOLIO.PortfolioError):
            PORTFOLIO.validate(self.root, self.record)

    def test_unknown_usage_is_not_rewritten_as_zero(self):
        record = copy.deepcopy(self.record)
        actual = record["candidates"][0]["budget"]["actual"]
        actual.update({"wall_minutes": None, "cost_usd": None, "compute_hours": None, "source": None})
        result = PORTFOLIO.validate(self.root, record)
        self.assertTrue(result["valid"])

    def test_cli_distinguishes_eligible_blocked_and_invalid(self):
        path = self.root / "research" / "portfolio.json"
        path.write_text(json.dumps(self.record), encoding="utf-8")
        eligible = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", "research/portfolio.json"], capture_output=True, text=True)
        self.assertEqual(eligible.returncode, 0, eligible.stdout + eligible.stderr)
        blocked_record = copy.deepcopy(self.record)
        blocked_record["candidates"][0]["probe"]["outcome"] = "inconclusive"
        path.write_text(json.dumps(blocked_record), encoding="utf-8")
        blocked = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", str(path)], capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        path.write_text("{}", encoding="utf-8")
        invalid = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", str(path)], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()
