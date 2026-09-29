"""Actual-byte mutations with an unchanged, structurally valid release contract."""

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

import test_release_handoff as legacy

BRIDGE, SCRIPT = legacy.BRIDGE, legacy.SCRIPT
fixture, sidecar = legacy.fixture, legacy.sidecar


CONTENT = runpy.run_path(str(SCRIPT.with_name("content_bindings.py")))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ContentBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        legacy.HandoffTests.setUpClass()
        cls.validator = staticmethod(legacy.HandoffTests.validator)
        cls.validator_path = legacy.HandoffTests.validator_path

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture()
        # A second required branch shares the proof source file, but no support
        # claim/dependency with the first branch. This detects over-invalidation.
        self.data["claims"][3]["required"] = True
        self.data["release_vector"]["simulation_GO"] = True
        self.data["artifacts"].extend([
            {"artifact_id": "table", "claim_ids": ["proof"], "freshness": "current"},
            {"artifact_id": "diagnostic-output", "claim_ids": ["diagnostic"], "freshness": "current"},
        ])
        self.source = "preamble\r\n<proof>\r\n证明 α\r\n</proof>\n<diagnostic>\nindependent\n</diagnostic>\n"
        (self.root / "shared.tex").write_bytes(self.source.encode("utf-8"))
        self.bindings = {"schema_version": CONTENT["BINDING_VERSION"], "bindings": []}
        for record in self.data["objects"]:
            cid = record["object_id"]
            if cid in {"proof", "diagnostic"}:
                locator = {"kind": "markers", "start": f"<{cid}>", "end": f"</{cid}>"}
                raw = self.source.split(locator["start"])[1].split(locator["end"])[0].encode("utf-8")
                self.bind(record, "object", "shared.tex", raw, locator)
            else:
                self.whole(record, "object", f"{cid}.md", f"{cid} text\n".encode())
        for record in self.data["artifacts"]:
            self.whole(record, "artifact", f'{record["artifact_id"]}.txt', b"measured value 0.1\n")

    def bind(self, record, kind, path, raw, locator):
        self.bindings["bindings"].append({
            f"{kind}_id": record[f"{kind}_id"],
            "record_sha256": CONTENT["record_sha256"](record),
            "path": path, "sha256": digest(raw), "locator": locator,
        })

    def whole(self, record, kind, path, raw):
        (self.root / path).write_bytes(raw)
        self.bind(record, kind, path, raw, {"kind": "file"})

    def check(self, edges=None):
        return BRIDGE.check_contract(
            self.data, self.validator, edges,
            bindings=self.bindings, project_root=self.root,
        )

    def targets(self, result):
        return {(item["target_kind"], item["target_id"]): item
                for item in result["content_verification"]["targets"]}

    def certificates(self, result):
        return {(item["claim_id"], item["certificate"]): item
                for item in result["scientific_eligibility"]["certificates"]}

    def artifact_states(self, result):
        return {item["artifact_id"]: item["effective_freshness"]
                for item in result["artifact_assessment"]}

    def test_unchanged_bytes_and_records_are_explicitly_limited(self):
        before_data, before_bindings = copy.deepcopy(self.data), copy.deepcopy(self.bindings)
        before_files = {path.name: path.read_bytes() for path in self.root.iterdir()}
        result = self.check()
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["content_verification"]["mode"], "bound-content-check")
        self.assertEqual(
            result["content_verification"]["schema_version"],
            CONTENT["REPORT_SCHEMA"],
        )
        self.assertNotEqual(CONTENT["REPORT_SCHEMA"], CONTENT["BINDING_SCHEMA"])
        self.assertTrue(result["content_verification"]["coverage"]["registered_required_contents_unchanged"])
        self.assertTrue(all(item["status"] == "unchanged" for item in self.targets(result).values()))
        self.assertIn("scientific correctness", result["content_verification"]["scope"])
        self.assertEqual(self.data, before_data)
        self.assertEqual(self.bindings, before_bindings)
        self.assertEqual(before_files, {path.name: path.read_bytes() for path in self.root.iterdir()})

    def test_fragment_change_propagates_to_consumers_and_outputs_only(self):
        (self.root / "shared.tex").write_bytes(self.source.replace("证明 α", "证明 β").encode("utf-8"))
        result = self.check(sidecar())
        self.assertEqual(result["exit_code"], 1)
        targets, certs = self.targets(result), self.certificates(result)
        self.assertEqual(targets[("object", "proof")]["status"], "changed")
        self.assertEqual(targets[("object", "diagnostic")]["status"], "unchanged")
        for cid, cert in (("proof", "proof_truth"), ("middle", "manuscript_wording_eligibility"), ("sentence", "manuscript_wording_eligibility")):
            self.assertEqual(certs[(cid, cert)]["recorded_state"], "PASS")
            self.assertEqual(certs[(cid, cert)]["effective_state"], "NOT_EVALUABLE")
        self.assertEqual(certs[("diagnostic", "simulation_inference_eligibility")]["effective_state"], "PASS")
        self.assertEqual(self.artifact_states(result), {"draft": "needs_review", "table": "needs_review", "diagnostic-output": "current"})

    def test_outside_fragment_edit_preserves_both_fragment_bindings(self):
        (self.root / "shared.tex").write_bytes(self.source.replace("preamble", "edited outside both fragments").encode("utf-8"))
        self.assertEqual(self.check()["exit_code"], 0)

    def test_whole_artifact_change_reopens_its_support_claim_and_consumers(self):
        (self.root / "table.txt").write_bytes(b"measured value 0.9\n")
        result = self.check()
        certs = self.certificates(result)
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(self.targets(result)[("artifact", "table")]["status"], "changed")
        self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["middle", "proof", "sentence"])
        self.assertEqual(certs[("diagnostic", "simulation_inference_eligibility")]["effective_state"], "PASS")
        self.assertEqual(result["affected_required_artifacts"], ["draft", "table"])

    def test_whole_object_change_cannot_reuse_recorded_pass(self):
        (self.root / "middle.md").write_bytes(b"changed wording\n")
        result = self.check()
        self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["middle", "sentence"])
        self.assertEqual(self.artifact_states(result)["table"], "current")

    def test_missing_file_is_not_unchanged_or_unbound(self):
        (self.root / "table.txt").unlink()
        result = self.check()
        self.assertEqual(self.targets(result)[("artifact", "table")]["status"], "missing")
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["scientific_eligibility"]["evaluable"])

    def test_fragment_missing_duplicate_reversed_overlapping_and_non_utf8(self):
        variants = [
            self.source.replace("<proof>", "<renamed>"),
            self.source + "<proof>",
            self.source + "</proof>",
            "</proof>text<proof>" + self.source.split("</proof>")[1],
        ]
        for text in variants:
            with self.subTest(text=text):
                (self.root / "shared.tex").write_bytes(text.encode("utf-8"))
                result = self.check()
                self.assertEqual(self.targets(result)[("object", "proof")]["status"], "locator_unresolved")
                self.assertEqual(result["exit_code"], 1)
        (self.root / "shared.tex").write_bytes(b"\xff<proof>x</proof>")
        self.assertEqual(self.targets(self.check())[("object", "proof")]["status"], "locator_unresolved")
        binding = self.bindings["bindings"][0]
        binding["locator"] = {"kind": "markers", "start": "aaa", "end": "end"}
        (self.root / "shared.tex").write_bytes(b"aaaaend")
        self.assertEqual(self.targets(self.check())[("object", "proof")]["status"], "locator_unresolved")

    def test_required_object_or_artifact_omission_is_unknown_and_blocks(self):
        original = copy.deepcopy(self.bindings["bindings"])
        for kind, identifier in (("object", "proof"), ("artifact", "table")):
            with self.subTest(kind=kind):
                self.bindings["bindings"] = [item for item in original if item.get(f"{kind}_id") != identifier]
                result = self.check()
                coverage = result["content_verification"]["coverage"]
                self.assertEqual(result["exit_code"], 1)
                self.assertEqual(self.targets(result)[(kind, identifier)]["status"], "unbound")
                self.assertEqual(coverage["required_unbound_targets"], [{"target_kind": kind, "target_id": identifier}])
                self.assertFalse(coverage["registered_required_contents_unchanged"])

    def test_empty_sidecar_cannot_claim_all_required_contents_checked(self):
        self.bindings["bindings"] = []
        result = self.check()
        self.assertEqual(result["exit_code"], 1)
        coverage = result["content_verification"]["coverage"]
        self.assertEqual(coverage["bound_required_target_count"], 0)
        self.assertFalse(coverage["registered_required_contents_unchanged"])

    def test_optional_unbound_or_changed_branch_does_not_block_required_closure(self):
        self.data["claims"][3]["required"] = False
        for status in ("unbound", "changed"):
            with self.subTest(status=status):
                original = copy.deepcopy(self.bindings)
                if status == "unbound":
                    self.bindings["bindings"] = [item for item in self.bindings["bindings"] if item.get("object_id") != "diagnostic" and item.get("artifact_id") != "diagnostic-output"]
                else:
                    (self.root / "shared.tex").write_bytes(self.source.replace("independent", "changed optional").encode("utf-8"))
                result = self.check()
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(self.targets(result)[("object", "diagnostic")]["status"], status)
                self.assertEqual(self.artifact_states(result)["draft"], "current")
                self.bindings = original

    def test_record_identity_captures_version_content_and_scope_separately(self):
        for key in ("version", "content_hash", "scope_hash", "object_type"):
            with self.subTest(key=key):
                original = self.data["objects"][0][key]
                self.data["objects"][0][key] = original + "-changed"
                result = self.check()
                target = self.targets(result)[("object", "proof")]
                self.assertEqual(target["status"], "changed")
                self.assertFalse(target["record_matches"])
                self.assertEqual(target["actual_sha256"], target["expected_sha256"])
                self.assertEqual(result["exit_code"], 1)
                self.data["objects"][0][key] = original

    def test_artifact_record_fingerprint_detects_support_registration_change(self):
        self.data["artifacts"][1]["claim_ids"].append("diagnostic")
        result = self.check()
        target = self.targets(result)[("artifact", "table")]
        self.assertEqual(target["status"], "changed")
        self.assertFalse(target["record_matches"])
        self.assertEqual(result["exit_code"], 1)

    def test_support_removal_or_transfer_without_snapshot_cannot_turn_green(self):
        self.data["claims"][3]["required"] = False
        for support in ([], ["diagnostic"]):
            with self.subTest(support=support):
                self.data["artifacts"][1]["claim_ids"] = support
                result = self.check()
                target = self.targets(result)[("artifact", "table")]
                self.assertEqual(result["exit_code"], 1)
                self.assertTrue(target["required"])
                self.assertTrue(target["support_ownership_unknown"])
                self.assertIsNone(target["baseline_claim_ids"])
                self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["middle", "proof", "sentence"])
                self.assertEqual(result["content_verification"]["coverage"]["unknown_support_targets"], [{"target_kind": "artifact", "target_id": "table"}])
                self.assertFalse(result["content_verification"]["coverage"]["registered_required_contents_unchanged"])
                self.assertIn("table", result["affected_required_artifacts"])

    def test_snapshot_support_removal_blocks_original_branch_only(self):
        table = self.data["artifacts"][1]
        binding = next(item for item in self.bindings["bindings"] if item.get("artifact_id") == "table")
        binding["record_snapshot"] = copy.deepcopy(table)
        table["claim_ids"] = []
        result = self.check()
        target = self.targets(result)[("artifact", "table")]
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(target["support_ownership_unknown"])
        self.assertEqual(target["current_claim_ids"], [])
        self.assertEqual(target["baseline_claim_ids"], ["proof"])
        self.assertEqual(target["claim_ids"], ["proof"])
        self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["middle", "proof", "sentence"])
        self.assertEqual(self.artifact_states(result)["diagnostic-output"], "current")
        self.assertEqual(self.certificates(result)[("diagnostic", "simulation_inference_eligibility")]["effective_state"], "PASS")

    def test_snapshot_support_transfer_invalidates_union_of_old_and_current_support(self):
        table = self.data["artifacts"][1]
        binding = next(item for item in self.bindings["bindings"] if item.get("artifact_id") == "table")
        binding["record_snapshot"] = copy.deepcopy(table)
        table["claim_ids"] = ["diagnostic"]
        result = self.check()
        target = self.targets(result)[("artifact", "table")]
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(target["support_ownership_unknown"])
        self.assertEqual(target["claim_ids"], ["diagnostic", "proof"])
        self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["diagnostic", "middle", "proof", "sentence"])

    def test_snapshot_known_optional_support_change_does_not_block_required_branch(self):
        self.data["claims"][3]["required"] = False
        optional = self.data["artifacts"][2]
        binding = next(item for item in self.bindings["bindings"] if item.get("artifact_id") == "diagnostic-output")
        binding["record_snapshot"] = copy.deepcopy(optional)
        optional["claim_ids"] = []
        result = self.check()
        target = self.targets(result)[("artifact", "diagnostic-output")]
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(target["status"], "changed")
        self.assertFalse(target["required"])
        self.assertFalse(target["support_ownership_unknown"])
        self.assertEqual(self.artifact_states(result)["draft"], "current")

    def test_missing_historical_claim_is_explicit_unknown_not_a_new_graph_node(self):
        table = self.data["artifacts"][1]
        binding = next(item for item in self.bindings["bindings"] if item.get("artifact_id") == "table")
        binding["record_snapshot"] = copy.deepcopy(table)
        table["claim_ids"] = []
        self.data["claims"] = [claim for claim in self.data["claims"] if claim["claim_id"] != "proof"]
        self.data["claims"][0]["dependencies"] = []
        result = self.check()
        target = self.targets(result)[("artifact", "table")]
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(target["support_ownership_unknown"])
        self.assertEqual(target["unresolved_claim_ids"], ["proof"])
        self.assertNotIn("proof", target["blocking_claim_ids"])
        self.assertEqual(result["scientific_eligibility"]["not_evaluable"], ["diagnostic", "middle", "sentence"])

    def test_invalid_snapshot_digest_id_or_structure_is_rejected(self):
        binding = next(item for item in self.bindings["bindings"] if item.get("artifact_id") == "table")
        baseline = copy.deepcopy(self.data["artifacts"][1])
        snapshots = [None, {**baseline, "artifact_id": "different"},
                     {**baseline, "claim_ids": ["diagnostic"]},
                     {**baseline, "claim_ids": "proof"},
                     {"artifact_id": "table", "claim_ids": ["proof"]}]
        for snapshot in snapshots:
            with self.subTest(snapshot=snapshot):
                binding["record_snapshot"] = snapshot
                self.assertEqual(self.check()["exit_code"], 2)

    def test_matching_record_with_or_without_snapshot_retains_compatibility(self):
        old_result = self.check()
        for binding in self.bindings["bindings"]:
            if "artifact_id" in binding:
                binding["record_snapshot"] = copy.deepcopy(next(
                    record for record in self.data["artifacts"]
                    if record["artifact_id"] == binding["artifact_id"]
                ))
        new_result = self.check()
        self.assertEqual(old_result, new_result)
        self.assertEqual(new_result["exit_code"], 0)

    def test_path_traversal_absolute_and_outside_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            outside_file = Path(outside) / "secret.txt"
            outside_file.write_bytes(b"not project evidence")
            (self.root / "escape").symlink_to(outside, target_is_directory=True)
            (self.root / "escape-file").symlink_to(outside_file)
            for path in ("../secret.txt", str(outside_file), "escape/secret.txt", "escape-file", "./shared.tex", "dir/../shared.tex", "dir\\file"):
                with self.subTest(path=path):
                    self.bindings["bindings"][0]["path"] = path
                    result = self.check()
                    self.assertEqual(result["exit_code"], 2)
                    self.assertFalse(result["structural_validity"]["valid"])

    def test_inside_symlink_is_allowed_without_changing_fragment_rules(self):
        (self.root / "inside").symlink_to(self.root / "shared.tex")
        self.bindings["bindings"][0]["path"] = "inside"
        self.assertEqual(self.check()["exit_code"], 0)

    def test_non_regular_file_never_blocks_waiting_for_fifo_content(self):
        (self.root / "directory").mkdir()
        os.mkfifo(self.root / "fifo")
        for path in ("directory", "fifo"):
            with self.subTest(path=path):
                self.bindings["bindings"][0]["path"] = path
                result = self.check()
                target = self.targets(result)[("object", "proof")]
                self.assertEqual(target["status"], "locator_unresolved")
                self.assertEqual(target["detail"], "bound path is not a regular file")

    def test_noncanonical_record_value_returns_structural_report_from_api(self):
        self.data["objects"][0]["extra"] = float("nan")
        result = self.check()
        self.assertEqual(result["exit_code"], 2)
        self.assertFalse(result["structural_validity"]["valid"])
        self.assertTrue(any("bindings/input failure" in error for error in result["structural_validity"]["errors"]))

    def test_binding_cannot_invent_targets_dependencies_or_certificates(self):
        original = copy.deepcopy(self.bindings)
        mutations = [
            lambda b: b["bindings"][0].update(object_id="invented"),
            lambda b: b["bindings"][0].update(dependencies=["sentence"]),
            lambda b: b["bindings"][0].update(certificate="proof_truth"),
            lambda b: b["bindings"].append(copy.deepcopy(b["bindings"][0])),
            lambda b: b["bindings"][0].update(sha256="not-sha256"),
            lambda b: b["bindings"][0].update(locator={"kind": "label", "label": "theorem-1"}),
            lambda b: b["bindings"][0].update(artifact_id="table"),
        ]
        for mutate in mutations:
            self.bindings = copy.deepcopy(original)
            mutate(self.bindings)
            self.assertEqual(self.check()["exit_code"], 2)

    def test_legacy_call_remains_record_only_despite_actual_change(self):
        (self.root / "table.txt").write_bytes(b"modified")
        legacy = BRIDGE.check_contract(self.data, self.validator)
        current = self.check()
        self.assertEqual(legacy["exit_code"], 0)
        self.assertEqual(legacy["content_verification"]["mode"], "record-only")
        self.assertIsNone(legacy["content_verification"]["coverage"])
        self.assertEqual(current["exit_code"], 1)

    def test_byte_equality_never_cures_a_failed_scientific_certificate(self):
        self.data["claims"][0]["state"]["proof_truth"] = "FAIL"
        result = self.check()
        self.assertTrue(result["content_verification"]["coverage"]["registered_required_contents_unchanged"])
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(self.certificates(result)[("proof", "proof_truth")]["effective_state"], "FAIL")

    def test_record_hash_is_canonical_json_not_the_contract_semantic_hash(self):
        record = self.data["objects"][0]
        expected = digest(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        self.assertEqual(CONTENT["record_sha256"](record), expected)
        self.assertEqual(CONTENT["record_sha256"](dict(reversed(list(record.items())))), expected)
        self.assertNotEqual(self.bindings["bindings"][0]["sha256"], record["content_hash"])

    def test_cli_pairs_arguments_rejects_null_and_returns_same_content_result(self):
        contract, bindings_path = self.root / "contract.json", self.root / "bindings.json"
        contract.write_text(json.dumps(self.data), encoding="utf-8")
        bindings_path.write_text(json.dumps(self.bindings), encoding="utf-8")
        args = [sys.executable, "-B", str(SCRIPT), str(contract), "--validator", str(self.validator_path)]
        for extra in (["--bindings", str(bindings_path)], ["--project-root", str(self.root)]):
            result = subprocess.run(args + extra, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
        full = args + ["--bindings", str(bindings_path), "--project-root", str(self.root)]
        result = subprocess.run(full, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["content_verification"], self.check()["content_verification"])
        (self.root / "table.txt").write_bytes(b"changed")
        result = subprocess.run(full, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        bindings_path.write_text("null", encoding="utf-8")
        result = subprocess.run(full, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
