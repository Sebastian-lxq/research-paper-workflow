# State schemas and compatibility

The workflow exchanges strict JSON records and keeps a small amount of
project-local state. The machine-readable inventory is
[`schemas.json`](../plugins/research-paper-workflow/schemas.json). The release
validator proves that every registered owner exists, every source marker remains
implemented, every replacement resolves, and every named `*.vN` schema in the
bundled controllers is registered.

This registry is an index and lifecycle contract. The controller validators are
the executable structural specifications; the registry does not pretend that a
schema name alone establishes scientific validity.

## Format classes

| Role | Meaning | Compatibility expectation |
| --- | --- | --- |
| `input-contract` | A project or caller supplies the record. | Exact schema identifier and documented fields are required. Unknown fields normally fail closed. |
| `persistent-state` | A controller stores or reads the record across invocations. | Current formats remain readable throughout the declared release series. Writes are atomic or append-only where the controller promises that property. |
| `derived-report` | A controller generates a rebuildable result or status view. | Consumers must inspect the schema identifier. Reports are evidence summaries, not a second source of scientific truth. |
| `internal-control` | Private controller integrity state. | No public authoring contract; only the owning controller may create or modify it. |

`compatibility` in the registry states what the current implementation actually
does—for example `accepted`, `generated`, or `read-existing-state-only`. It is
not a claim that every future preview release will accept the format.

## Preview compatibility policy

The v0.1.x series follows `preview-no-silent-mutation`:

1. A named identifier such as `paper-revision-contract.v2` is not silently
   reused for a different record shape or meaning.
2. Patch releases in the same `0.1.x` series retain current input and persistent
   readers. A security or integrity repair may reject data that was malformed,
   unsafe, or outside the documented contract.
3. A breaking format change requires a new identifier, a registry entry, a
   changelog note, updated fixtures, and an explicit migration or coexistence
   rule. Preview minor releases may retire compatibility only after recording
   that change; semantic versioning before 1.0 does not imply permanent support.
4. Strict validators reject unknown fields. Additive fields therefore also need
   a new schema version unless the existing format explicitly declares an
   extension point.
5. Derived reports must use a different identifier from their input contract.
   For example, `empirical-result-contract.v1` produces
   `empirical-result-contract-status.v1`; the two shapes cannot be confused.

## Current coexistence and migration rules

There is no generic in-place migrator in v0.1.1. That is deliberate: research
records may contain judgments that cannot be safely inferred by a mechanical
conversion.

- `research-operation-event.v1` and `.v2` coexist in the same append-only log.
  Version 2 adds dependency and wait contracts; new waiting events must use v2.
  Existing v1 events are not rewritten.
- Existing revision cycles containing `paper-revision-contract.v1` and
  `paper-revision-issues.v1` remain readable. New cycles require the v2 contract
  and v2 issue package so non-regression objectives and admission evidence are
  explicit.
- `research-operations-status.v1` is still generated for an all-v1 operation
  log; a log containing v2 events produces `research-operations-status.v2`.
- The integer-versioned probe run, probe decision, and `revisions.yaml` ledger
  are controller-local formats. Their compatibility applies only inside the
  owning controller's directory and must not be treated as globally named APIs.

When a future migration is added, it must validate the source first, write a new
record instead of mutating the only copy, preserve evidence hashes or explain
why they change, run both old-state and migrated-state fixtures, and leave an
auditable rollback path.

## Inventory by controller

| Owner | Current named formats | Legacy-readable formats |
| --- | --- | --- |
| `workflow_state.py` | `paper-workflow-plan.v1`, `paper-workflow-status.v1` | — |
| `revision_cycle.py` | `paper-revision-contract.v2`, `paper-revision-issues.v2`, `paper-revision-cycle.v1`, `paper-revision-event.v1`, `paper-revision-review.v1`, `paper-revision-retrospective.v1`, `paper-non-regression-report.v1`, `paper-revision-cycle-status.v1` | `paper-revision-contract.v1`, `paper-revision-issues.v1` |
| `research_operations.py` | `research-operation-event.v2`, `research-operations-status.v2` | `research-operation-event.v1`, `research-operations-status.v1` |
| `resume_view.py` | `research-resume-adapter.v1`, `research-resume-view.v1`, `research-resume-freshness.v1` | — |
| `check_release_handoff.py` | `research-handoff-edges.v1`, `research-handoff-check.v1` | — |
| `content_bindings.py` | `research-content-bindings.v1`, `research-content-bindings-report.v1` | — |
| `review_handoff.py` | `review-handoff-spec.v1`, `review-handoff-criteria.v1`, `review-handoff-evidence.v1` | — |
| `idea_portfolio.py` | `research-idea-portfolio.v1`, `research-idea-portfolio-status.v1` | — |
| `empirical_contract.py` | `empirical-result-contract.v1`, `empirical-result-contract-status.v1` | — |
| `proof_lineage.py` | `proof-lineage-manifest.v1`, `proof-lineage-status.v1` | — |
| `token_evaluation.py` | `research-token-evaluation.v1`, `research-token-evaluation-status.v1` | — |

`review-handoff-controller.v1` is intentionally internal. The full registry,
including the three controller-local integer formats, is authoritative for the
release series.
