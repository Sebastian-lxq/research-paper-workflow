"""Tests for append-only operational telemetry and control summaries."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "research_operations.py"
SPEC = importlib.util.spec_from_file_location("research_operations_under_test", SCRIPT)
OPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPS)


class ResearchOperationsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="research-operations-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "research").mkdir()
        (self.root / "research" / "output.md").write_text("Observed output.\n", encoding="utf-8")

    def event(self, state="started", **changes):
        body = {
            "schema": OPS.SCHEMA,
            "operation_id": "literature-search-1",
            "stage": "literature",
            "activity": "Search and verify the nearest-neighbor frontier.",
            "state": state,
            "recorded_at": "2026-09-27T09:00:00+08:00",
            "worker_id": "primary-worker",
            "usage": {"wall_seconds": None, "tokens": None, "cost_usd": None, "compute_seconds": None, "source": None},
            "provider": "OpenAlex",
            "artifacts": [],
            "blocker": None,
            "next_action": "Run the deanchored query." if state == "started" else None,
        }
        body.update(changes)
        if state in {"failed", "blocked"} and "blocker" not in changes:
            body["blocker"] = "The provider returned an incomplete page."
            body["next_action"] = "Retry through a second scholarly index."
        return body

    def event_v2(self, operation_id="simulation-production-1", state="started", **changes):
        body = {
            "schema": OPS.SCHEMA_V2,
            "operation_id": operation_id,
            "stage": "simulation",
            "activity": "Run the frozen production simulation.",
            "state": state,
            "recorded_at": "2026-09-28T09:00:00+08:00",
            "worker_id": "local-simulator",
            "usage": {"wall_seconds": None, "tokens": 0, "cost_usd": 0, "compute_seconds": None, "source": "Local process; no model call."},
            "provider": "local",
            "artifacts": [],
            "blocker": None,
            "next_action": "Wait for the process terminal event." if state in {"started", "waiting"} else None,
            "dependencies": [],
            "wait": None,
        }
        if state == "waiting":
            body["wait"] = {
                "kind": "process",
                "handle": "session-42",
                "resume_condition": "The process exits and the result manifest is present.",
                "dependent_actions_suspended": True,
                "next_check_at": None,
            }
        body.update(changes)
        return body

    def append(self, supplied, events):
        event = OPS.next_event(self.root, supplied, events)
        folder, path, _ = OPS.state_paths(self.root)
        folder.mkdir(parents=True, exist_ok=True)
        OPS.atomic(path, "".join(OPS.canonical(item) + "\n" for item in events + [event]))
        return events + [event]

    def test_lifecycle_aggregates_only_latest_observed_usage(self):
        events = self.append(self.event(), [])
        finished = self.event(
            "succeeded",
            recorded_at="2026-09-27T09:05:00+08:00",
            usage={"wall_seconds": 300.5, "tokens": 2400, "cost_usd": 0.42, "compute_seconds": 12.0, "source": "Provider response and local timer."},
            artifacts=["research/output.md"],
            next_action="Compare the verified neighbor with the candidate contribution vector.",
        )
        events = self.append(finished, events)
        loaded = OPS.load(self.root)
        self.assertEqual(loaded, events)
        status = OPS.summarize(self.root, loaded)
        self.assertEqual(status["operation_count"], 1)
        self.assertEqual(status["usage"]["tokens"]["observed_total"], 2400)
        self.assertEqual(status["usage"]["tokens"]["known_operations"], 1)
        self.assertEqual(status["attention"], [])

    def test_unknown_usage_remains_explicit(self):
        events = self.append(self.event("succeeded", next_action=None), [])
        status = OPS.summarize(self.root, events)
        for metric in OPS.METRICS:
            self.assertEqual(status["usage"][metric]["observed_total"], 0)
            self.assertEqual(status["usage"][metric]["unknown_operations"], 1)

    def test_blocker_and_next_action_surface_in_status(self):
        events = self.append(self.event("blocked"), [])
        status = OPS.summarize(self.root, events)
        self.assertEqual(status["attention"][0]["state"], "blocked")
        self.assertIn("second scholarly index", status["attention"][0]["next_action"])

    def test_terminal_operation_cannot_be_reopened_silently(self):
        events = self.append(self.event("succeeded", next_action=None), [])
        with self.assertRaises(OPS.OperationsError):
            OPS.next_event(self.root, self.event("started", recorded_at="2026-09-27T10:00:00+08:00"), events)

    def test_waiting_operation_records_handle_and_surfaces_attention(self):
        events = self.append(self.event_v2(), [])
        events = self.append(
            self.event_v2(
                state="waiting",
                recorded_at="2026-09-28T09:01:00+08:00",
            ),
            events,
        )
        status = OPS.summarize(self.root, events)
        self.assertEqual(status["schema"], "research-operations-status.v2")
        self.assertEqual(status["attention"][0]["state"], "waiting")
        self.assertEqual(status["attention"][0]["wait"]["handle"], "session-42")
        self.assertIn("waiting on process handle session-42", OPS.markdown(status))

    def test_waiting_requires_suspending_dependent_actions(self):
        event = self.event_v2(state="waiting")
        event["wait"]["dependent_actions_suspended"] = False
        with self.assertRaisesRegex(OPS.OperationsError, "dependent_actions_suspended"):
            OPS.next_event(self.root, event, [])

    def test_dependent_operation_cannot_start_until_waited_operation_succeeds(self):
        events = self.append(self.event_v2(state="waiting"), [])
        downstream = self.event_v2(
            operation_id="write-simulation-results",
            dependencies=["simulation-production-1"],
            activity="Write result-dependent manuscript claims.",
            worker_id="primary-worker",
        )
        with self.assertRaisesRegex(OPS.OperationsError, "before dependency"):
            OPS.next_event(self.root, downstream, events)

    def test_independent_operation_can_continue_while_simulation_waits(self):
        events = self.append(self.event_v2(state="waiting"), [])
        independent = self.event_v2(
            operation_id="verify-bibliography",
            dependencies=[],
            stage="literature",
            activity="Verify bibliography metadata independent of simulation results.",
            worker_id="primary-worker",
        )
        event = OPS.next_event(self.root, independent, events)
        self.assertEqual(event["state"], "started")

    def test_v1_cannot_smuggle_a_waiting_state_without_a_handle(self):
        with self.assertRaisesRegex(OPS.OperationsError, "waiting requires"):
            OPS.next_event(self.root, self.event("waiting"), [])

    def test_artifact_mutation_is_reported_not_hidden(self):
        events = self.append(self.event("succeeded", artifacts=["research/output.md"], next_action=None), [])
        (self.root / "research" / "output.md").write_text("Changed output.\n", encoding="utf-8")
        status = OPS.summarize(self.root, events)
        self.assertEqual(status["stale_artifacts"][0]["reason"], "hash-changed")

    def test_hash_chain_tampering_is_rejected(self):
        self.append(self.event("succeeded", next_action=None), [])
        _, path, _ = OPS.state_paths(self.root)
        value = json.loads(path.read_text())
        value["activity"] = "Tampered activity"
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        with self.assertRaises(OPS.OperationsError):
            OPS.load(self.root)

    def test_rehashed_malformed_stored_event_is_still_rejected(self):
        events = self.append(self.event("succeeded", next_action=None), [])
        malformed = copy.deepcopy(events[0])
        malformed["usage"]["tokens"] = -1
        malformed["sha256"] = OPS.digest({key: value for key, value in malformed.items() if key != "sha256"})
        _, path, _ = OPS.state_paths(self.root)
        path.write_text(OPS.canonical(malformed) + "\n", encoding="utf-8")
        with self.assertRaises(OPS.OperationsError):
            OPS.load(self.root)

    def test_cli_preview_write_and_markdown_status(self):
        event_path = self.root / "research" / "event.json"
        event_path.write_text(json.dumps(self.event("succeeded", next_action=None)), encoding="utf-8")
        preview = subprocess.run([sys.executable, "-B", str(SCRIPT), "record", "--project", str(self.root), "--event", "research/event.json"], capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        self.assertFalse((self.root / ".paper" / "workflow" / "operations.jsonl").exists())
        written = subprocess.run([sys.executable, "-B", str(SCRIPT), "record", "--project", str(self.root), "--event", str(event_path), "--write"], capture_output=True, text=True)
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        status = subprocess.run([sys.executable, "-B", str(SCRIPT), "status", "--project", str(self.root), "--format", "markdown"], capture_output=True, text=True)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertIn("Research operations status", status.stdout)
        self.assertIn("unknown 1", status.stdout)


if __name__ == "__main__":
    unittest.main()
