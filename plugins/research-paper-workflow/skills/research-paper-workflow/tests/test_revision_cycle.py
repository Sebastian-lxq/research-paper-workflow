"""Behavior tests for the continuous revision controller.

Fixtures are synthetic or deidentified control slices. They test orchestration
invariants, not the scientific correctness of a manuscript or review.
"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CYCLE = load_module("revision_cycle_under_test", ROOT / "scripts/revision_cycle.py")
WORKFLOW = load_module("workflow_state_for_revision_test", ROOT / "scripts/workflow_state.py")


class RevisionCycleFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="revision-cycle-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / ".paper/workflow").mkdir(parents=True)
        (self.root / ".paper/revisions.yaml").write_text(
            json.dumps({"schema_version": 1, "revisions": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.root / "manuscript.md").write_text(
            "# Synthetic manuscript\n\nThe null and statistic are recorded.\n",
            encoding="utf-8",
        )
        self.plan = WORKFLOW.make_plan("theory", "not-applicable")
        (self.root / ".paper/workflow/plan.json").write_text(
            json.dumps(self.plan, indent=2) + "\n", encoding="utf-8"
        )
        self.contract = {
            "schema": CYCLE.CONTRACT_SCHEMA_V2,
            "cycle_id": "cycle-001",
            "mode": "continuous-revision",
            "objective": "Produce a manuscript ready for author review.",
            "manuscript": {"path": "manuscript.md", "version": "draft-v1"},
            "scope": {
                "allowed_paths": ["manuscript.md", "sections", "tables", "code"],
                "locked_paths": [],
                "authorized_operations": [
                    "edit-manuscript",
                    "edit-proof",
                    "edit-simulation-code",
                    "run-local-compute",
                    "update-project-state",
                ],
            },
            "resources": {
                "compute_limit": "bounded local smoke and pre-authorized production inventory",
                "data_access": ["project-local synthetic fixtures"],
                "external_access": False,
            },
            "confidentiality": "local-only",
            "target": CYCLE.TARGET,
            "expert_authorization": {
                "status": "confirmed",
                "primary": "mentor-primary",
                "roundtable_members": ["mentor-primary", "mentor-secondary"],
                "source_locator": "user-message:project-start",
                "one_round_per_issue": True,
            },
            "non_regression": {
                "primary_objectives": [
                    {
                        "id": "OBJ-ready",
                        "description": "Improve the candidate to author-reviewable readiness.",
                        "baseline_locator": "baseline:synthetic-candidate",
                        "improvement_criterion": "All admitted load-bearing issues are closed.",
                    }
                ],
                "protected_invariants": [
                    {
                        "id": "INV-scope",
                        "description": "Preserve the maintained scientific scope.",
                        "baseline_locator": "baseline:synthetic-scope",
                        "preservation_check": "The final scope audit passes.",
                    }
                ],
                "allowed_tradeoffs": [],
                "paired_evidence_requirements": [
                    {
                        "id": "PAIR-ready",
                        "baseline_locator": "baseline:synthetic-candidate",
                        "candidate_locator": "verification:synthetic-candidate",
                        "criterion": "Apply the same readiness checks to both versions.",
                    }
                ],
                "rollback": {
                    "trigger_conditions": ["The protected scope regresses."],
                    "restore_locator": "baseline:synthetic-candidate",
                    "required_action": "rework",
                },
                "whole_candidate_dimensions": ["theory", "integration"],
                "report_path": "verification/non-regression-report.json",
            },
            "stop_conditions": CYCLE.STOP_CONDITIONS,
            "pause_conditions": CYCLE.PAUSE_CONDITIONS,
        }
        CYCLE.initialize(self.root, self.contract, True)

    def tree(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def state(self):
        return CYCLE.load_state(self.root / ".paper/workflow/revision-cycle.json")

    def ledger(self):
        return CYCLE.load_ledger(self.root / ".paper/revisions.yaml")

    def issue(
        self,
        issue_id,
        severity="P1",
        area="theory",
        depends_on=None,
        affected=None,
        root_cause="skill-gap",
    ):
        return {
            "id": issue_id,
            "problem": f"Deidentified problem for {issue_id}.",
            "severity": severity,
            "area": area,
            "source": {"kind": "workflow-audit", "locator": f"audit:{issue_id}"},
            "affected_objects": affected or [f"object:{issue_id}"],
            "depends_on": depends_on or [],
            "acceptance_criteria": [f"A fresh reviewer accepts {issue_id}."],
            "objective_link": f"Issue {issue_id} affects the frozen manuscript objective.",
            "consequence_if_unresolved": f"The candidate would retain the recorded defect for {issue_id}.",
            "admission_basis": "material-research-effect",
            "author_gate": False,
            "reopen_if": ["A prerequisite or bound manuscript version changes."],
            "root_cause": root_cause,
        }

    def add(self, *issues, write=True):
        return CYCLE.add_issues(
            self.root,
            {"schema": CYCLE.ISSUES_SCHEMA_V2, "issues": list(issues)},
            write,
        )

    def select(self):
        return CYCLE.select_next(self.root, True)

    def event(self, action, **fields):
        return CYCLE.apply_event(
            self.root,
            {"schema": CYCLE.EVENT_SCHEMA, "action": action, **fields},
            True,
        )

    def write_review(
        self,
        name,
        *,
        scope,
        issue_id,
        reviewer,
        context,
        verdict="accepted",
        severity="none",
    ):
        evidence = self.root / "evidence" / f"{name}.txt"
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text("Synthetic review evidence.\n", encoding="utf-8")
        state = self.state()
        evidence_paths = [evidence.relative_to(self.root).as_posix()]
        if scope == "full" and verdict == "accepted":
            evidence_paths.append(self.write_non_regression_report())
        review = {
            "schema": CYCLE.REVIEW_SCHEMA,
            "review_id": name,
            "review_scope": scope,
            "issue_id": issue_id,
            "reviewer_id": reviewer,
            "reviewer_context_id": context,
            "candidate_sha256": state["manuscript"]["sha256"],
            "severity": severity,
            "locator": f"review:{name}",
            "evidence": evidence_paths,
            "verdict": verdict,
            "next_action": "" if verdict == "accepted" else "Repair the linked issue and re-review it.",
        }
        path = self.root / "reviews" / f"{name}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        return path.relative_to(self.root).as_posix()

    def write_non_regression_report(self):
        verification = self.root / "verification"
        verification.mkdir(exist_ok=True)
        evidence_names = {
            "objective": "objective.md",
            "invariant": "invariant.md",
            "paired": "paired.md",
            "theory": "theory.md",
            "integration": "integration.md",
        }
        evidence = {}
        for key, name in evidence_names.items():
            path = verification / name
            path.write_text(f"Synthetic {key} evidence.\n", encoding="utf-8")
            relative = path.relative_to(self.root).as_posix()
            evidence[key] = [{"path": relative, "sha256": CYCLE.file_digest(path)}]
        state = self.state()
        report = {
            "schema": CYCLE.NON_REGRESSION_REPORT_SCHEMA,
            "contract_sha256": CYCLE.digest(state["contract"]),
            "candidate_sha256": state["manuscript"]["sha256"],
            "objectives": [{"id": "OBJ-ready", "status": "improved", "evidence": evidence["objective"]}],
            "invariants": [{"id": "INV-scope", "status": "preserved", "evidence": evidence["invariant"]}],
            "tradeoffs": [],
            "paired_evidence": [{"id": "PAIR-ready", "status": "pass", "evidence": evidence["paired"]}],
            "whole_candidate": [
                {"dimension": "theory", "status": "pass", "evidence": evidence["theory"]},
                {"dimension": "integration", "status": "pass", "evidence": evidence["integration"]},
            ],
            "decision": "retain",
        }
        path = self.root / state["contract"]["non_regression"]["report_path"]
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return path.relative_to(self.root).as_posix()

    def implement_active(self, issue_id, worker="writer-1"):
        with (self.root / "manuscript.md").open("a", encoding="utf-8") as stream:
            stream.write(f"\nVerified candidate change for {issue_id}.\n")
        return self.event(
            "implemented",
            issue_id=issue_id,
            worker_id=worker,
            locators=["manuscript.md"],
        )

    def accept_active(self, issue_id, review_name=None):
        name = review_name or f"review-{issue_id}"
        path = self.write_review(
            name,
            scope="issue",
            issue_id=issue_id,
            reviewer=f"reviewer-{issue_id}",
            context=f"context-{issue_id}",
        )
        return CYCLE.record_review(self.root, path, True)

    def workflow_receipt(self, stage):
        evidence = self.root / "workflow-evidence" / f"{stage}.txt"
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text("Synthetic stage evidence.\n", encoding="utf-8")
        relative = evidence.relative_to(self.root).as_posix()
        return {
            "summary": f"Synthetic {stage} evidence.",
            "artifacts": [relative],
            "checks": {
                check: {"state": "pass", "evidence": [relative], "note": "Synthetic pass fixture."}
                for check in WORKFLOW.STAGES[stage]
            },
            "worker_id": "workflow-worker",
            "reviewer_id": "workflow-reviewer" if stage in {"theory", "review", "submission"} else None,
            "next_action": "",
        }

    def complete_workflow_to_delivery(self):
        events = []
        for stage in WORKFLOW.STAGES:
            if stage in self.plan["inactive"] or stage == "submission":
                continue
            event = WORKFLOW.event_for(
                self.root,
                self.plan,
                events,
                stage,
                "ready",
                self.workflow_receipt(stage),
            )
            events.append(event)
        (self.root / ".paper/workflow/events.jsonl").write_text(
            "".join(WORKFLOW.canonical(event) + "\n" for event in events),
            encoding="utf-8",
        )


class InitializationAndQueueTests(RevisionCycleFixture):
    def test_init_preview_is_read_only_and_contract_is_hash_bound(self):
        other = self.root / "other"
        other.mkdir()
        (other / ".paper/workflow").mkdir(parents=True)
        (other / ".paper/revisions.yaml").write_text(
            '{"schema_version": 1, "revisions": []}\n', encoding="utf-8"
        )
        (other / "manuscript.md").write_text("draft\n", encoding="utf-8")
        (other / ".paper/workflow/plan.json").write_text(
            json.dumps(self.plan), encoding="utf-8"
        )
        before = {
            path.relative_to(other).as_posix(): path.read_bytes()
            for path in other.rglob("*") if path.is_file()
        }
        result = CYCLE.initialize(other, self.contract, False)
        self.assertFalse(result["written"])
        self.assertFalse((other / ".paper/workflow/revision-cycle.json").exists())
        self.assertEqual(before, {
            path.relative_to(other).as_posix(): path.read_bytes()
            for path in other.rglob("*") if path.is_file()
        })
        state = self.state()
        self.assertEqual(state["contract_sha256"], CYCLE.digest(state["contract"]))

    def test_dependency_order_beats_severity_and_one_issue_is_active(self):
        self.add(
            self.issue("W1", "P3", "writing"),
            self.issue("T1", "P1", "theory"),
            self.issue("C1", "P0", "research-positioning", depends_on=["T1"]),
        )
        self.assertEqual(self.state()["queue"], ["T1", "C1", "W1"])
        self.assertEqual(self.select()["selected_issue_id"], "T1")
        self.assertEqual(self.state()["active_issue_id"], "T1")
        self.assertEqual([item["status"] for item in self.ledger()["revisions"]], ["queued", "active", "queued"])
        self.assertTrue(self.select()["already_active"])

    def test_collect_only_preview_does_not_add_revision(self):
        before = self.tree()
        result = self.add(self.issue("COLLECT1", "P2", "writing"), write=False)
        self.assertFalse(result["written"])
        self.assertEqual(before, self.tree())
        self.assertEqual(self.ledger()["revisions"], [])

    def test_v2_issue_requires_objective_and_consequence_before_admission(self):
        focused = self.issue("FOCUS1", "P2", "integration")
        focused.update({
            "objective_link": "Keeps the main empirical result aligned with the frozen paper objective.",
            "consequence_if_unresolved": "The abstract would report a result from an obsolete data version.",
            "admission_basis": "material-research-effect",
        })
        result = CYCLE.add_issues(
            self.root,
            {"schema": CYCLE.ISSUES_SCHEMA_V2, "issues": [focused]},
            True,
        )
        self.assertEqual(result["added_issue_ids"], ["FOCUS1"])
        saved = self.ledger()["revisions"][0]
        self.assertEqual(saved["objective_link"], focused["objective_link"])
        self.assertEqual(saved["admission_basis"], "material-research-effect")

        missing = self.issue("FOCUS2", "P3", "writing")
        for field in ("objective_link", "consequence_if_unresolved", "admission_basis"):
            missing.pop(field)
        with self.assertRaisesRegex(CYCLE.CycleError, "v2 issues require"):
            CYCLE.add_issues(
                self.root,
                {"schema": CYCLE.ISSUES_SCHEMA_V2, "issues": [missing]},
                True,
            )

    def test_v2_issue_rejects_unknown_admission_basis(self):
        issue = self.issue("FOCUS3", "P3", "writing")
        issue.update({
            "objective_link": "Improves the stated contribution boundary.",
            "consequence_if_unresolved": "Readers could confuse the result with the nearest procedure.",
            "admission_basis": "polish-for-its-own-sake",
        })
        with self.assertRaisesRegex(CYCLE.CycleError, "unknown admission_basis"):
            CYCLE.add_issues(
                self.root,
                {"schema": CYCLE.ISSUES_SCHEMA_V2, "issues": [issue]},
                True,
            )

    def test_new_cycle_rejects_v1_but_legacy_state_remains_compatible(self):
        legacy_issue = self.issue("LEGACY1", "P2", "integration")
        for field in ("objective_link", "consequence_if_unresolved", "admission_basis"):
            legacy_issue.pop(field)
        package = {"schema": CYCLE.ISSUES_SCHEMA, "issues": [legacy_issue]}
        with self.assertRaisesRegex(CYCLE.CycleError, "requires paper-revision-issues.v2"):
            CYCLE.add_issues(self.root, package, True)

        state_path = self.root / ".paper/workflow/revision-cycle.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.pop("issue_schema")
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        result = CYCLE.add_issues(self.root, package, True)
        self.assertEqual(result["added_issue_ids"], ["LEGACY1"])

    def test_cli_mutation_preview_is_read_only(self):
        self.add(self.issue("CLI1"))
        before = self.tree()
        run = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "scripts/revision_cycle.py"),
                "select",
                "--project",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(json.loads(run.stdout)["written"])
        self.assertEqual(before, self.tree())

    def test_external_ledger_edit_requires_explicit_sync(self):
        self.add(self.issue("X1"))
        ledger_path = self.root / ".paper/revisions.yaml"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["revisions"][0]["status"] = "active"
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(CYCLE.CycleError, "run sync"):
            CYCLE.select_next(self.root, True)
        CYCLE.sync(self.root, True)
        self.assertEqual(self.state()["active_issue_id"], "X1")


class IssueLifecycleTests(RevisionCycleFixture):
    def test_issue_requires_actual_implementation_and_review_before_acceptance(self):
        self.add(self.issue("SIM1", "P1", "simulation", root_cause="execution-miss"))
        self.select()
        report = CYCLE.status_report(self.root, self.state(), self.ledger())
        self.assertIn("SIM1", report["open_p0_p1"])
        self.assertEqual(self.ledger()["revisions"][0]["implementation"]["attempts"], 0)
        self.implement_active("SIM1")
        self.assertEqual(self.ledger()["revisions"][0]["status"], "verifying")
        self.accept_active("SIM1")
        issue = self.ledger()["revisions"][0]
        self.assertEqual(issue["status"], "accepted")
        self.assertEqual(issue["implementation"]["attempts"], 1)
        self.assertTrue(issue["verification"]["review_sha256"])

    def test_adverse_re_review_enables_exactly_one_expert_escalation(self):
        self.add(self.issue("THEORY1", "P0", "theory"))
        self.select()
        self.implement_active("THEORY1")
        review = self.write_review(
            "adverse-theory",
            scope="issue",
            issue_id="THEORY1",
            reviewer="reviewer-a",
            context="fresh-a",
            verdict="rework",
            severity="P0",
        )
        result = CYCLE.record_review(self.root, review, True)
        self.assertTrue(result["expert_escalation_eligible"])
        packet = self.root / "reviews/escalation-packet.json"
        packet.write_text('{"issue_id":"THEORY1"}\n', encoding="utf-8")
        result = self.event("escalate", issue_id="THEORY1", packet_path="reviews/escalation-packet.json")
        self.assertEqual(result["escalation"]["panel"], ["mentor-primary", "mentor-secondary"])
        with self.assertRaisesRegex(CYCLE.CycleError, "already used"):
            self.event("escalate", issue_id="THEORY1", packet_path="reviews/escalation-packet.json")

    def test_compute_overrun_pauses_and_requires_recorded_resume(self):
        self.add(self.issue("SIM2", "P1", "simulation"))
        self.select()
        result = self.event(
            "pause",
            issue_id="SIM2",
            reason_code="compute-budget-exceeded",
            reason="Production matrix exceeds the frozen local budget.",
            source_locator="resource-estimate:v2",
        )
        self.assertEqual(result["pause"]["reason_code"], "compute-budget-exceeded")
        self.assertEqual(self.ledger()["revisions"][0]["status"], "blocked_author")
        with self.assertRaisesRegex(CYCLE.CycleError, "paused"):
            self.select()
        self.event("resume", resolution_locator="user-message:expanded-budget")
        self.assertEqual(self.ledger()["revisions"][0]["status"], "active")

    def test_p0_cannot_be_deferred_and_p3_needs_explicit_nonblocking_reason(self):
        self.add(self.issue("P0X", "P0", "theory"), self.issue("P3X", "P3", "writing"))
        with self.assertRaisesRegex(CYCLE.CycleError, "P2/P3"):
            self.event(
                "defer",
                issue_id="P0X",
                reason="Hard.",
                source_locator="decision:1",
                nonblocking=True,
            )
        with self.assertRaisesRegex(CYCLE.CycleError, "explicitly nonblocking"):
            self.event(
                "defer",
                issue_id="P3X",
                reason="Cosmetic only.",
                source_locator="decision:2",
                nonblocking=False,
            )

    def test_reopening_theory_reopens_accepted_downstream_prose(self):
        self.add(
            self.issue("T", "P1", "theory"),
            self.issue("W", "P2", "writing", depends_on=["T"]),
            self.issue("I", "P2", "integration", depends_on=["W"]),
        )
        for issue_id in ("T", "W", "I"):
            self.select()
            self.implement_active(issue_id, worker=f"worker-{issue_id}")
            self.accept_active(issue_id)
        result = self.event(
            "reopen",
            issue_id="T",
            reason="The theorem statement changed under a new bound.",
            source_locator="proof-ledger:new-bound",
        )
        self.assertEqual(result["reopened_issue_ids"], ["I", "T", "W"])
        self.assertEqual(self.state()["queue"], ["T", "W", "I"])
        self.assertTrue(all(item["status"] == "queued" for item in self.ledger()["revisions"]))


class ConvergenceTests(RevisionCycleFixture):
    def test_two_distinct_clean_reviews_and_workflow_delivery_are_required(self):
        self.complete_workflow_to_delivery()
        self.event(
            "candidate",
            worker_id="final-writer",
            change_locator="candidate-freeze:v1",
            material=True,
        )
        first = self.write_review(
            "full-1",
            scope="full",
            issue_id=None,
            reviewer="reviewer-one",
            context="fresh-context-one",
        )
        CYCLE.record_review(self.root, first, True)
        self.assertFalse(CYCLE.status_report(self.root, self.state(), self.ledger())["ready"])
        second = self.write_review(
            "full-2",
            scope="full",
            issue_id=None,
            reviewer="reviewer-two",
            context="fresh-context-two",
        )
        CYCLE.record_review(self.root, second, True)
        report = CYCLE.status_report(self.root, self.state(), self.ledger())
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["outcome"], CYCLE.TARGET)

    def test_material_edit_invalidates_two_clean_reviews(self):
        self.complete_workflow_to_delivery()
        self.event("candidate", worker_id="writer", change_locator="freeze:1", material=True)
        for index in (1, 2):
            path = self.write_review(
                f"clean-{index}",
                scope="full",
                issue_id=None,
                reviewer=f"reviewer-{index}",
                context=f"context-{index}",
            )
            CYCLE.record_review(self.root, path, True)
        self.assertTrue(CYCLE.status_report(self.root, self.state(), self.ledger())["ready"])
        with (self.root / "manuscript.md").open("a", encoding="utf-8") as stream:
            stream.write("\nMaterial post-review change.\n")
        report = CYCLE.status_report(self.root, self.state(), self.ledger())
        self.assertFalse(report["checks"]["manuscript_hash_current"])
        self.event("candidate", worker_id="writer", change_locator="freeze:2", material=True)
        self.assertEqual(self.state()["clean_reviews"], [])

    def test_same_reviewer_or_context_cannot_supply_both_clean_passes(self):
        self.event("candidate", worker_id="writer", change_locator="freeze", material=True)
        first = self.write_review(
            "independent-1",
            scope="full",
            issue_id=None,
            reviewer="reviewer-one",
            context="context-one",
        )
        CYCLE.record_review(self.root, first, True)
        second = self.write_review(
            "independent-2",
            scope="full",
            issue_id=None,
            reviewer="reviewer-one",
            context="context-two",
        )
        with self.assertRaisesRegex(CYCLE.CycleError, "distinct reviewers"):
            CYCLE.record_review(self.root, second, True)

    def test_retrospective_never_auto_promotes_project_findings_to_global_skill(self):
        self.add(
            self.issue("R1", "P1", "writing", root_cause="skill-gap"),
            self.issue("R2", "P2", "integration", root_cause="skill-gap"),
        )
        report = CYCLE.retrospective(self.root)
        self.assertFalse(report["project_specific_content_included"])
        self.assertTrue(report["manager_handoff"]["required_for_global_change"])
        self.assertTrue(all(not item["global_skill_candidate"] for item in report["patterns"]))
        self.assertNotIn("Deidentified problem", json.dumps(report))


class DeidentifiedHistorySlices(RevisionCycleFixture):
    def test_quantile_contribution_slice_cascades_to_reader_facing_sections(self):
        self.add(
            self.issue("nearest-neighbor", "P1", "research-positioning"),
            self.issue(
                "contribution-language",
                "P1",
                "writing",
                depends_on=["nearest-neighbor"],
                affected=["abstract", "introduction", "conclusion"],
            ),
        )
        self.assertEqual(self.state()["queue"], ["nearest-neighbor", "contribution-language"])
        self.assertEqual(self.select()["selected_issue_id"], "nearest-neighbor")

    def test_simulation_plan_is_not_an_actual_result_without_execution_and_review(self):
        self.add(
            self.issue(
                "simulation-evidence",
                "P1",
                "simulation",
                affected=["code", "result-ledger", "table", "result-prose"],
                root_cause="execution-miss",
            )
        )
        self.select()
        full = self.write_review(
            "premature-full-review",
            scope="full",
            issue_id="simulation-evidence",
            reviewer="reviewer-plan",
            context="context-plan",
            verdict="rework",
            severity="P1",
        )
        with self.assertRaisesRegex(CYCLE.CycleError, "no active issue"):
            CYCLE.record_review(self.root, full, True)
        self.assertEqual(self.ledger()["revisions"][0]["implementation"]["attempts"], 0)

    def test_holdout_theory_change_reopens_only_declared_dependents(self):
        self.add(
            self.issue("bound", "P1", "theory"),
            self.issue("abstract-sync", "P2", "integration", depends_on=["bound"]),
            self.issue("unrelated-style", "P3", "writing"),
        )
        for issue_id in ("bound", "abstract-sync", "unrelated-style"):
            self.select()
            self.implement_active(issue_id)
            self.accept_active(issue_id)
        result = self.event(
            "reopen",
            issue_id="bound",
            reason="Holdout fixture changes the theorem bound.",
            source_locator="holdout:theory-change",
        )
        self.assertEqual(result["reopened_issue_ids"], ["abstract-sync", "bound"])
        statuses = {item["id"]: item["status"] for item in self.ledger()["revisions"]}
        self.assertEqual(statuses["unrelated-style"], "accepted")


if __name__ == "__main__":
    unittest.main()
