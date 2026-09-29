"""Exercise real subprocesses, failures, input lineage and append-only decisions."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "exploration_probe.py"
PROBE = runpy.run_path(str(SCRIPT))


class ExplorationProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.baseline = self.project / "baseline.txt"
        self.baseline.write_text("original input\n", encoding="utf-8")
        self.output = self.root / "probe-1"

    def run_probe(self, code="print('complete')", **changes):
        options = dict(project=self.project, probe_id="probe-1", baselines=["baseline.txt"],
                       question="Does the proposed change pass this fixture?",
                       criterion="Inspect the recorded output and failure lineage",
                       timeout=5.0, output=self.output, command=[sys.executable, "-c", code])
        options.update(changes)
        return PROBE["run_probe"](**options)

    def test_real_execution_has_cwd_logs_and_actual_duration(self):
        result = self.run_probe("import os,sys,time; print(os.getcwd()); print('diagnostic',file=sys.stderr); time.sleep(.06)")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["returncode"], 0)
        self.assertGreaterEqual(result["wall_seconds"], .06)
        self.assertEqual((self.output / "stdout.txt").read_text().strip(), str(self.project))
        self.assertEqual((self.output / "stderr.txt").read_text().strip(), "diagnostic")
        self.assertEqual(json.loads((self.output / "run.json").read_text()), result)
        self.assertIsNone(result["scientific_score"])
        self.assertEqual(result["usage"], {"tokens": None, "cost": None, "source": None})
        self.assertFalse(result["baselines"][0]["changed"])

    def test_argv_is_never_interpreted_as_shell(self):
        payload = "$(touch injected); echo unsafe"
        self.run_probe(command=[sys.executable, "-c", "import sys; print(sys.argv[1])", payload])
        self.assertEqual((self.output / "stdout.txt").read_text().strip(), payload)
        self.assertFalse((self.project / "injected").exists())

    def test_failure_preserves_nonzero_exit_and_logs_without_score(self):
        result = self.run_probe("import sys; print('partial',flush=True); print('failed',file=sys.stderr); sys.exit(7)")
        self.assertEqual((result["status"], result["returncode"]), ("failed", 7))
        self.assertEqual((self.output / "stdout.txt").read_text().strip(), "partial")
        self.assertIsNone(result["scientific_score"])

    def test_launch_error_is_recorded(self):
        result = self.run_probe(command=[str(self.project / "missing-command")])
        self.assertEqual(result["status"], "launch_error")
        self.assertIsNone(result["returncode"])
        self.assertIn("FileNotFoundError", result["error"])

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup")
    def test_timeout_stops_child_group_and_retains_partial_output(self):
        child = "import time,pathlib; time.sleep(.7); pathlib.Path('escaped.txt').write_text('bad')"
        code = ("import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
                "print('before timeout',flush=True); time.sleep(10)")
        result = self.run_probe(code, timeout=.2)
        self.assertEqual(result["status"], "timed_out")
        self.assertLess(result["returncode"], 0)
        self.assertGreaterEqual(result["wall_seconds"], .2)
        self.assertLess(result["wall_seconds"], 2)
        self.assertEqual((self.output / "stdout.txt").read_text().strip(), "before timeout")
        time.sleep(.8)
        self.assertFalse((self.project / "escaped.txt").exists())

    def test_snapshot_precedes_command_and_tracks_modified_input(self):
        before = self.baseline.read_bytes()
        result = self.run_probe("from pathlib import Path; Path('baseline.txt').write_text('modified')")
        entry = result["baselines"][0]
        self.assertEqual((self.output / entry["snapshot"]).read_bytes(), before)
        self.assertEqual(entry["sha256_before"], hashlib.sha256(before).hexdigest())
        self.assertEqual(entry["sha256_after"], hashlib.sha256(b"modified").hexdigest())
        self.assertTrue(entry["changed"])

    def test_deleted_input_is_preserved_as_changed_with_error(self):
        result = self.run_probe("from pathlib import Path; Path('baseline.txt').unlink()")
        entry = result["baselines"][0]
        self.assertTrue(entry["changed"])
        self.assertIsNone(entry["sha256_after"])
        self.assertIsNotNone(entry["after_error"])
        self.assertTrue((self.output / entry["snapshot"]).exists())

    def test_decisions_append_without_rewriting_run_or_prior_events(self):
        self.run_probe()
        original = (self.output / "run.json").read_bytes()
        first = PROBE["decide"](self.output, "inconclusive", "Fixture is limited", ["baseline.txt"])
        previous = (self.output / "decisions.jsonl").read_bytes()
        second = PROBE["decide"](self.output, "revise", "Add a boundary fixture")
        current = (self.output / "decisions.jsonl").read_bytes()
        self.assertTrue(current.startswith(previous))
        self.assertEqual([json.loads(line) for line in current.splitlines()], [first, second])
        self.assertEqual((self.output / "run.json").read_bytes(), original)
        self.assertEqual(first["evidence"][0]["sha256"], hashlib.sha256(self.baseline.read_bytes()).hexdigest())

    def test_invalid_requests_never_launch(self):
        cases = [{"timeout": value} for value in (0, -1, float("nan"), float("inf"))]
        cases += [{"probe_id": "../escape"}, {"baselines": []}, {"baselines": ["missing"]},
                  {"baselines": ["../external"]}, {"question": " "}, {"command": []}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_probe(**changes)
            self.assertFalse(self.output.exists())

    def test_existing_output_is_never_overwritten(self):
        self.run_probe()
        original = (self.output / "run.json").read_bytes()
        with self.assertRaises(ValueError):
            self.run_probe("raise RuntimeError('must not run')")
        self.assertEqual((self.output / "run.json").read_bytes(), original)

    def test_symlink_input_and_output_parent_are_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("external")
        (self.project / "link.txt").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.run_probe(baselines=["link.txt"])
        (self.root / "alias").symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_probe(output=self.root / "alias" / "new")
        self.assertFalse((self.project / "new").exists())

    def test_decision_symlink_cannot_modify_external_file(self):
        self.run_probe()
        external = self.root / "external.txt"
        external.write_text("keep")
        (self.output / "decisions.jsonl").symlink_to(external)
        with self.assertRaises(ValueError):
            PROBE["decide"](self.output, "retain", "Inspect fixture")
        self.assertEqual(external.read_text(), "keep")

    def test_cli_failure_exit_and_decision(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "run", "--project", str(self.project),
                                 "--id", "cli-1", "--baseline", "baseline.txt", "--question", "Q",
                                 "--criterion", "C", "--timeout", "3", "--output", str(self.output),
                                 "--", sys.executable, "-c", "raise SystemExit(9)"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["returncode"], 9)
        decided = subprocess.run([sys.executable, str(SCRIPT), "decide", str(self.output),
                                  "--decision", "discard", "--reason", "Observed exit failure"],
                                 capture_output=True, text=True)
        self.assertEqual(decided.returncode, 0, decided.stderr)
        self.assertEqual(json.loads(decided.stdout)["decision"], "discard")


if __name__ == "__main__":
    unittest.main()
