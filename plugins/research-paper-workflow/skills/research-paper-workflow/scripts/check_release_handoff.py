#!/usr/bin/env python3
"""Check recorded research-release eligibility across actual dependencies.

Usage: python3 check_release_handoff.py CONTRACT --validator VALIDATOR [--edges EDGES]
       [--bindings BINDINGS --project-root ROOT]

VALIDATOR is an explicitly trusted local Python file exposing validate(data).
The existing validator checks structure. This bridge additionally evaluates the
transitive certificate dependencies and the declared release vector. Optional
content bindings check registered files/fragments without changing the contract.
It does not verify proof truth, semantic mappings, or human approval. Without
bindings the check retains its previous record-only meaning.

The optional sidecar format is research-handoff-edges.v1:
{"schema_version": "research-handoff-edges.v1", "edges": [{
  "consumer_claim_id": "sentence", "dependency_claim_id": "theorem",
  "consumer_certificate": "manuscript_wording_eligibility",
  "dependency_certificates": ["proof_truth", "proof_scope_coverage"],
  "required": true
}]}
Every existing claim-dependency pair must be mapped when a sidecar is supplied;
multiple mappings may consume different certificates. A mapping cannot invent
an edge absent from the original contract. required=false explicitly marks an
optional edge. Without a sidecar, each legacy dependency conservatively consumes
all applicable upstream certificates for every applicable consumer certificate.
No dependency is inferred from similar names, owners, or scientific subject.

An optional `certificate` field on a root error or coverage blocker narrows its
scope. Without that field, it applies to every certificate of its claim. Artifact
claim_ids are claim-level support bindings and must contain only actual support.

Exit codes: 0 = structure valid, required recorded support eligible, vector
consistent; 1 = structure valid but required support incomplete/ineligible,
required artifact stale, or release vector inconsistent; 2 = invalid structure,
sidecar, input, or validator failure. A zero exit is not submission approval;
inspect declared_release_vector and release_permitted_from_record separately.
"""

from __future__ import annotations

import argparse
import copy
import json
import runpy
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable


REPORT_VERSION = "research-handoff-check.v1"
EDGE_VERSION = "research-handoff-edges.v1"
MISSING_CERTIFICATE = "__missing_applicable_evidence__"
CERTIFICATE_COMPONENT = {
    "source_identity_version": "source_GO",
    "citation_novelty_coverage": "source_GO",
    "proof_truth": "proof_GO",
    "proof_scope_coverage": "proof_GO",
    "implementation_reproducibility": "implementation_GO",
    "simulation_inference_eligibility": "simulation_GO",
    "artifact_lineage_freshness": "artifact_GO",
    "manuscript_wording_eligibility": "writing_GO",
}
Node = tuple[str, str]
check_bindings = runpy.run_path(str(Path(__file__).with_name("content_bindings.py")))[
    "check_bindings"
]


def structural_failure(errors: list[str], upstream: Any = None) -> dict[str, Any]:
    return {
        "schema_version": REPORT_VERSION,
        "structural_validity": {"valid": False, "errors": sorted(set(errors))},
        "upstream_validation": upstream,
        "scientific_eligibility": {"eligible": False, "evaluable": False},
        "release_permitted_from_record": False,
        "exit_code": 2,
        "scope": "Recorded contract consistency only; underlying scientific evidence is not verified.",
    }


def load_validator(path: Path) -> Callable[[Any], dict[str, Any]]:
    # Do not create bytecode files beside the read-only installed validator.
    sys.dont_write_bytecode = True
    namespace = runpy.run_path(str(path.resolve()))
    validator = namespace.get("validate")
    if not callable(validator):
        raise ValueError("validator must expose callable validate(data)")
    return validator


def call_validator(validator: Callable, data: Any) -> dict[str, Any]:
    result = validator(copy.deepcopy(data))
    if not isinstance(result, dict) or type(result.get("valid")) is not bool:
        raise ValueError("validator must return an object containing boolean valid")
    if not isinstance(result.get("errors"), list) or not all(
        isinstance(item, str) for item in result["errors"]
    ):
        raise ValueError("validator must return an errors array of strings")
    if result["valid"] != (not result["errors"]):
        raise ValueError("validator returned inconsistent valid/errors fields")
    return result


def build_graph(
    claims: dict[str, dict], sidecar: Any
) -> tuple[dict[Node, set[Node]], list[str]]:
    certificates = {
        cid: set(record["applicable_certificates"]) or {MISSING_CERTIFICATE}
        for cid, record in claims.items()
    }
    graph = {(cid, cert): set() for cid in claims for cert in certificates[cid]}
    pairs = {
        (cid, dep) for cid, record in claims.items() for dep in record["dependencies"]
    }
    if sidecar is None:
        for consumer, dependency in pairs:
            for cert in certificates[consumer]:
                graph[(consumer, cert)].update(
                    (dependency, source) for source in certificates[dependency]
                )
        return graph, []

    errors: list[str] = []
    if not isinstance(sidecar, dict) or sidecar.get("schema_version") != EDGE_VERSION:
        return graph, [f"edges sidecar must have schema_version={EDGE_VERSION}"]
    if set(sidecar) - {"schema_version", "edges"}:
        errors.append("edges sidecar contains unknown top-level fields")
    if not isinstance(sidecar.get("edges"), list):
        return graph, errors + ["edges sidecar edges must be an array"]
    covered: set[tuple[str, str]] = set()
    seen: set[tuple[str, str, str, str]] = set()
    fields = {
        "consumer_claim_id",
        "dependency_claim_id",
        "consumer_certificate",
        "dependency_certificates",
        "required",
    }
    for index, edge in enumerate(sidecar["edges"]):
        prefix = f"edges[{index}]"
        if not isinstance(edge, dict) or set(edge) != fields:
            errors.append(f"{prefix} must contain exactly {sorted(fields)}")
            continue
        consumer, dependency = edge["consumer_claim_id"], edge["dependency_claim_id"]
        target, sources = edge["consumer_certificate"], edge["dependency_certificates"]
        if not all(isinstance(value, str) for value in (consumer, dependency, target)):
            errors.append(
                f"{prefix} claim IDs and consumer_certificate must be strings"
            )
            continue
        if (consumer, dependency) not in pairs:
            errors.append(f"{prefix} is not a registered claim dependency")
            continue
        if target not in certificates[consumer] or target == MISSING_CERTIFICATE:
            errors.append(f"{prefix} consumer_certificate is not applicable")
            continue
        if type(edge["required"]) is not bool:
            errors.append(f"{prefix}.required must be boolean")
            continue
        if (
            not isinstance(sources, list)
            or not sources
            or not all(isinstance(s, str) for s in sources)
        ):
            errors.append(
                f"{prefix}.dependency_certificates must be a non-empty string array"
            )
            continue
        if len(set(sources)) != len(sources):
            errors.append(f"{prefix} repeats a dependency certificate")
        covered.add((consumer, dependency))
        for source in sources:
            if source not in certificates[dependency] or source == MISSING_CERTIFICATE:
                errors.append(
                    f"{prefix} dependency certificate {source} is not applicable"
                )
                continue
            identity = (consumer, target, dependency, source)
            if identity in seen:
                errors.append(f"{prefix} repeats certificate edge {identity}")
            seen.add(identity)
            if edge["required"]:
                graph[(consumer, target)].add((dependency, source))
    for pair in sorted(pairs - covered):
        errors.append(
            f"edges sidecar omits registered dependency {pair[0]} -> {pair[1]}"
        )
    return graph, errors


def check_contract(
    data: Any, validator: Callable, sidecar: Any = None, *,
    bindings: Any = None, project_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return a deterministic report without writing input or evidence files."""
    try:
        upstream = call_validator(validator, data)
        # The legacy validator combines schema errors with release decisions.
        # Recheck an otherwise identical copy with well-typed GO booleans withheld
        # to separate structural validity from our own eligibility computation.
        structural_data = copy.deepcopy(data)
        if isinstance(structural_data, dict) and isinstance(
            structural_data.get("release_vector"), dict
        ):
            for key, value in structural_data["release_vector"].items():
                if type(value) is bool:
                    structural_data["release_vector"][key] = False
        structure = call_validator(validator, structural_data)
    except Exception as exc:
        return structural_failure(
            [f"validator/input failure: {type(exc).__name__}: {exc}"]
        )
    if not structure["valid"]:
        return structural_failure(structure["errors"], upstream)

    claims = {item["claim_id"]: item for item in data["claims"]}
    graph, edge_errors = build_graph(claims, sidecar)
    for collection in ("root_errors", "coverage_blockers"):
        for record in data[collection]:
            if (
                "certificate" in record
                and record["certificate"]
                not in claims[record["claim_id"]]["applicable_certificates"]
            ):
                edge_errors.append(
                    f"{collection} record has a non-applicable certificate"
                )
    if edge_errors:
        return structural_failure(edge_errors, upstream)

    roots = {node for node in graph if claims[node[0]]["required"]}
    required = set(roots)
    pending = list(roots)
    while pending:
        for dependency in graph[pending.pop()]:
            if dependency not in required:
                required.add(dependency)
                pending.append(dependency)

    required_claims = {node[0] for node in required}
    try:
        content_report, binding_errors = check_bindings(
            data, bindings, project_root, required_claims
        )
    except Exception as exc:
        return structural_failure(
            [f"bindings/input failure: {type(exc).__name__}: {exc}"], upstream
        )
    if binding_errors:
        return structural_failure(binding_errors, upstream)

    reasons: dict[str, dict[str, Any]] = {}
    local: dict[Node, set[str]] = {node: set() for node in graph}

    def add_reason(node: Node, kind: str, identifier: str, **extra: Any) -> None:
        # JSON encoding is unambiguous even when a user ID contains punctuation.
        key = json.dumps([kind, node[0], node[1], identifier], separators=(",", ":"))
        reasons[key] = {
            "kind": kind,
            "claim_id": node[0],
            "certificate": node[1],
            "id": identifier,
            **extra,
        }
        local[node].add(key)

    for node in graph:
        cid, cert = node
        if cert == MISSING_CERTIFICATE:
            add_reason(node, "missing_evidence", "no-applicable-certificates")
        elif claims[cid]["state"][cert] != "PASS":
            add_reason(
                node, "certificate_state", cert, state=claims[cid]["state"][cert]
            )
    for collection, id_key, kind in (
        ("root_errors", "error_id", "root_error"),
        ("coverage_blockers", "blocker_id", "coverage_blocker"),
    ):
        for record in data[collection]:
            # A claim-wide error remains one owned root even when it governs
            # several certificates. Consumers inherit that root's identity.
            key = json.dumps(
                [kind, record["claim_id"], record.get("certificate"), record[id_key]],
                separators=(",", ":"),
            )
            reasons[key] = {
                "kind": kind,
                "claim_id": record["claim_id"],
                "certificate": record.get("certificate"),
                "id": record[id_key],
            }
            if "owner" in record:
                reasons[key]["owner"] = record["owner"]
            for node in graph:
                if node[0] == record["claim_id"] and (
                    "certificate" not in record or node[1] == record["certificate"]
                ):
                    local[node].add(key)

    for target in content_report["targets"]:
        if target["status"] == "unchanged" or (
            target["status"] == "unbound" and not target["required"]
        ):
            continue
        for cid in target["blocking_claim_ids"]:
            key = json.dumps(
                ["content_binding", cid, target["target_kind"], target["target_id"]],
                separators=(",", ":"),
            )
            reasons[key] = {
                "kind": "content_binding", "claim_id": cid, "certificate": None,
                "id": target["target_id"], "target_kind": target["target_kind"],
                "status": target["status"], "record_matches": target["record_matches"],
                "support_ownership_unknown": target["support_ownership_unknown"],
            }
            for node in graph:
                if node[0] == cid:
                    local[node].add(key)

    # A dependency-first traversal computes the full meet without recursion.
    waiting = {node: len(dependencies) for node, dependencies in graph.items()}
    consumers: dict[Node, set[Node]] = defaultdict(set)
    for node, dependencies in graph.items():
        for dependency in dependencies:
            consumers[dependency].add(node)
    ready = deque(sorted(node for node, count in waiting.items() if not count))
    effective_reasons: dict[Node, set[str]] = {}
    while ready:
        node = ready.popleft()
        effective_reasons[node] = set(local[node])
        for dependency in graph[node]:
            effective_reasons[node].update(effective_reasons[dependency])
        for consumer in sorted(consumers[node]):
            waiting[consumer] -= 1
            if not waiting[consumer]:
                ready.append(consumer)
    if len(effective_reasons) != len(graph):
        return structural_failure(["certificate dependency cycle"], upstream)

    selected_reasons = (
        set().union(*(effective_reasons[node] for node in required))
        if required
        else set()
    )
    affected = sorted(node for node in required if effective_reasons[node])
    content_artifacts = {
        target["target_id"]: target for target in content_report["targets"]
        if target["target_kind"] == "artifact"
    }
    relevant_artifacts = [
        item
        for item in data["artifacts"]
        if (content_artifacts[item["artifact_id"]]["required"] if content_artifacts
            else required_claims.intersection(item["claim_ids"]))
    ]
    stale_artifacts = sorted(
        item["artifact_id"]
        for item in relevant_artifacts
        if item["freshness"] == "stale"
    )
    artifact_assessment = []
    for artifact in sorted(data["artifacts"], key=lambda item: item["artifact_id"]):
        content = content_artifacts.get(artifact["artifact_id"])
        support_ids = content["blocking_claim_ids"] if content else artifact["claim_ids"]
        support_reasons = set().union(*(
            effective_reasons[node] for node in graph
            if node[0] in support_ids
        ))
        needs_review = bindings is not None and (
            bool(support_reasons) or (content is not None and content["status"] not in {"unchanged", "unbound"})
        )
        artifact_assessment.append({
            "artifact_id": artifact["artifact_id"],
            "required": content["required"] if content else bool(required_claims.intersection(artifact["claim_ids"])),
            "recorded_freshness": artifact["freshness"],
            "effective_freshness": "needs_review" if needs_review else artifact["freshness"],
            "content_status": content["status"] if content else "not_checked",
            "reason_ids": sorted(support_reasons) if bindings is not None else [],
        })
    affected_required_artifacts = sorted(
        item["artifact_id"] for item in artifact_assessment
        if item["required"] and item["effective_freshness"] == "needs_review"
    )
    scientific_eligible = bool(roots) and not affected

    components: dict[str, bool | None] = {}
    for component in sorted(set(CERTIFICATE_COMPONENT.values())):
        component_nodes = [
            node for node in required if CERTIFICATE_COMPONENT.get(node[1]) == component
        ]
        value = (
            all(not effective_reasons[node] for node in component_nodes)
            if component_nodes
            else None
        )
        if component == "artifact_GO" and relevant_artifacts:
            value = value is not False and not stale_artifacts and not affected_required_artifacts
        components[component] = value

    release = data["release_vector"]
    vector_errors: list[str] = []
    if release["schema_GO"] is not True:
        # Withholding a gate is permitted. It cannot support a positive final GO.
        if release["scientific_GO"] or release["submission_GO"]:
            vector_errors.append(
                "positive scientific_GO/submission_GO requires schema_GO"
            )
    for component, eligible in components.items():
        if eligible is False and release[component]:
            vector_errors.append(
                f"{component} is true but its required recorded support is ineligible"
            )
        if (
            component != "artifact_GO"
            and eligible is not None
            and release["scientific_GO"]
            and not release[component]
        ):
            vector_errors.append(f"scientific_GO requires applicable {component}")
    if release["scientific_GO"] and not scientific_eligible:
        vector_errors.append(
            "scientific_GO is true but required recorded support is ineligible or absent"
        )
    if release["artifact_GO"] and stale_artifacts:
        vector_errors.append("artifact_GO is true with stale required artifacts")
    if release["submission_GO"] and (
        not release["scientific_GO"]
        or not release["artifact_GO"]
        or not scientific_eligible
        or components["artifact_GO"] is not True
        or not relevant_artifacts
    ):
        vector_errors.append(
            "submission_GO requires eligible scientific and artifact gates with registered required artifacts"
        )

    certificate_report = []
    not_evaluable: set[str] = set()
    for node in sorted(required):
        recorded = claims[node[0]]["state"].get(node[1])
        effective = (
            recorded
            if recorded not in (None, "PASS")
            else ("NOT_EVALUABLE" if effective_reasons[node] else "PASS")
        )
        if effective == "NOT_EVALUABLE":
            not_evaluable.add(node[0])
        certificate_report.append(
            {
                "claim_id": node[0],
                "certificate": node[1],
                "recorded_state": recorded,
                "effective_state": effective,
                "eligible": not effective_reasons[node],
                "reason_ids": sorted(effective_reasons[node]),
            }
        )
    if not roots:
        reasons["missing-required-claims"] = {
            "kind": "missing_evidence",
            "id": "no-required-claims",
        }
        selected_reasons.add("missing-required-claims")

    evidence_incomplete = any(
        reasons[key]["kind"] in {"missing_evidence", "coverage_blocker", "content_binding"}
        or reasons[key].get("state") == "PARTIAL"
        for key in selected_reasons
    )

    exit_code = (
        0 if scientific_eligible and not stale_artifacts
        and not affected_required_artifacts and not vector_errors else 1
    )
    return {
        "schema_version": REPORT_VERSION,
        "structural_validity": {"valid": True, "errors": []},
        "upstream_validation": upstream,
        "dependency_mode": "typed"
        if sidecar is not None
        else "legacy-all-applicable-certificates",
        "content_verification": content_report,
        "scientific_eligibility": {
            "eligible": scientific_eligible,
            "evaluable": not evidence_incomplete and not not_evaluable,
            "required_root_claims": sorted({node[0] for node in roots}),
            "required_claim_closure": sorted(required_claims),
            "certificates": certificate_report,
            "not_evaluable": sorted(not_evaluable),
            "blocking_reasons": [
                {"reason_id": key, **reasons[key]} for key in sorted(selected_reasons)
            ],
        },
        "component_eligibility": components,
        "stale_required_artifacts": stale_artifacts,
        "affected_required_artifacts": affected_required_artifacts,
        "artifact_assessment": artifact_assessment,
        "declared_release_vector": release,
        "release_vector_consistency": {
            "valid": not vector_errors,
            "errors": sorted(set(vector_errors)),
        },
        "release_permitted_from_record": exit_code == 0
        and release["schema_GO"]
        and release["submission_GO"],
        "exit_code": exit_code,
        "scope": (
            "Recorded contract consistency plus registered byte/record identity; scientific correctness, semantic mappings, unregistered dependencies, and human approval are not verified."
            if bindings is not None else
            "Record-only contract consistency; underlying scientific evidence, semantic mappings, actual hashes, and human approval are not verified."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("contract", type=Path)
    parser.add_argument(
        "--validator",
        type=Path,
        required=True,
        help="Trusted installed validate_research_contract.py",
    )
    parser.add_argument(
        "--edges", type=Path, help="Optional complete typed dependency sidecar"
    )
    parser.add_argument("--bindings", type=Path, help="Optional registered file/fragment content bindings")
    parser.add_argument("--project-root", type=Path, help="Explicit root for content binding relative paths")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.contract.read_text(encoding="utf-8"))
        sidecar = (
            json.loads(args.edges.read_text(encoding="utf-8")) if args.edges else None
        )
        if args.edges and sidecar is None:
            raise ValueError("an explicitly supplied edges sidecar cannot be null")
        if bool(args.bindings) != bool(args.project_root):
            raise ValueError("--bindings and --project-root must be supplied together")
        bindings = json.loads(args.bindings.read_text(encoding="utf-8")) if args.bindings else None
        if args.bindings and bindings is None:
            raise ValueError("an explicitly supplied bindings sidecar cannot be null")
        report = check_contract(
            data, load_validator(args.validator), sidecar,
            bindings=bindings, project_root=args.project_root,
        )
    except Exception as exc:
        report = structural_failure(
            [f"input/validator failure: {type(exc).__name__}: {exc}"]
        )
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if args.pretty else None,
        )
    )
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
