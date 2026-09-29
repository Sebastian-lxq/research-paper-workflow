"""Small contract mutations against the actual installed structural validator.

Set RESEARCH_CONTRACT_VALIDATOR to test another trusted installation. No installed
skill or scientific evidence is edited. The suite skips if no validator exists.
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_release_handoff.py"
SPEC = importlib.util.spec_from_file_location("release_handoff_bridge", SCRIPT)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


def fixture():
    certificates = {
        "proof": ["proof_truth", "proof_scope_coverage"],
        "middle": ["manuscript_wording_eligibility"],
        "sentence": ["manuscript_wording_eligibility"],
        "diagnostic": ["simulation_inference_eligibility"],
    }
    dependencies = {
        "proof": [],
        "middle": ["proof"],
        "sentence": ["middle"],
        "diagnostic": [],
    }
    return {
        "schema_version": "research-release-contract.v1",
        "objects": [
            {
                "object_id": cid,
                "object_type": "synthetic",
                "version": "v1",
                "content_hash": "synthetic",
                "scope_hash": "synthetic",
            }
            for cid in certificates
        ],
        "claims": [
            {
                "claim_id": cid,
                "object_id": cid,
                "required": cid == "sentence",
                "dependencies": dependencies[cid],
                "applicable_certificates": certs,
                "state": {cert: "PASS" for cert in certs},
            }
            for cid, certs in certificates.items()
        ],
        "root_errors": [],
        "coverage_blockers": [],
        "artifacts": [
            {"artifact_id": "draft", "claim_ids": ["sentence"], "freshness": "current"}
        ],
        "release_vector": {
            "schema_GO": True,
            "source_GO": False,
            "proof_GO": True,
            "implementation_GO": False,
            "simulation_GO": False,
            "writing_GO": True,
            "artifact_GO": True,
            "scientific_GO": True,
            "submission_GO": True,
        },
    }


def sidecar():
    return {
        "schema_version": BRIDGE.EDGE_VERSION,
        "edges": [
            {
                "consumer_claim_id": "sentence",
                "dependency_claim_id": "middle",
                "consumer_certificate": "manuscript_wording_eligibility",
                "dependency_certificates": ["manuscript_wording_eligibility"],
                "required": True,
            },
            {
                "consumer_claim_id": "middle",
                "dependency_claim_id": "proof",
                "consumer_certificate": "manuscript_wording_eligibility",
                "dependency_certificates": ["proof_truth"],
                "required": True,
            },
        ],
    }


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator_path = Path(
            os.environ.get(
                "RESEARCH_CONTRACT_VALIDATOR",
                Path.home()
                / ".codex"
                / "skills"
                / "write-econometrics-paper-v3"
                / "scripts"
                / "validate_research_contract.py",
            )
        )
        if not cls.validator_path.is_file():
            raise unittest.SkipTest(
                "Set RESEARCH_CONTRACT_VALIDATOR to a trusted structural validator"
            )
        cls.validator = staticmethod(BRIDGE.load_validator(cls.validator_path))

    def check(self, data=None, edges=None):
        return BRIDGE.check_contract(
            fixture() if data is None else data, self.validator, edges
        )

    def test_clean_includes_transitive_required_ancestors(self):
        result = self.check()
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(
            result["scientific_eligibility"]["required_claim_closure"],
            ["middle", "proof", "sentence"],
        )
        self.assertIsNone(result["component_eligibility"]["simulation_GO"])
        self.assertTrue(result["release_permitted_from_record"])

    def test_partial_fail_and_contradicted_propagate_without_changing_truth(self):
        for state in ("PARTIAL", "FAIL", "CONTRADICTED"):
            with self.subTest(state=state):
                data = fixture()
                data["claims"][0]["state"]["proof_truth"] = state
                result = self.check(data)
                self.assertTrue(result["upstream_validation"]["valid"])
                self.assertTrue(result["structural_validity"]["valid"])
                self.assertEqual(result["exit_code"], 1)
                self.assertFalse(result["release_permitted_from_record"])
                self.assertEqual(
                    result["scientific_eligibility"]["not_evaluable"],
                    ["middle", "sentence"],
                )
                certs = {
                    (r["claim_id"], r["certificate"]): r
                    for r in result["scientific_eligibility"]["certificates"]
                }
                self.assertEqual(
                    certs[("proof", "proof_truth")]["effective_state"], state
                )
                self.assertEqual(
                    certs[("sentence", "manuscript_wording_eligibility")][
                        "recorded_state"
                    ],
                    "PASS",
                )

    def test_root_and_blocker_propagation_with_exact_scope(self):
        for collection, id_key in (
            ("root_errors", "error_id"),
            ("coverage_blockers", "blocker_id"),
        ):
            data = fixture()
            data[collection] = [
                {
                    id_key: "failure",
                    "claim_id": "proof",
                    "owner": "proof",
                    "certificate": "proof_truth",
                }
            ]
            result = self.check(data)
            self.assertEqual(result["exit_code"], 1)
            self.assertEqual(
                result["scientific_eligibility"]["not_evaluable"],
                ["middle", "proof", "sentence"],
            )

    def test_cycle_is_structural_failure(self):
        data = fixture()
        data["claims"][0]["dependencies"] = ["sentence"]
        self.assertEqual(self.check(data)["exit_code"], 2)

    def test_unrelated_optional_diagnostic_is_not_required(self):
        data = fixture()
        data["claims"][3]["state"]["simulation_inference_eligibility"] = "PARTIAL"
        data["coverage_blockers"] = [
            {"blocker_id": "optional", "claim_id": "diagnostic"}
        ]
        data["artifacts"].append(
            {
                "artifact_id": "optional-stale",
                "claim_ids": ["diagnostic"],
                "freshness": "stale",
            }
        )
        result = self.check(data)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stale_required_artifacts"], [])
        self.assertIsNone(result["component_eligibility"]["simulation_GO"])

    def test_typed_consumption_ignores_unused_source_certificate(self):
        data = fixture()
        data["claims"][0]["state"]["proof_scope_coverage"] = "PARTIAL"
        data["coverage_blockers"] = [
            {
                "blocker_id": "unused-scope",
                "claim_id": "proof",
                "certificate": "proof_scope_coverage",
            }
        ]
        self.assertEqual(self.check(data)["exit_code"], 1)
        result = self.check(data, sidecar())
        self.assertEqual(result["exit_code"], 0)
        selected = [
            (r["claim_id"], r["certificate"])
            for r in result["scientific_eligibility"]["certificates"]
        ]
        self.assertNotIn(("proof", "proof_scope_coverage"), selected)

    def test_unscoped_blocker_remains_conservative_under_typed_edges(self):
        data = fixture()
        data["coverage_blockers"] = [
            {"blocker_id": "unknown-scope", "claim_id": "proof"}
        ]
        self.assertEqual(self.check(data, sidecar())["exit_code"], 1)

    def test_explicit_optional_edge_does_not_consume_proof(self):
        data = fixture()
        data["claims"][0]["state"]["proof_truth"] = "FAIL"
        edges = sidecar()
        edges["edges"][1]["required"] = False
        result = self.check(data, edges)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(
            result["scientific_eligibility"]["required_claim_closure"],
            ["middle", "sentence"],
        )

    def test_typed_edges_reject_omissions_unknown_links_and_bad_certificates(self):
        variants = []
        missing = sidecar()
        missing["edges"].pop()
        variants.append(missing)
        unknown = sidecar()
        unknown["edges"][0]["dependency_claim_id"] = "diagnostic"
        variants.append(unknown)
        bad_cert = sidecar()
        bad_cert["edges"][1]["dependency_certificates"] = [
            "simulation_inference_eligibility"
        ]
        variants.append(bad_cert)
        for edges in variants:
            self.assertEqual(self.check(edges=edges)["exit_code"], 2)

    def test_lying_component_vector_is_rejected(self):
        data = fixture()
        data["release_vector"]["proof_GO"] = False
        result = self.check(data)
        self.assertTrue(result["scientific_eligibility"]["eligible"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn(
            "scientific_GO requires applicable proof_GO",
            result["release_vector_consistency"]["errors"],
        )

    def test_missing_state_is_structural_but_missing_support_is_scientific(self):
        data = fixture()
        del data["claims"][0]["state"]["proof_truth"]
        self.assertEqual(self.check(data)["exit_code"], 2)
        data = fixture()
        data["claims"][0]["applicable_certificates"] = []
        data["claims"][0]["state"] = {}
        result = self.check(data)
        self.assertTrue(result["structural_validity"]["valid"])
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(
            any(
                r["kind"] == "missing_evidence"
                for r in result["scientific_eligibility"]["blocking_reasons"]
            )
        )

    def test_no_required_claims_cannot_vacuously_release(self):
        data = fixture()
        for claim in data["claims"]:
            claim["required"] = False
        self.assertEqual(self.check(data)["exit_code"], 1)

    def test_stale_ancestor_artifact_is_detected(self):
        data = fixture()
        data["artifacts"].append(
            {"artifact_id": "proof-pdf", "claim_ids": ["proof"], "freshness": "stale"}
        )
        result = self.check(data)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["stale_required_artifacts"], ["proof-pdf"])

    def test_stale_artifact_does_not_reopen_verified_scientific_support(self):
        data = fixture()
        data["artifacts"][0]["freshness"] = "stale"
        data["release_vector"]["artifact_GO"] = False
        data["release_vector"]["submission_GO"] = False
        result = self.check(data)
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(result["scientific_eligibility"]["eligible"])
        self.assertTrue(result["release_vector_consistency"]["valid"])

    def test_missing_submission_artifact_cannot_be_self_certified(self):
        data = fixture()
        data["artifacts"] = []
        result = self.check(data)
        self.assertTrue(result["scientific_eligibility"]["eligible"])
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["release_permitted_from_record"])
        data["release_vector"]["submission_GO"] = False
        self.assertEqual(self.check(data)["exit_code"], 0)

    def test_composite_roots_are_unique_and_match_the_single_union(self):
        first = fixture()
        first["root_errors"] = [
            {"error_id": "owned-root", "claim_id": "proof", "owner": "proof"}
        ]
        second = fixture()
        second["coverage_blockers"] = [
            {"blocker_id": "missing-receipt", "claim_id": "middle"}
        ]
        combined = copy.deepcopy(first)
        combined["coverage_blockers"] = second["coverage_blockers"]

        def ids(result):
            return {
                r["reason_id"]
                for r in result["scientific_eligibility"]["blocking_reasons"]
            }

        self.assertEqual(len(ids(self.check(first))), 1)
        self.assertEqual(
            ids(self.check(combined)), ids(self.check(first)) | ids(self.check(second))
        )

    def test_withheld_submission_is_not_approval(self):
        data = fixture()
        data["release_vector"]["submission_GO"] = False
        result = self.check(data)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["release_permitted_from_record"])

    def test_malformed_vector_cannot_be_normalized_into_validity(self):
        data = fixture()
        data["release_vector"]["proof_GO"] = "false"
        self.assertEqual(self.check(data)["exit_code"], 2)

    def test_input_is_not_mutated_and_order_is_deterministic(self):
        data = fixture()
        data["claims"][0]["state"]["proof_truth"] = "PARTIAL"
        before = copy.deepcopy(data)
        first = self.check(data)
        self.assertEqual(data, before)
        data["claims"].reverse()
        self.assertEqual(first, self.check(data))

    def test_cli_reports_json_and_exit_status(self):
        with tempfile.TemporaryDirectory() as temp:
            contract = Path(temp) / "contract.json"
            # A temporary test fixture is the only file this test writes.
            contract.write_text(json.dumps(fixture()), encoding="utf-8")
            args = [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(contract),
                "--validator",
                str(self.validator_path),
            ]
            clean = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(json.loads(clean.stdout)["exit_code"], 0)
            edges = Path(temp) / "edges.json"
            edges.write_text("null", encoding="utf-8")
            invalid_edges = subprocess.run(
                args + ["--edges", str(edges)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(invalid_edges.returncode, 2)
            contract.write_text("{", encoding="utf-8")
            invalid = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertEqual(invalid.returncode, 2)
            self.assertFalse(json.loads(invalid.stdout)["structural_validity"]["valid"])


if __name__ == "__main__":
    unittest.main()
