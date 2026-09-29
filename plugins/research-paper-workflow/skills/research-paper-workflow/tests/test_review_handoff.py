"""Behavioral tests for staged disclosure and immutable byte bindings."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/review_handoff.py"
SPEC = importlib.util.spec_from_file_location("review_handoff", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "bundle"
        for name, content in {"old.md": "OLD-MANUSCRIPT-SECRET", "new.md": "NEW-MANUSCRIPT-SECRET",
                              "checks.txt": "EVIDENCE-SECRET", "reply.md": "RESPONSE-SECRET"}.items():
            (self.root / name).write_text(content)
        self.spec = {"schema_version": "review-handoff-spec.v1", "project_root": str(self.root),
                     "issues": [{"issue_id": "R1", "criterion": "Uniformity justified"},
                                {"issue_id": "R2", "criterion": "Dependence handled"}],
                     "old": ["old.md"], "new": ["new.md"], "evidence": ["checks.txt"],
                     "response": ["reply.md"]}
        self.criteria = {"schema_version": "review-handoff-criteria.v1",
                         "issues": copy.deepcopy(self.spec["issues"])}
        self.evidence = {"schema_version": "review-handoff-evidence.v1", "issues": [
            {"issue_id": "R1", "status": "resolved", "reason": "Bound stated explicitly",
             "evidence_locators": [{"path": "new.md", "locator": "section 2"}]},
            {"issue_id": "R2", "status": "unresolved", "reason": "Dependence condition remains absent",
             "evidence_locators": [{"path": "new.md", "locator": "assumptions"}]}]}
        self.spec_path = self.dump("spec.json", self.spec)
        self.criteria_path = self.dump("criteria.json", self.criteria)
        self.evidence_path = self.dump("evidence.json", self.evidence)

    def dump(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data))
        return path

    def prepare(self):
        return review.prepare(self.spec_path, self.out)

    def stage2(self):
        self.prepare()
        return review.advance(self.out, self.criteria_path, 2)

    def snapshot(self):
        return {p.relative_to(self.out).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.out.rglob("*") if p.is_file()}

    def test_disclosure_happens_in_order_and_unresolved_is_preserved(self):
        self.prepare()
        first = (self.out / "stage1/packet.json").read_text()
        self.assertNotIn("SECRET", first)
        self.assertNotIn("reply.md", first)
        self.assertEqual(list((self.out / "stage1").iterdir()), [self.out / "stage1/packet.json"])
        self.assertFalse((self.out / "stage2").exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(["reveal", str(self.out)]), 2)
        review.advance(self.out, self.criteria_path, 2)
        second = b"".join(p.read_bytes() for p in (self.out / "stage2").rglob("*") if p.is_file())
        self.assertIn(b"NEW-MANUSCRIPT-SECRET", second)
        self.assertIn(b"EVIDENCE-SECRET", second)
        self.assertNotIn(b"RESPONSE-SECRET", second)
        self.assertNotIn(b"reply.md", second)
        self.assertFalse((self.out / "stage3").exists())
        review.advance(self.out, self.evidence_path, 3)
        packet = review.load(self.out / "stage3/packet.json")
        self.assertEqual(packet["frozen_evidence_verdict"]["issues"][1]["status"], "unresolved")
        self.assertEqual((self.out / "stage3/files/response/reply.md").read_text(), "RESPONSE-SECRET")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(["reveal", str(self.out)]), 0)

    def test_all_original_source_changes_refuse_advance(self):
        self.prepare()
        for path in (self.spec_path, self.root / "old.md", self.root / "new.md",
                     self.root / "checks.txt", self.root / "reply.md"):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "source changed"):
                    review.advance(self.out, self.criteria_path, 2)
                self.assertFalse((self.out / "stage2").exists())
                path.write_bytes(original)

    def test_frozen_criteria_and_copy_tamper_refuse_reveal(self):
        self.stage2()
        for relative in ("stage2/result.json", "stage2/packet.json", "stage2/files/new/new.md"):
            with self.subTest(relative=relative):
                path = self.out / relative
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "frozen file changed"):
                    review.advance(self.out, self.evidence_path, 3)
                self.assertFalse((self.out / "stage3").exists())
                path.write_bytes(original)

    def test_submitted_result_drift_is_bound(self):
        self.stage2()
        self.criteria_path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "source changed"):
            review.verify(self.out)

    def test_frozen_evidence_drift_is_bound(self):
        self.stage2()
        review.advance(self.out, self.evidence_path, 3)
        path = self.out / "stage3/result.json"
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "frozen file changed"):
            review.verify(self.out)

    def test_exact_criteria_coverage(self):
        self.prepare()
        for issues in (self.criteria["issues"][:1], self.criteria["issues"] * 2,
                       self.criteria["issues"] + [{"issue_id": "R3", "criterion": "Extra"}]):
            self.dump("criteria.json", {**self.criteria, "issues": issues})
            with self.assertRaises(ValueError):
                review.advance(self.out, self.criteria_path, 2)
        self.assertFalse((self.out / "stage2").exists())

    def test_exact_evidence_coverage(self):
        self.stage2()
        for issues in (self.evidence["issues"][:1], self.evidence["issues"] * 2,
                       self.evidence["issues"] + [{**self.evidence["issues"][0], "issue_id": "R3"}]):
            self.dump("evidence.json", {**self.evidence, "issues": issues})
            with self.assertRaises(ValueError):
                review.advance(self.out, self.evidence_path, 3)
        self.assertFalse((self.out / "stage3").exists())

    def test_evidence_requires_status_reason_and_registered_locators(self):
        self.stage2()
        for field, value in (("status", "PASS"), ("reason", " "), ("evidence_locators", []),
                             ("evidence_locators", [{"path": "reply.md", "locator": "line 1"}]),
                             ("evidence_locators", [{"path": "new.md", "locator": ""}])):
            result = copy.deepcopy(self.evidence)
            result["issues"][0][field] = value
            self.dump("evidence.json", result)
            with self.assertRaises(ValueError):
                review.advance(self.out, self.evidence_path, 3)
        self.assertFalse((self.out / "stage3").exists())

    def test_path_escapes_rejected_before_bundle_creation(self):
        outside = self.root.parent / (self.root.name + "-external.txt")
        outside.write_text("OUTSIDE")
        self.addCleanup(outside.unlink)
        (self.root / "escape.md").symlink_to(outside)
        for bad in (str(outside), "../" + outside.name, "escape.md", "./old.md"):
            self.spec["old"] = [bad]
            self.dump("spec.json", self.spec)
            with self.assertRaises(ValueError):
                self.prepare()
            self.assertFalse(self.out.exists())

    def test_response_alias_in_evidence_rejected(self):
        (self.root / "alias.md").symlink_to(self.root / "reply.md")
        self.spec["evidence"] = ["alias.md"]
        self.dump("spec.json", self.spec)
        with self.assertRaisesRegex(ValueError, "aliased"):
            self.prepare()

    def test_symlink_retarget_and_packet_symlink_rejected(self):
        (self.root / "old-link.md").symlink_to(self.root / "old.md")
        self.spec["old"] = ["old-link.md"]
        self.dump("spec.json", self.spec)
        self.prepare()
        link = self.root / "old-link.md"
        link.unlink()
        link.symlink_to(self.root / "new.md")
        with self.assertRaisesRegex(ValueError, "source changed"):
            review.verify(self.out)
        link.unlink()
        link.symlink_to(self.root / "old.md")
        packet = self.out / "stage1/packet.json"
        copy_path = self.root / "packet-copy.json"
        copy_path.write_bytes(packet.read_bytes())
        packet.unlink()
        packet.symlink_to(copy_path)
        with self.assertRaises(ValueError):
            review.verify(self.out)

    def test_verify_and_reveal_are_read_only(self):
        self.stage2()
        review.advance(self.out, self.evidence_path, 3)
        before = self.snapshot()
        self.assertEqual(review.verify(self.out)["stage"], 3)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(["verify", str(self.out)]), 0)
            self.assertEqual(review.main(["reveal", str(self.out)]), 0)
        self.assertEqual(before, self.snapshot())

    def test_existing_bundle_and_stage_are_never_overwritten(self):
        self.stage2()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.prepare()
        with self.assertRaises(ValueError):
            review.advance(self.out, self.criteria_path, 2)
        self.assertEqual(before, self.snapshot())

    def test_unexpected_file_and_incomplete_stage_refused(self):
        self.prepare()
        extra = self.out / "stage1/extra.txt"
        extra.write_text("unsealed")
        with self.assertRaises(ValueError):
            review.verify(self.out)
        extra.unlink()
        (self.out / "stage2").mkdir()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            review.verify(self.out)

    def test_controller_or_seal_tamper_refused(self):
        self.prepare()
        for relative in (".controller/manifest.json", ".controller/stage1.json"):
            path = self.out / relative
            original = path.read_bytes()
            data = json.loads(original)
            if "payload" in data:
                data["payload"]["sources"] = []
            else:
                data["issues"] = []
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                review.verify(self.out)
            path.write_bytes(original)

    def test_duplicate_json_keys_are_rejected(self):
        self.spec_path.write_text('{"issues": [], "issues": []}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
