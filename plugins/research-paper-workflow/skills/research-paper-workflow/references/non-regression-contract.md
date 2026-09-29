# Project-level non-regression contract

Read this reference before a material paper iteration. It defines the bounded
meaning of “positive revision” for the current project. It does **not** claim
that the candidate is better in every dimension, that no relevant literature
exists, or that a theorem, source claim, simulation, or empirical result is
true merely because a checklist passes.

## What the contract freezes

Define the following before evaluating the revised candidate:

1. **Primary objectives**: the specific outcomes that must improve, each with a
   baseline locator and a falsifiable improvement criterion.
2. **Protected scientific invariants**: objects that may not regress, such as
   the estimand or null, theorem scope, assumptions, proof validity, calibration,
   data lineage, claim strength, citation support, result provenance, or
   reproducibility.
3. **Allowed trade-offs**: a named benefit, the cost that may be accepted, its
   explicit bound, and the evidence needed to show the bound was respected.
   Silence is not permission to trade away a scientific property.
4. **Paired evidence requirements**: the baseline and candidate evidence to be
   compared under the same criterion. A favorable candidate-only observation is
   not evidence of improvement.
5. **Rollback conditions**: concrete triggers, a restorable baseline locator,
   and the required action: `rework`, `restore`, or `pause-author`.
6. **Whole-candidate dimensions**: the applicable final review areas selected
   from `research-positioning`, `theory`, `method`, `simulation`, `empirical`,
   `notation`, `writing`, and `integration`.

Do not write generic objectives such as “make the paper better.” Name the object,
version, observable criterion, evidence locator, and failure condition. A
criterion may be qualitative when the research object is qualitative, but it
must still distinguish `improved` from `not-improved` and identify who or what
evidence can make that judgment.

## Proportional use

For an ordinary single-item iteration, record a compact version in the existing
notes or revision log. One line per applicable field is enough for a local,
low-impact edit. Expand it when a change can affect claims, mathematical objects,
results, evidence versions, or several manuscript sections. Do not create a
second issue or claims database.

For `continuous-revision`, new cycles use
`paper-revision-contract.v2`. The contract contains this exact additional
object:

```json
{
  "non_regression": {
    "primary_objectives": [
      {
        "id": "OBJ-scope-alignment",
        "description": "Align the headline guarantee with the maintained null and proved scope.",
        "baseline_locator": "baseline/scope-audit.md#current-gap",
        "improvement_criterion": "The abstract, theorem, proof and conclusion state the same maintained null and scope."
      }
    ],
    "protected_invariants": [
      {
        "id": "INV-proof-validity",
        "description": "Preserve all previously verified proof obligations not superseded by an explicit design decision.",
        "baseline_locator": "proof/release-status.json",
        "preservation_check": "Every retained obligation remains verified for the current statement and assumptions."
      }
    ],
    "allowed_tradeoffs": [
      {
        "id": "TRD-exposition-length",
        "benefit": "Make the main identification argument self-contained.",
        "allowed_cost": "Additional main-text length.",
        "bound": "No more than one page and no removal of required appendix detail.",
        "evidence_requirement": "Rendered-page comparison plus appendix coverage check."
      }
    ],
    "paired_evidence_requirements": [
      {
        "id": "PAIR-scope",
        "baseline_locator": "baseline/scope-audit.md",
        "candidate_locator": "verification/scope-audit.md",
        "criterion": "Compare the same null, theorem scope, proof inputs and reader-facing claims."
      }
    ],
    "rollback": {
      "trigger_conditions": [
        "Any protected invariant is regressed.",
        "The primary objective is not improved after bounded rework.",
        "An allowed trade-off exceeds its frozen bound."
      ],
      "restore_locator": "baseline/candidate-manifest.json",
      "required_action": "rework"
    },
    "whole_candidate_dimensions": [
      "research-positioning",
      "theory",
      "writing",
      "integration"
    ],
    "report_path": "verification/non-regression-report.json"
  }
}
```

The full contract still carries all v1 fields. Its `stop_conditions` remain the
controller's fixed list; non-regression is an additional v2 readiness gate.
Existing v1 states remain readable, but `init` does not create new v1 cycles.

## Evaluate the current candidate

After all cycle issues are resolved and before the two clean full reviews,
create `paper-non-regression-report.v1` at the frozen `report_path`. Bind it to
the SHA-256 of the full frozen contract and the current manuscript. Cover every
frozen ID and whole-candidate dimension exactly once. Each result includes one
or more current project-relative evidence snapshots of the form
`{"path": "...", "sha256": "..."}`.

Use only these result states:

| Result | Passing state | Other states |
| --- | --- | --- |
| Primary objective | `improved` | `not-improved`, `unknown` |
| Protected invariant | `preserved` | `regressed`, `unknown` |
| Allowed trade-off | `within-bound` | `exceeded`, `unknown` |
| Paired evidence | `pass` | `fail`, `unknown` |
| Whole-candidate dimension | `pass` | `fail`, `unknown` |

The report has this exact shape (replace the illustrative hashes and expand the
rows to match the frozen contract exactly):

```json
{
  "schema": "paper-non-regression-report.v1",
  "contract_sha256": "<SHA-256 of the frozen full contract>",
  "candidate_sha256": "<SHA-256 of the current manuscript>",
  "objectives": [
    {
      "id": "OBJ-scope-alignment",
      "status": "improved",
      "evidence": [{"path": "verification/scope-audit.md", "sha256": "<current SHA-256>"}]
    }
  ],
  "invariants": [
    {
      "id": "INV-proof-validity",
      "status": "preserved",
      "evidence": [{"path": "proof/release-status.json", "sha256": "<current SHA-256>"}]
    }
  ],
  "tradeoffs": [
    {
      "id": "TRD-exposition-length",
      "status": "within-bound",
      "evidence": [{"path": "verification/rendered-page-comparison.md", "sha256": "<current SHA-256>"}]
    }
  ],
  "paired_evidence": [
    {
      "id": "PAIR-scope",
      "status": "pass",
      "evidence": [{"path": "verification/scope-paired-comparison.md", "sha256": "<current SHA-256>"}]
    }
  ],
  "whole_candidate": [
    {
      "dimension": "theory",
      "status": "pass",
      "evidence": [{"path": "reviews/final-theory-audit.md", "sha256": "<current SHA-256>"}]
    }
  ],
  "decision": "retain"
}
```

The final decision is `retain`, `rework`, or `rollback`. `retain` is eligible
only when every row is in its passing state. An `unknown` is pending evidence,
not a pass. When no trade-off was authorized, the frozen trade-off list and the
report's matching result list may both be empty.

The controller checks schema, exact ID coverage, current file hashes, contract
binding, manuscript binding, and the decision rule. It cannot decide whether an
evidence artifact is scientifically persuasive. The specialist owner and fresh
reviewers must inspect that substance.

## Retain, repair, or restore

- If an objective is not improved, do not call the iteration complete merely
  because nothing else regressed. Rework it or record a non-retain decision.
- If a protected invariant regresses, do not average it against improvements in
  other dimensions. Rework, restore, or pause according to the frozen rule.
- If a trade-off exceeds its bound, the current contract does not authorize it.
  Do not silently widen the bound after seeing the result; record an author
  decision and begin a superseding cycle when the research target truly changes.
- If paired evidence is stale, asymmetric, or inconclusive, use `unknown` and
  obtain the missing evidence.
- A candidate edit invalidates the report through its manuscript hash. A report
  edit invalidates clean full reviews through the report hash.

Each accepted full review of a v2 cycle must list the non-regression report in
its evidence and is stored against that report's hash. The final whole-manuscript
review therefore evaluates the same candidate and the same declared meaning of
“positive” that the controller uses for readiness.

The strongest warranted completion statement is: within the frozen objectives,
protected invariants, trade-off bounds, registered evidence, and review scope,
the current candidate passed the project-specific non-regression checks. Never
shorten this to “the paper necessarily improved in every respect.”
