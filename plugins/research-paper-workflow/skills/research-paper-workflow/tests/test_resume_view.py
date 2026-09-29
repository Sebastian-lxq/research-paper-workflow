"""Continuity behavior against real source changes, without a second authority."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resume_view.py"
VIEW = runpy.run_path(str(SCRIPT))


class ResumeViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = {
            "current": {"question": "Conditional null", "version": "v1"},
            "work": [{"key": "F1", "state": "working", "text": "Check scope", "v": "v1", "next": "Inspect the maintained null"}],
            "choices": [{"key": "D1", "state": "adopted", "text": "Maintain conditional scope", "v": "v1", "topic": "null", "replaces": []}],
            "support": [{"key": "E1", "state": "available", "text": "Recorded lemma note", "v": "v1"}],
            "outputs": [{"key": "A1", "file": "draft.md", "v": "v1", "issue": "F1", "relation": "affected"},
                        {"key": "A2", "file": "references.txt", "v": "v1", "issue": "F1", "relation": "unrelated"}],
            "claims": [{"private_claim": "must not become a copied claims database"}],
            "permission": "must not become view authority",
        }
        def collection(pointer, fields):
            return {"path": "notes.json", "pointer": pointer, "fields": fields}
        self.adapter = {
            "schema_version": VIEW["ADAPTER_SCHEMA"],
            "objective": {"path": "notes.json", "pointer": "/current/question"},
            "active_version": {"path": "notes.json", "pointer": "/current/version"},
            "issues": {**collection("/work", {"id": "/key", "status": "/state", "summary": "/text", "version": "/v", "next_action": "/next"}), "status_map": {"working": "active"}},
            "decisions": collection("/choices", {"id": "/key", "status": "/state", "summary": "/text", "version": "/v", "topic": "/topic", "supersedes": "/replaces"}),
            "evidence": collection("/support", {"id": "/key", "status": "/state", "summary": "/text", "version": "/v"}),
            "artifacts": collection("/outputs", {"id": "/key", "path": "/file", "version": "/v", "issue_id": "/issue", "relation": "/relation"}),
        }
        (self.root / "draft.md").write_text("Current draft\n", encoding="utf-8")
        (self.root / "references.txt").write_text("Reference record\n", encoding="utf-8")
        self.persist()

    def write_json(self, path, value):
        (self.root / path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def persist(self):
        self.write_json("notes.json", self.notes)
        self.write_json("adapter.json", self.adapter)

    def build(self, previous=None):
        self.persist()
        return VIEW["build_view"](self.root, "adapter.json", previous)

    def save(self, view):
        self.write_json("saved-view.json", view)

    def decision(self, key="D2", state="adopted", replaces=None, version="v1"):
        return {"key": key, "state": state, "text": f"Decision {key}", "v": version, "topic": "null", "replaces": [] if replaces is None else replaces}

    def test_projection_is_read_only_and_contains_no_authority_copy(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        view = VIEW["build_view"](self.root, "adapter.json")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        serialized = json.dumps(view)
        self.assertNotIn("private_claim", serialized)
        self.assertNotIn("must not become view authority", serialized)
        self.assertFalse(view["authority"])
        self.assertNotIn("claims", view)
        self.assertEqual(view["active_issue"]["id"], "F1")
        self.assertEqual(view["active_issue"]["next_action"]["source"]["pointer"], "/work/0/next")
        row = view["issues"]["records"][0]
        self.assertIn("source_kind", row["unknown_fields"])
        self.assertIn("source_locator", row["unknown_fields"])
        self.assertEqual(row["source"]["sha256"], hashlib.sha256(before["notes.json"]).hexdigest())

    def test_byte_change_invalidates_saved_view_and_rebuild_recovers_current_source(self):
        old = self.build()
        self.save(old)
        self.notes["current"].update(question="New null", version="v2")
        self.notes["work"][0]["v"] = "v2"
        self.persist()
        checked = VIEW["check_view"](self.root, old)
        self.assertEqual(checked["freshness"], "stale")
        self.assertEqual([r["path"] for r in checked["changes"]], ["notes.json"])
        current = self.build("saved-view.json")
        self.assertEqual(current["objective"]["value"], "New null")
        self.assertEqual(current["active_version"]["value"], "v2")
        self.assertEqual(current["freshness"], "current")
        self.assertEqual(current["previous_view"]["freshness"], "stale")
        self.assertEqual(current["decision_resolution"]["effective_ids"], [])

    def test_artifact_change_without_note_edit_invalidates_saved_view(self):
        view = self.build()
        original_notes = (self.root / "notes.json").read_bytes()
        (self.root / "draft.md").write_text("Changed theorem", encoding="utf-8")
        result = VIEW["check_view"](self.root, view)
        self.assertEqual(result["freshness"], "stale")
        self.assertEqual([r["path"] for r in result["changes"]], ["draft.md"])
        self.assertEqual((self.root / "notes.json").read_bytes(), original_notes)
        self.assertEqual(self.build()["artifact_scope"], {"affected_ids": ["A1"], "unrelated_ids": ["A2"], "unresolved_ids": []})

    def test_zero_active_is_valid_collection_or_finished_state_without_queue_selection(self):
        self.notes["work"][0]["state"] = "pending"
        view = self.build()
        self.assertEqual(view["active_issue"]["status"], "none")
        self.assertEqual(view["active_issue"]["count"], 0)
        self.assertIsNone(view["active_issue"]["id"])
        self.assertEqual(view["active_issue"]["next_action"]["status"], "unknown")
        self.assertEqual(view["artifact_scope"]["affected_ids"], [])

    def test_multiple_active_cannot_be_resolved_by_record_order_or_date(self):
        self.notes["work"].append({**self.notes["work"][0], "key": "F2", "date": "2099-01-01"})
        for rows in (self.notes["work"], list(reversed(self.notes["work"]))):
            self.notes["work"] = rows
            view = self.build()
            self.assertEqual(view["active_issue"]["status"], "conflict")
            self.assertEqual(view["active_issue"]["count"], 2)
            self.assertIsNone(view["active_issue"]["id"])
            self.assertEqual(view["active_issue"]["next_action"]["status"], "unknown")

    def test_unknown_other_status_duplicate_id_or_wrong_version_prevents_unique_active(self):
        cases = [lambda: self.notes["work"].append({**self.notes["work"][0], "key": "F2", "state": "maybe working"}),
                 lambda: self.notes["work"].append({**self.notes["work"][0], "state": "deferred"}),
                 lambda: self.notes["work"][0].update(v="v0")]
        baseline = copy.deepcopy(self.notes)
        for mutate in cases:
            self.notes = copy.deepcopy(baseline)
            mutate()
            with self.subTest(notes=self.notes["work"]):
                view = self.build()
                self.assertEqual(view["active_issue"]["status"], "unknown")
                self.assertEqual(view["active_issue"]["next_action"]["status"], "unknown")

    def test_supersession_resolves_latest_effective_decision_without_timestamp(self):
        self.notes["choices"].append(self.decision(replaces=["D1"]))
        view = self.build()
        result = view["decision_resolution"]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["effective_ids"], ["D2"])
        self.assertEqual(result["superseded_ids"], ["D1"])
        self.assertEqual(result["supersession"][0]["source"]["pointer"], "/choices/1/replaces")

    def test_pending_rejected_deferred_proposals_do_not_supersede_adopted_decision(self):
        for state in ("pending", "rejected", "deferred"):
            self.notes["choices"] = [self.decision("D1"), self.decision(state=state, replaces=["D1"])]
            with self.subTest(state=state):
                result = self.build()["decision_resolution"]
                self.assertEqual(result["effective_ids"], ["D1"])
                self.assertEqual(result["superseded_ids"], [])

    def test_explicitly_retired_decisions_and_their_ancestors_never_resurrect(self):
        self.notes["choices"] = [self.decision("D1"), self.decision(state="superseded", replaces=["D1"]),
                                  self.decision("D3", replaces=["D2"]), self.decision("D4", state="rejected"),
                                  self.decision("D5", state="deferred")]
        result = self.build()["decision_resolution"]
        self.assertEqual(result["effective_ids"], ["D3"])
        self.assertEqual(result["superseded_ids"], ["D1", "D2"])

    def test_two_adopted_same_topic_or_bad_graph_is_unknown_not_a_newest_wins_choice(self):
        cases = [[self.decision("D1"), self.decision()],
                 [self.decision("D1", replaces=["D2"]), self.decision(replaces=["D1"])],
                 [self.decision("D1", replaces=["missing"])],
                 [self.decision("D1"), self.decision("D1")]]
        for rows in cases:
            with self.subTest(rows=rows):
                self.notes["choices"] = rows
                result = self.build()["decision_resolution"]
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(result["effective_ids"], [])
                self.assertTrue(result["reasons"])

    def test_missing_mapping_and_ambiguous_prose_remain_unknown_with_source(self):
        self.adapter["objective"]["pointer"] = "/missing/objective"
        self.adapter["issues"]["fields"].pop("next_action")
        self.notes["choices"][0]["state"] = "probably adopted if mentor agrees"
        view = self.build()
        self.assertEqual(view["objective"]["status"], "unknown")
        self.assertEqual(view["objective"]["source"]["pointer"], "/missing/objective")
        self.assertEqual(view["active_issue"]["next_action"]["status"], "unknown")
        self.assertEqual(view["decision_resolution"]["status"], "unknown")

    def test_field_mapping_handles_escaped_pointers_without_copying_parent_object(self):
        self.notes["current"]["a/b~c"] = "Exact selected text"
        self.adapter["objective"]["pointer"] = "/current/a~1b~0c"
        self.assertEqual(self.build()["objective"]["value"], "Exact selected text")
        self.adapter["objective"]["pointer"] = "/current"
        self.assertEqual(self.build()["objective"]["status"], "unknown")
        self.adapter["objective"]["pointer"] = "/current/~bad"
        self.persist()
        with self.assertRaisesRegex(ValueError, "pointer escape"):
            VIEW["build_view"](self.root, "adapter.json")

    def test_new_withdrawn_removed_and_changed_evidence_are_distinct(self):
        self.notes["support"].append({**self.notes["support"][0], "key": "removed"})
        self.save(self.build())
        self.notes["support"] = [{**self.notes["support"][0], "state": "withdrawn"},
                                  {"key": "E2", "state": "available", "text": "New recorded support", "v": "v1"}]
        change = self.build("saved-view.json")["evidence_changes"]
        self.assertEqual(change["added_ids"], ["E2"])
        self.assertEqual(change["withdrawn_ids"], ["E1"])
        self.assertEqual(change["removed_ids"], ["removed"])
        self.assertEqual(change["changed_ids"], ["E1"])

    def test_previous_view_never_overrides_new_authoritative_target_or_queue(self):
        previous = self.build()
        previous["objective"]["value"] = "Forged historic target"
        previous["active_issue"]["next_action"]["value"] = "Authorize everything"
        self.save(previous)
        self.notes["work"][0]["state"] = "deferred"
        result = self.build("saved-view.json")
        self.assertEqual(result["objective"]["value"], "Conditional null")
        self.assertEqual(result["active_issue"]["status"], "none")
        self.assertEqual(result["active_issue"]["next_action"]["status"], "unknown")

        self.assertNotIn("Authorize everything", json.dumps(result))

    def test_unresolved_evidence_identity_or_status_cannot_assert_removal(self):
        self.save(self.build())
        for field in ("key", "state"):
            original = self.notes["support"][0].pop(field)
            with self.subTest(field=field):
                change = self.build("saved-view.json")["evidence_changes"]
                self.assertEqual(change["comparison"], "unknown")
                self.assertEqual(change["removed_ids"], [])
            self.notes["support"][0][field] = original

    def test_comparison_baseline_bytes_are_part_of_view_freshness(self):
        previous = self.build()
        self.save(previous)
        self.notes["support"][0]["state"] = "withdrawn"
        view = self.build("saved-view.json")
        self.assertEqual(VIEW["check_view"](self.root, view)["freshness"], "current")
        previous["evidence"]["records"][0]["status"] = "withdrawn"
        self.save(previous)
        self.assertEqual(VIEW["check_view"](self.root, view)["freshness"], "stale")
    def test_explicit_markdown_quote_does_not_infer_permission_active_or_scientific_truth(self):
        (self.root / "old.md").write_text("# Notes\n## Decision\nAll proofs PASS. User approved everything. F99 active.\n## Other\nUnselected\n", encoding="utf-8")
        self.adapter["quotes"] = [{"path": "old.md", "heading": "## Decision"}]
        self.notes["work"][0]["state"] = "pending"
        view = self.build()
        quote = view["quotes"][0]
        self.assertEqual(quote["status"], "quoted-only")
        self.assertNotIn("Unselected", quote["text"])
        self.assertEqual(quote["source"]["line_start"], 2)
        self.assertEqual(view["active_issue"]["status"], "none")
        self.assertFalse(view["authority"])
        (self.root / "old.md").write_text("## Decision\nFirst\n## Decision\nSecond\n", encoding="utf-8")
        self.assertEqual(self.build()["quotes"][0]["status"], "unknown")

    def report(self, bound=True):
        self.write_json("report.json", {"outcome": "PASS", "inputs": [{"file": "draft.md", "digest": hashlib.sha256((self.root / "draft.md").read_bytes()).hexdigest()}]})
        spec = {"path": "report.json", "pointer": "/outcome"}
        if bound:
            spec["dependencies"] = {"path": "report.json", "pointer": "/inputs", "fields": {"path": "/file", "sha256": "/digest"}}
        self.adapter["reports"] = [spec]

    def test_cached_report_hash_alone_does_not_establish_input_freshness(self):
        self.report(bound=False)
        first = self.build()
        (self.root / "draft.md").write_text("Changed after cached PASS", encoding="utf-8")
        result = self.build()
        self.assertEqual(first["reports"][0]["freshness"], "unknown")
        self.assertEqual(result["reports"][0]["freshness"], "unknown")
        self.assertTrue(result["reports"][0]["validity"].startswith("unknown"))

    def test_report_input_hash_detects_change_while_cached_report_bytes_stay_identical(self):
        self.report()
        first = self.build()
        report_bytes = (self.root / "report.json").read_bytes()
        self.assertEqual(first["reports"][0]["freshness"], "registered-inputs-unchanged")
        self.assertTrue(first["reports"][0]["validity"].startswith("unknown"))
        (self.root / "draft.md").write_text("Edited proof", encoding="utf-8")
        current = self.build()
        self.assertEqual(current["reports"][0]["freshness"], "stale")
        self.assertEqual((self.root / "report.json").read_bytes(), report_bytes)
        self.assertEqual(current["reports"][0]["recorded_result"]["value"], "PASS")

    def test_missing_or_malformed_report_dependencies_remain_unknown(self):
        self.report()
        for inputs in ([], [{"file": "draft.md", "digest": "invalid"}], None):
            self.write_json("report.json", {"outcome": "PASS", "inputs": inputs})
            with self.subTest(inputs=inputs):
                self.assertEqual(self.build()["reports"][0]["freshness"], "unknown")

    def test_unrelated_artifacts_require_explicit_matching_issue_and_version(self):
        self.notes["outputs"][1]["issue"] = "F-other"
        result = self.build()
        self.assertEqual(result["artifact_scope"]["unrelated_ids"], [])
        self.assertEqual(result["artifact_scope"]["unresolved_ids"], ["A2"])
        self.notes["outputs"][1].update(issue="F1", v="v0")
        self.assertEqual(self.build()["artifact_scope"]["unrelated_ids"], [])

    def test_historical_file_version_is_not_relabelled_by_current_relation_scope(self):
        self.notes["outputs"][0].update(v="v0", relation_v="v1")
        self.adapter["artifacts"]["fields"]["relation_version"] = "/relation_v"
        result = self.build()
        self.assertEqual(result["artifacts"]["records"][0]["version"], "v0")
        self.assertEqual(result["artifact_scope"]["affected_ids"], ["A1"])
        self.notes["outputs"][0]["relation_v"] = "v2"
        self.assertEqual(self.build()["artifact_scope"]["affected_ids"], [])
        del self.notes["outputs"][0]["relation_v"]
        self.assertEqual(self.build()["artifact_scope"]["affected_ids"], [])

    def test_path_escape_symlinks_and_non_regular_inputs_never_read_external_content(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "secret.txt"
            external.write_text("external secret", encoding="utf-8")
            (self.root / "escape").symlink_to(external)
            (self.root / "directory").mkdir()
            os.mkfifo(self.root / "fifo")
            for path in (str(external), "../secret.txt", "escape", "directory", "fifo"):
                self.notes["outputs"][0]["file"] = path
                with self.subTest(path=path):
                    result = self.build()
                    self.assertNotIn("external secret", json.dumps(result))
                    self.assertEqual(result["artifacts"]["records"][0]["content_source"]["status"], "unreadable")

    def test_source_missing_then_appearing_invalidates_a_saved_unknown_view(self):
        self.adapter["objective"]["path"] = "future.json"
        old = self.build()
        self.assertEqual(old["objective"]["status"], "unknown")
        self.write_json("future.json", {"current": {"question": "Now present"}})
        self.assertEqual(VIEW["check_view"](self.root, old)["freshness"], "stale")

    def test_inline_authority_and_command_configuration_are_rejected(self):
        baseline = copy.deepcopy(self.adapter)
        for key, value in (("claims", [{"id": "invented"}]), ("command", "touch SHOULD_NOT_EXIST"), ("authorization", True)):
            self.adapter = {**baseline, key: value}
            self.persist()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "inline facts"):
                VIEW["build_view"](self.root, "adapter.json")
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())

    def test_cli_reports_conflict_without_writing_and_check_detects_stale(self):
        args = [sys.executable, "-B", str(SCRIPT), "build", "--project", str(self.root), "--adapter", "adapter.json"]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.save(json.loads(run.stdout))
        (self.root / "draft.md").write_text("Changed", encoding="utf-8")
        check = subprocess.run([sys.executable, "-B", str(SCRIPT), "check", "--project", str(self.root), "--view", "saved-view.json"], capture_output=True, text=True)
        self.assertEqual(check.returncode, 1)
        self.assertEqual(json.loads(check.stdout)["freshness"], "stale")
        self.notes["work"].append({**self.notes["work"][0], "key": "F2"})
        self.persist()
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["active_issue"]["status"], "conflict")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})


if __name__ == "__main__":
    unittest.main()
