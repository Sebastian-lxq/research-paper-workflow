import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/revision_cycle.py"
SPEC = importlib.util.spec_from_file_location("revision_cycle_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NonRegressionContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "main.tex").write_text("baseline manuscript\n", encoding="utf-8")
        for name in ("objective.md", "invariant.md", "tradeoff.md", "paired.md", "theory.md", "integration.md"):
            (self.root / name).write_text(f"evidence for {name}\n", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def contract(self):
        return {
            "schema": MODULE.CONTRACT_SCHEMA_V2,
            "cycle_id": "test-cycle",
            "mode": "continuous-revision",
            "objective": "Improve the frozen candidate without regressing protected science.",
            "manuscript": {"path": "main.tex", "version": "draft-1"},
            "scope": {
                "allowed_paths": ["main.tex"],
                "locked_paths": [],
                "authorized_operations": ["edit-manuscript"],
            },
            "resources": {
                "compute_limit": "no new compute",
                "data_access": [],
                "external_access": False,
            },
            "confidentiality": "local-only",
            "target": MODULE.TARGET,
            "expert_authorization": {
                "status": "disabled",
                "primary": None,
                "roundtable_members": [],
                "source_locator": "not-applicable",
                "one_round_per_issue": True,
            },
            "non_regression": {
                "primary_objectives": [
                    {
                        "id": "OBJ-main",
                        "description": "Improve the main objective.",
                        "baseline_locator": "objective.md#baseline",
                        "improvement_criterion": "The paired check passes.",
                    }
                ],
                "protected_invariants": [
                    {
                        "id": "INV-main",
                        "description": "Preserve the maintained scientific object.",
                        "baseline_locator": "invariant.md#baseline",
                        "preservation_check": "The current audit finds no change.",
                    }
                ],
                "allowed_tradeoffs": [
                    {
                        "id": "TRD-main",
                        "benefit": "Improve exposition.",
                        "allowed_cost": "One additional paragraph.",
                        "bound": "At most one paragraph.",
                        "evidence_requirement": "Compare rendered versions.",
                    }
                ],
                "paired_evidence_requirements": [
                    {
                        "id": "PAIR-main",
                        "baseline_locator": "paired.md#baseline",
                        "candidate_locator": "paired.md#candidate",
                        "criterion": "Apply the same audit to both versions.",
                    }
                ],
                "rollback": {
                    "trigger_conditions": ["A protected invariant regresses."],
                    "restore_locator": "invariant.md#baseline",
                    "required_action": "rework",
                },
                "whole_candidate_dimensions": ["theory", "integration"],
                "report_path": "non-regression-report.json",
            },
            "stop_conditions": list(MODULE.STOP_CONDITIONS),
            "pause_conditions": list(MODULE.PAUSE_CONDITIONS),
        }

    def evidence(self, path):
        return [{"path": path, "sha256": MODULE.file_digest(self.root / path)}]

    def passing_report(self, contract):
        return {
            "schema": MODULE.NON_REGRESSION_REPORT_SCHEMA,
            "contract_sha256": MODULE.digest(contract),
            "candidate_sha256": MODULE.file_digest(self.root / "main.tex"),
            "objectives": [{"id": "OBJ-main", "status": "improved", "evidence": self.evidence("objective.md")}],
            "invariants": [{"id": "INV-main", "status": "preserved", "evidence": self.evidence("invariant.md")}],
            "tradeoffs": [{"id": "TRD-main", "status": "within-bound", "evidence": self.evidence("tradeoff.md")}],
            "paired_evidence": [{"id": "PAIR-main", "status": "pass", "evidence": self.evidence("paired.md")}],
            "whole_candidate": [
                {"dimension": "theory", "status": "pass", "evidence": self.evidence("theory.md")},
                {"dimension": "integration", "status": "pass", "evidence": self.evidence("integration.md")},
            ],
            "decision": "retain",
        }

    def test_passing_report_is_bound_and_satisfied(self):
        contract = MODULE.validate_contract(self.contract(), self.root, allow_legacy=False)
        manuscript = MODULE.snapshot(self.root, "main.tex")
        report = self.passing_report(contract)
        result = MODULE.validate_non_regression_report(report, self.root, contract, manuscript)
        self.assertTrue(result["satisfied"])

        (self.root / contract["non_regression"]["report_path"]).write_text(
            json.dumps(report), encoding="utf-8"
        )
        status = MODULE.non_regression_status(self.root, contract, manuscript)
        self.assertTrue(status["satisfied"])
        self.assertEqual(status["report"]["sha256"], MODULE.file_digest(self.root / "non-regression-report.json"))

    def test_regressed_invariant_blocks_retain(self):
        contract = MODULE.validate_contract(self.contract(), self.root, allow_legacy=False)
        report = self.passing_report(contract)
        report["invariants"][0]["status"] = "regressed"
        result = MODULE.validate_non_regression_report(
            report, self.root, contract, MODULE.snapshot(self.root, "main.tex")
        )
        self.assertFalse(result["satisfied"])
        self.assertFalse(result["checks"]["invariants_preserved"])

    def test_stale_evidence_is_rejected(self):
        contract = MODULE.validate_contract(self.contract(), self.root, allow_legacy=False)
        report = self.passing_report(contract)
        (self.root / "objective.md").write_text("changed after the report\n", encoding="utf-8")
        with self.assertRaises(MODULE.CycleError):
            MODULE.validate_non_regression_report(
                report, self.root, contract, MODULE.snapshot(self.root, "main.tex")
            )

    def test_new_cycle_rejects_legacy_contract_but_legacy_remains_readable(self):
        legacy = copy.deepcopy(self.contract())
        legacy["schema"] = MODULE.CONTRACT_SCHEMA_V1
        del legacy["non_regression"]
        MODULE.validate_contract(copy.deepcopy(legacy), self.root, allow_legacy=True)
        with self.assertRaisesRegex(MODULE.CycleError, "new revision cycles require"):
            MODULE.validate_contract(legacy, self.root, allow_legacy=False)

    def test_clean_full_review_must_consume_current_report(self):
        contract = MODULE.validate_contract(self.contract(), self.root, allow_legacy=False)
        report = self.passing_report(contract)
        (self.root / "non-regression-report.json").write_text(json.dumps(report), encoding="utf-8")
        (self.root / ".paper/workflow").mkdir(parents=True)
        ledger = {"schema_version": 1, "revisions": []}
        ledger_path = self.root / ".paper/revisions.yaml"
        ledger_path.write_bytes(MODULE.encoded(ledger))
        state = {
            "schema": MODULE.CYCLE_SCHEMA,
            "cycle_id": contract["cycle_id"],
            "issue_schema": MODULE.ISSUES_SCHEMA_V2,
            "contract": contract,
            "contract_sha256": MODULE.digest(contract),
            "manuscript": MODULE.snapshot(self.root, "main.tex"),
            "queue": [],
            "active_issue_id": None,
            "clean_reviews": [],
            "escalations": [],
            "pause": None,
            "candidate_worker_ids": [],
            "revision_ledger_sha256": MODULE.file_digest(ledger_path),
            "created_at": MODULE.utc_now(),
            "updated_at": MODULE.utc_now(),
        }
        (self.root / ".paper/workflow/revision-cycle.json").write_bytes(MODULE.encoded(state))
        (self.root / "reviews").mkdir()
        (self.root / "reviews/full.md").write_text("clean full review\n", encoding="utf-8")
        review = {
            "schema": MODULE.REVIEW_SCHEMA,
            "review_id": "FULL-R1",
            "review_scope": "full",
            "issue_id": None,
            "reviewer_id": "reviewer-1",
            "reviewer_context_id": "fresh-context-1",
            "candidate_sha256": MODULE.file_digest(self.root / "main.tex"),
            "severity": "none",
            "locator": "reviews/full.md",
            "evidence": ["reviews/full.md", "non-regression-report.json"],
            "verdict": "accepted",
            "next_action": "",
        }
        review_path = self.root / "reviews/full.json"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        result = MODULE.record_review(self.root, "reviews/full.json", False)
        self.assertEqual(result["clean_review_count"], 1)
        self.assertEqual(
            result["review"]["non_regression_report_sha256"],
            MODULE.file_digest(self.root / "non-regression-report.json"),
        )

        review["evidence"] = ["reviews/full.md"]
        review_path.write_text(json.dumps(review), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.CycleError, "must include the non-regression report"):
            MODULE.record_review(self.root, "reviews/full.json", False)

    def test_report_change_invalidates_prior_clean_reviews(self):
        contract = MODULE.validate_contract(self.contract(), self.root, allow_legacy=False)
        report_path = self.root / "non-regression-report.json"
        report_path.write_text(json.dumps(self.passing_report(contract)), encoding="utf-8")
        (self.root / ".paper/workflow").mkdir(parents=True)
        ledger = {"schema_version": 1, "revisions": []}
        ledger_path = self.root / ".paper/revisions.yaml"
        ledger_path.write_bytes(MODULE.encoded(ledger))
        (self.root / "reviews").mkdir()
        clean_reviews = []
        for index in (1, 2):
            path = self.root / f"reviews/full-{index}.json"
            path.write_text(f"review {index}\n", encoding="utf-8")
            clean_reviews.append(
                {
                    "path": f"reviews/full-{index}.json",
                    "sha256": MODULE.file_digest(path),
                    "reviewer_id": f"reviewer-{index}",
                    "reviewer_context_id": f"fresh-context-{index}",
                    "candidate_sha256": MODULE.file_digest(self.root / "main.tex"),
                    "non_regression_report_sha256": MODULE.file_digest(report_path),
                }
            )
        state = {
            "schema": MODULE.CYCLE_SCHEMA,
            "cycle_id": contract["cycle_id"],
            "issue_schema": MODULE.ISSUES_SCHEMA_V2,
            "contract": contract,
            "contract_sha256": MODULE.digest(contract),
            "manuscript": MODULE.snapshot(self.root, "main.tex"),
            "queue": [],
            "active_issue_id": None,
            "clean_reviews": clean_reviews,
            "escalations": [],
            "pause": None,
            "candidate_worker_ids": [],
            "revision_ledger_sha256": MODULE.file_digest(ledger_path),
            "created_at": MODULE.utc_now(),
            "updated_at": MODULE.utc_now(),
        }
        original_workflow_status = MODULE.workflow_status
        MODULE.workflow_status = lambda root: {
            "outcome": MODULE.TARGET,
            "stages": {
                "manuscript": "ready",
                "verification": "ready",
                "review": "ready",
                "revision": "ready",
                "delivery": "ready",
            },
        }
        try:
            self.assertTrue(MODULE.status_report(self.root, state, ledger)["ready"])
            report_path.write_text(json.dumps(self.passing_report(contract), indent=2), encoding="utf-8")
            changed = MODULE.status_report(self.root, state, ledger)
            self.assertTrue(changed["non_regression"]["satisfied"])
            self.assertFalse(changed["checks"]["two_independent_clean_reviews"])
            self.assertFalse(changed["ready"])
        finally:
            MODULE.workflow_status = original_workflow_status


if __name__ == "__main__":
    unittest.main()
