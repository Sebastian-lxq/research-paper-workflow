import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "proof_lineage.py"
SPEC = importlib.util.spec_from_file_location("proof_lineage", SCRIPT)
PROOF_LINEAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROOF_LINEAGE)


class ProofLineageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="proof-lineage-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name, content in {
            "theory/statement.md": "Theorem T under assumptions A.\n",
            "theory/assumptions.md": "Assumptions A1--A3.\n",
            "theory/obligations.json": '{"PO-1": "closed"}\n',
            "theory/proof.md": "Proof of theorem T.\n",
            "theory/review.json": '{"verdict": "pass", "findings": []}\n',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.manifest = self.fixture()

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def binding(self, role, name):
        return {
            "role": role,
            "path": name,
            "sha256": self.sha(name),
            "locator": {"kind": "file"},
        }

    def fixture(self):
        return {
            "schema": PROOF_LINEAGE.MANIFEST_SCHEMA,
            "lineage_id": "example-theorem-lineage",
            "producer": {"name": "prove-econometrics-theory-v2", "version": "2"},
            "specialist_release": {
                "status": "pass",
                "scope": "Frozen theorem T only.",
                "permitted_wording": "Theorem T is verified only under assumptions A1--A3.",
            },
            "roots": ["claim:T:v1"],
            "objects": [
                {"id": "claim:T:v1", "kind": "claim", "version": "1", "status": "verified", "required": True, "actor": None, "bindings": [self.binding("statement", "theory/statement.md")]},
                {"id": "assumptions:T:v1", "kind": "assumption-set", "version": "1", "status": "verified", "required": True, "actor": None, "bindings": [self.binding("assumptions", "theory/assumptions.md")]},
                {"id": "obligation:T:PO-1", "kind": "obligation", "version": "1", "status": "verified", "required": True, "actor": None, "bindings": [self.binding("ledger", "theory/obligations.json")]},
                {"id": "proof:T:v1", "kind": "proof", "version": "1", "status": "verified", "required": True, "actor": None, "bindings": [self.binding("proof", "theory/proof.md")]},
                {"id": "review:T:v1", "kind": "review", "version": "1", "status": "verified", "required": True, "actor": "fresh-context-reviewer-1", "bindings": [self.binding("review", "theory/review.json")]},
            ],
            "edges": [
                {"from": "claim:T:v1", "to": "assumptions:T:v1", "relation": "uses-assumptions"},
                {"from": "claim:T:v1", "to": "obligation:T:PO-1", "relation": "depends-on"},
                {"from": "obligation:T:PO-1", "to": "proof:T:v1", "relation": "discharged-by"},
                {"from": "claim:T:v1", "to": "review:T:v1", "relation": "reviewed-by"},
            ],
        }

    def test_complete_lineage_is_consumable_without_certifying_math(self):
        result = PROOF_LINEAGE.validate(self.root, self.manifest)
        self.assertTrue(result["workflow_consumable"])
        self.assertFalse(result["mathematical_correctness_established"])
        self.assertFalse(result["reviewer_independence_established"])
        self.assertTrue(result["distinct_reviewer_identity_recorded"])
        self.assertIn("assumptions A1--A3", result["permitted_wording"])

    def test_changed_binding_blocks_but_does_not_invalidate_schema(self):
        (self.root / "theory" / "proof.md").write_text("Changed proof.\n", encoding="utf-8")
        result = PROOF_LINEAGE.validate(self.root, self.manifest)
        self.assertTrue(result["valid"])
        self.assertFalse(result["workflow_consumable"])
        self.assertEqual(result["binding_summary"]["noncurrent"], 1)

    def test_open_load_bearing_obligation_blocks_consumption(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["objects"][2]["status"] = "open"
        result = PROOF_LINEAGE.validate(self.root, manifest)
        self.assertFalse(result["workflow_consumable"])
        self.assertIn("obligation:T:PO-1", result["unresolved_ids"])

    def test_root_requires_assumptions_obligation_and_review_interfaces(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["edges"] = [edge for edge in manifest["edges"] if edge["relation"] != "reviewed-by"]
        result = PROOF_LINEAGE.validate(self.root, manifest)
        self.assertFalse(result["workflow_consumable"])
        self.assertTrue(any("no review record" in blocker for blocker in result["blockers"]))

    def test_unknown_endpoint_and_dependency_cycle_are_invalid(self):
        unknown = copy.deepcopy(self.manifest)
        unknown["edges"][0]["to"] = "missing"
        with self.assertRaises(PROOF_LINEAGE.ProofLineageError):
            PROOF_LINEAGE.validate(self.root, unknown)
        cyclic = copy.deepcopy(self.manifest)
        cyclic["edges"].append({"from": "obligation:T:PO-1", "to": "claim:T:v1", "relation": "depends-on"})
        with self.assertRaises(PROOF_LINEAGE.ProofLineageError):
            PROOF_LINEAGE.validate(self.root, cyclic)

    def test_typed_edge_contract_rejects_review_as_an_assumption_set(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["edges"][0]["to"] = "review:T:v1"
        with self.assertRaises(PROOF_LINEAGE.ProofLineageError):
            PROOF_LINEAGE.validate(self.root, manifest)

    def test_cli_separates_ready_blocked_and_invalid(self):
        record = self.root / "theory" / "lineage.json"
        record.write_text(json.dumps(self.manifest), encoding="utf-8")
        command = [sys.executable, "-B", str(SCRIPT), "--project", str(self.root), "--record", "theory/lineage.json"]
        ready = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        blocked = copy.deepcopy(self.manifest)
        blocked["specialist_release"]["status"] = "partial"
        record.write_text(json.dumps(blocked), encoding="utf-8")
        pending = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(pending.returncode, 1, pending.stdout + pending.stderr)
        record.write_text("{}", encoding="utf-8")
        invalid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()
