"""Behavior tests for project-local workflow receipts, using temporary projects.

The text artifacts are synthetic test fixtures, never scientific evidence. API
tests exercise stage prerequisites and freshness; CLI tests separately exercise
read-only previews, persistence, track isolation, and process exit status.
"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow_state.py"
SPEC = importlib.util.spec_from_file_location("workflow_state_under_test", SCRIPT)
WORKFLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW)

EARLY_STAGES = ("framing", "ideas", "literature", "design")
PROSE_STAGES = ("manuscript", "verification", "review", "revision", "delivery")


class TemporaryWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workflow-state-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan = WORKFLOW.make_plan()
        self.events = []

    def artifact(
        self, name, content="Synthetic test artifact, not a research finding.\n"
    ):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def receipt(self, stage, state="ready"):
        if state == "ready":
            name = f"evidence/{stage}.txt"
            if not (self.root / name).exists():
                self.artifact(name)
            paths = [name]
            checks = {
                check: {
                    "state": "pass",
                    "evidence": paths[:],
                    "note": "Synthetic acceptance fixture.",
                }
                for check in WORKFLOW.STAGES[stage]
            }
            next_action = ""
        else:
            paths, checks = [], {}
            next_action = (
                "Complete the recorded missing prerequisite and recheck this stage."
            )
        return {
            "summary": f"Synthetic {stage} {state} receipt",
            "artifacts": paths,
            "checks": checks,
            "worker_id": "test-worker",
            "reviewer_id": "independent-test-reviewer"
            if stage in {"theory", "review", "submission"}
            else None,
            "next_action": next_action,
        }

    def record(self, stage, state="ready", receipt=None):
        event = WORKFLOW.event_for(
            self.root,
            self.plan,
            self.events,
            stage,
            state,
            self.receipt(stage, state) if receipt is None else receipt,
        )
        self.events.append(event)
        return event

    def status(self):
        return WORKFLOW.analyze(self.root, self.plan, self.events)

    def through_design(self):
        for stage in EARLY_STAGES:
            self.record(stage)

    def complete_draft(self):
        for stage in WORKFLOW.STAGES:
            if stage not in self.plan["inactive"] and stage not in {
                "simulation_run",
                "submission",
            }:
                self.record(stage)

    def refresh_prose(self):
        for stage in PROSE_STAGES:
            self.record(stage)

    def persist_api_state(self, track="main"):
        folder = WORKFLOW.directory(self.root, track)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "plan.json").write_text(json.dumps(self.plan), encoding="utf-8")
        (folder / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in self.events), encoding="utf-8"
        )
        return folder

    def tree(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            if path.is_file()
            else None
            for path in self.root.rglob("*")
        }

    def cli(self, command, *args):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                command,
                "--project",
                str(self.root),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        body = json.loads(result.stdout) if result.stdout.strip() else None
        return result, body

    def receipt_file(self, stage="framing", state="ready"):
        receipt = self.receipt(stage, state)
        path = self.root / f"receipt-{stage}.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path


class WorkflowPathsTests(TemporaryWorkflow):
    def test_complete_methods_draft_with_simulations_deferred(self):
        self.complete_draft()
        result = self.status()
        self.assertEqual(result["outcome"], "manuscript-ready-except-simulations")
        self.assertEqual(result["stages"]["delivery"], "ready")
        self.assertEqual(result["stages"]["simulation_run"], "deferred")
        self.assertEqual(result["stages"]["submission"], "pending")
        self.assertNotIn("submission", result["next_runnable"])
        self.assertEqual(
            result["scientific_certification"], "not-established-by-this-tool"
        )
        with self.assertRaises(WORKFLOW.WorkflowError):
            self.record("submission")

    def test_explicit_deferred_simulation_has_resume_action_and_cannot_release(self):
        self.complete_draft()
        receipt = self.receipt("simulation_run", "deferred")
        receipt[
            "next_action"
        ] = "Resume the frozen production simulation from remaining replication IDs."
        self.record("simulation_run", "deferred", receipt)
        # New simulation availability information requires acknowledging it in prose.
        self.assertEqual(self.status()["stages"]["manuscript"], "stale")
        self.refresh_prose()
        result = self.status()
        self.assertEqual(result["outcome"], "manuscript-ready-except-simulations")
        self.assertIn("simulation_run", result["deferred"])
        self.assertEqual(
            result["next_actions"]["simulation_run"], receipt["next_action"]
        )

    def test_theory_without_simulations_can_reach_distinct_submission_candidate(self):
        self.plan = WORKFLOW.make_plan("theory", "not-applicable")
        self.complete_draft()
        result = self.status()
        self.assertEqual(result["outcome"], "manuscript-ready-for-author-review")
        for stage in ("empirical", "simulation_design", "simulation_run"):
            self.assertEqual(result["stages"][stage], "not-applicable")
        self.assertNotIn("simulation_run", self.events[-5]["observed"])
        self.record("submission")
        self.assertEqual(self.status()["outcome"], "submission-candidate")

    def test_missing_empirical_data_is_not_waived_by_deferred_simulations(self):
        self.plan = WORKFLOW.make_plan("empirical", "deferred")
        self.through_design()
        self.record("simulation_design")
        receipt = self.receipt("empirical", "blocked")
        receipt[
            "next_action"
        ] = "Obtain the authorized dataset and construct the analysis sample."
        self.record("empirical", "blocked", receipt)
        result = self.status()
        self.assertEqual(result["stages"]["empirical"], "blocked")
        self.assertEqual(result["stages"]["simulation_run"], "deferred")
        self.assertEqual(result["outcome"], "in-progress")
        self.assertNotIn("manuscript", result["next_runnable"])
        with self.assertRaises(WORKFLOW.WorkflowError):
            self.record("manuscript")
        with self.assertRaises(WORKFLOW.WorkflowError):
            self.record("empirical", "deferred")

    def test_empirical_and_hybrid_types_cannot_disable_empirical_branch(self):
        for paper_type in ("empirical", "hybrid"):
            with self.subTest(paper_type=paper_type):
                with self.assertRaises(WORKFLOW.WorkflowError):
                    WORKFLOW.make_plan(paper_type, "deferred", False)

    def test_inactive_stages_cannot_accept_receipts(self):
        self.plan = WORKFLOW.make_plan("theory", "not-applicable")
        for stage in ("simulation_run", "empirical"):
            with self.subTest(stage=stage):
                with self.assertRaises(WORKFLOW.WorkflowError):
                    self.record(stage, "active")

    def test_nonproduction_work_cannot_be_deferred(self):
        for stage in ("theory", "manuscript", "verification", "review"):
            with self.subTest(stage=stage):
                with self.assertRaises(WORKFLOW.WorkflowError):
                    self.record(stage, "deferred")

    def test_ready_cannot_skip_prerequisite_stage(self):
        with self.assertRaises(WORKFLOW.WorkflowError):
            self.record("ideas")
        self.assertEqual(self.events, [])

    def test_fresh_blocked_receipt_remains_blocked_with_unfinished_prerequisite(self):
        # Waiting for a prerequisite is execution state, not evidence staleness.
        self.record("ideas", "blocked")
        result = self.status()
        self.assertEqual(result["stages"]["ideas"], "blocked")
        self.assertNotIn("ideas", result["next_runnable"])

    def test_early_simulation_deferral_is_not_immediately_stale(self):
        self.record("simulation_run", "deferred")
        result = self.status()
        self.assertEqual(result["stages"]["simulation_run"], "deferred")
        self.assertIn("simulation_run", result["deferred"])


class WorkflowFreshnessTests(TemporaryWorkflow):
    def test_result_receipt_arrival_stales_manuscript_and_actual_descendants(self):
        self.complete_draft()
        self.record("simulation_run")
        result = self.status()
        for stage in PROSE_STAGES:
            self.assertEqual(result["stages"][stage], "stale", stage)
        for stage in ("design", "theory", "simulation_design", "simulation_run"):
            self.assertEqual(result["stages"][stage], "ready", stage)
        self.assertEqual(result["outcome"], "in-progress")
        self.refresh_prose()
        self.assertEqual(self.status()["outcome"], "manuscript-ready-for-author-review")
        self.record("submission")
        self.assertEqual(self.status()["outcome"], "submission-candidate")

    def test_bound_result_file_change_stales_prose_without_new_receipt(self):
        self.complete_draft()
        self.record("simulation_run")
        self.refresh_prose()
        self.record("submission")
        before_event_count = len(self.events)
        self.artifact(
            "evidence/simulation_run.txt",
            "Changed numerical outputs in a synthetic fixture.\n",
        )
        result = self.status()
        self.assertEqual(len(self.events), before_event_count)
        self.assertEqual(result["stages"]["simulation_run"], "stale")
        for stage in (*PROSE_STAGES, "submission"):
            self.assertEqual(result["stages"][stage], "stale", stage)
        self.assertEqual(result["stages"]["theory"], "ready")
        self.assertEqual(result["outcome"], "in-progress")

    def test_theory_file_change_spares_independent_empirical_branch(self):
        self.plan = WORKFLOW.make_plan("methods", "deferred", empirical=True)
        self.complete_draft()
        self.artifact("evidence/theory.txt", "Changed synthetic statement or proof.\n")
        result = self.status()
        for stage in ("theory", "simulation_design", *PROSE_STAGES):
            self.assertEqual(result["stages"][stage], "stale", stage)
        self.assertEqual(result["stages"]["empirical"], "ready")
        self.assertEqual(result["stages"]["design"], "ready")

    def test_unrelated_file_changes_do_not_stale_existing_receipts(self):
        self.complete_draft()
        before = self.status()
        self.artifact("notes/unrelated.txt", "Unrelated administrative note.\n")
        self.assertEqual(self.status(), before)
        self.artifact("notes/unrelated.txt", "Edited unrelated administrative note.\n")
        self.assertEqual(self.status(), before)

    def test_new_theory_receipt_with_unchanged_files_reopens_consumers(self):
        self.complete_draft()
        self.record("theory")
        result = self.status()
        self.assertEqual(result["stages"]["theory"], "ready")
        self.assertEqual(result["stages"]["design"], "ready")
        for stage in ("simulation_design", *PROSE_STAGES):
            self.assertEqual(result["stages"][stage], "stale", stage)

    def test_missing_bound_artifact_is_reported_as_stale(self):
        self.complete_draft()
        (self.root / "evidence/theory.txt").unlink()
        result = self.status()
        self.assertEqual(result["stages"]["theory"], "stale")
        self.assertTrue(
            any("missing" in reason for reason in result["reasons"]["theory"])
        )
        self.assertEqual(result["stages"]["delivery"], "stale")


class WorkflowEvidenceTests(TemporaryWorkflow):
    def test_ready_requires_each_check_and_nonempty_actual_evidence(self):
        original = self.receipt("framing")
        mutations = []
        no_artifact = copy.deepcopy(original)
        no_artifact["artifacts"] = []
        mutations.append(no_artifact)
        no_check = copy.deepcopy(original)
        no_check["checks"] = {}
        mutations.append(no_check)
        no_evidence = copy.deepcopy(original)
        no_evidence["checks"]["scope"]["evidence"] = []
        mutations.append(no_evidence)
        outside = copy.deepcopy(original)
        outside["checks"]["scope"]["evidence"] = ["outside.txt"]
        mutations.append(outside)
        for state in ("partial", "fail", "not-applicable"):
            modified = copy.deepcopy(original)
            modified["checks"]["scope"]["state"] = state
            mutations.append(modified)
        for receipt in mutations:
            with self.subTest(receipt=receipt):
                with self.assertRaises(WORKFLOW.WorkflowError):
                    WORKFLOW.validate_receipt(receipt, "framing", "ready")

    def test_proof_review_and_submission_require_distinct_reviewers(self):
        for stage in ("theory", "review", "submission"):
            for reviewer in (None, "test-worker"):
                with self.subTest(stage=stage, reviewer=reviewer):
                    receipt = self.receipt(stage)
                    receipt["reviewer_id"] = reviewer
                    with self.assertRaises(WORKFLOW.WorkflowError):
                        WORKFLOW.validate_receipt(receipt, stage, "ready")
            WORKFLOW.validate_receipt(self.receipt(stage), stage, "ready")

    def test_nonready_receipt_needs_a_resume_action(self):
        receipt = self.receipt("framing", "blocked")
        receipt["next_action"] = "  "
        with self.assertRaises(WORKFLOW.WorkflowError):
            WORKFLOW.validate_receipt(receipt, "framing", "blocked")

    def test_receipt_metadata_does_not_replace_missing_artifact(self):
        receipt = self.receipt("framing")
        (self.root / receipt["artifacts"][0]).unlink()
        with self.assertRaises(WORKFLOW.WorkflowError):
            self.record("framing", receipt=receipt)

    def test_unsafe_or_self_referential_evidence_paths_are_rejected(self):
        for path in (
            "../outside.txt",
            "/absolute.txt",
            ".paper/workflow/plan.json",
            "evidence/../outside.txt",
        ):
            with self.subTest(path=path):
                with self.assertRaises(WORKFLOW.WorkflowError):
                    WORKFLOW.relative(path)

    def test_symlink_evidence_is_rejected(self):
        target = self.artifact("evidence/real.txt")
        link = self.root / "evidence/link.txt"
        link.symlink_to(target)
        with self.assertRaises(WORKFLOW.WorkflowError):
            WORKFLOW.snapshot(self.root, "evidence/link.txt")


class WorkflowCliTests(TemporaryWorkflow):
    def test_init_preview_does_not_create_or_change_paper_state(self):
        self.artifact(
            ".paper/paper_state.yaml", '{"author_state":"preserve exactly"}\n'
        )
        before = self.tree()
        result, body = self.cli(
            "init", "--paper-type", "methods", "--simulation", "deferred"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(body["schema"], "paper-workflow-plan.v1")
        self.assertEqual(self.tree(), before)

    def test_init_write_preserves_existing_paper_ledgers_and_refuses_reinitialization(
        self,
    ):
        original = self.artifact(
            ".paper/claims.yaml", '{"claims":[{"id":"existing-author-claim"}]}\n'
        )
        original_bytes = original.read_bytes()
        result, _ = self.cli("init", "--write")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(original.read_bytes(), original_bytes)
        before = self.tree()
        again, body = self.cli(
            "init",
            "--paper-type",
            "theory",
            "--simulation",
            "not-applicable",
            "--write",
        )
        self.assertEqual(again.returncode, 2)
        self.assertEqual(body["outcome"], "invalid-state")
        self.assertEqual(self.tree(), before)

    def test_record_preview_does_not_append_events_or_modify_state(self):
        self.assertEqual(self.cli("init", "--write")[0].returncode, 0)
        receipt = self.receipt_file()
        before = self.tree()
        result, body = self.cli(
            "record",
            "--stage",
            "framing",
            "--state",
            "ready",
            "--receipt",
            str(receipt),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(body["stage"], "framing")
        self.assertEqual(self.tree(), before)
        self.assertFalse((WORKFLOW.directory(self.root) / "events.jsonl").exists())

    def test_record_write_is_loadable_and_status_remains_in_progress(self):
        self.assertEqual(self.cli("init", "--write")[0].returncode, 0)
        receipt = self.receipt_file()
        result, event = self.cli(
            "record",
            "--stage",
            "framing",
            "--state",
            "ready",
            "--receipt",
            str(receipt),
            "--write",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan, events = WORKFLOW.load(self.root)
        self.assertEqual(events, [event])
        self.assertEqual(plan, self.plan)
        before = self.tree()
        status, body = self.cli("status")
        self.assertEqual(status.returncode, 1)
        self.assertEqual(body["stages"]["framing"], "ready")
        self.assertEqual(body["outcome"], "in-progress")
        self.assertEqual(self.tree(), before)

    def test_status_exit_codes_distinguish_deferred_draft_and_submission_candidate(
        self,
    ):
        self.complete_draft()
        self.persist_api_state()
        result, body = self.cli("status")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(body["outcome"], "manuscript-ready-except-simulations")
        self.record("simulation_run")
        self.refresh_prose()
        self.record("submission")
        self.persist_api_state()
        result, body = self.cli("status")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(body["outcome"], "submission-candidate")

    def test_malformed_receipt_fails_without_mutating_workflow(self):
        self.assertEqual(self.cli("init", "--write")[0].returncode, 0)
        receipt = self.artifact("broken-receipt.json", "{not-json")
        before = self.tree()
        result, body = self.cli(
            "record",
            "--stage",
            "framing",
            "--state",
            "ready",
            "--receipt",
            str(receipt),
            "--write",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(body["outcome"], "invalid-state")
        self.assertEqual(self.tree(), before)

    def test_status_without_workflow_returns_invalid_state(self):
        result, body = self.cli("status")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(body["outcome"], "invalid-state")

    def test_tampered_plan_and_event_chain_fail_closed(self):
        self.record("framing")
        folder = self.persist_api_state()
        plan_path = folder / "plan.json"
        original_plan = plan_path.read_text()
        plan = json.loads(original_plan)
        plan["simulation"] = "not-applicable"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        self.assertEqual(self.cli("status")[0].returncode, 2)
        plan_path.write_text(original_plan, encoding="utf-8")
        event = copy.deepcopy(self.events[0])
        event["receipt"]["summary"] = "Changed without updating the chain."
        (folder / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.assertEqual(self.cli("status")[0].returncode, 2)


class WorkflowTrackTests(TemporaryWorkflow):
    def test_named_track_is_isolated_and_cannot_overwrite_main(self):
        self.assertEqual(self.cli("init", "--write")[0].returncode, 0)
        receipt = self.receipt_file()
        self.assertEqual(
            self.cli(
                "record",
                "--stage",
                "framing",
                "--state",
                "ready",
                "--receipt",
                str(receipt),
                "--write",
            )[0].returncode,
            0,
        )
        main_before = WORKFLOW.load(self.root)
        result, _ = self.cli(
            "init",
            "--track",
            "scope-v2",
            "--paper-type",
            "theory",
            "--simulation",
            "not-applicable",
            "--write",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(WORKFLOW.load(self.root), main_before)
        named_plan, named_events = WORKFLOW.load(self.root, "scope-v2")
        self.assertEqual(named_plan["paper_type"], "theory")
        self.assertEqual(named_events, [])
        self.assertEqual(
            WORKFLOW.directory(self.root, "scope-v2"),
            self.root / ".paper/workflow/tracks/scope-v2",
        )
        status, body = self.cli("status", "--track", "scope-v2")
        self.assertEqual(status.returncode, 1)
        self.assertEqual(body["stages"]["framing"], "pending")
        before = self.tree()
        duplicate, _ = self.cli("init", "--track", "scope-v2", "--write")
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual(self.tree(), before)

    def test_named_track_can_be_created_before_main_without_blocking_main(self):
        result, _ = self.cli(
            "init",
            "--track",
            "scope-v2",
            "--paper-type",
            "theory",
            "--simulation",
            "not-applicable",
            "--write",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        named_before = WORKFLOW.load(self.root, "scope-v2")
        main, body = self.cli("init", "--write")
        self.assertEqual(main.returncode, 0, body)
        self.assertEqual(WORKFLOW.load(self.root, "scope-v2"), named_before)
        self.assertEqual(WORKFLOW.load(self.root)[0]["paper_type"], "methods")

    def test_named_track_preview_is_nonmutating(self):
        self.assertEqual(self.cli("init", "--write")[0].returncode, 0)
        before = self.tree()
        result, _ = self.cli(
            "init", "--track", "future-scope", "--paper-type", "theory"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tree(), before)

    def test_track_argument_cannot_escape_workflow_directory(self):
        for track in ("../escape", "/absolute", "a/b", "."):
            with self.subTest(track=track):
                before = self.tree()
                result, body = self.cli("init", "--track", track, "--write")
                self.assertEqual(result.returncode, 2)
                self.assertEqual(body["outcome"], "invalid-state")
                self.assertEqual(self.tree(), before)

    def test_empirical_scope_cannot_be_disabled_through_cli(self):
        for kind in ("empirical", "hybrid"):
            with self.subTest(kind=kind):
                result, body = self.cli(
                    "init",
                    "--paper-type",
                    kind,
                    "--empirical",
                    "not-applicable",
                    "--write",
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(body["outcome"], "invalid-state")
                self.assertFalse(WORKFLOW.directory(self.root).exists())


if __name__ == "__main__":
    unittest.main()
