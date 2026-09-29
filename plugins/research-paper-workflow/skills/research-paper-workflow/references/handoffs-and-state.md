# Handoffs, progress, and resuming work

Read this reference for a multi-stage paper. The workflow records **which stage
can proceed**, while specialist evidence records determine **what can be claimed**.
Neither a filled checklist nor a zero exit code proves a scientific result.

## One owner for each kind of state

| Owner | Canonical information | Workflow consumes |
| --- | --- | --- |
| Existing project and author decisions | Active manuscript, scope, language, locks and authorized actions | Current objective and work boundaries |
| Idea record plus optional portfolio sidecar | Candidate arguments, search evidence and decisions remain in the record; sidecar exposes IDs, frontiers, probes and reopen conditions | Selected candidate and bounded novelty status |
| `write-econometrics-paper-v3` `.paper/` | Claims, citations, exhibits, revisions and journal overlay | IDs, exact evidence paths and permitted wording |
| `prove-econometrics-theory-v2` | Statements, assumptions, obligations, proofs and independent checks | Version-bound proof handoff plus an optional hash-bound lineage projection |
| `audit-numerical-simulations-v2` | Design, code/config, RNG, actual replication ledger and inference | Runnable preparation or actual validated results |
| Empirical branch | Data lineage, design, analysis and actual outputs | Claim-to-estimand-to-result mapping |
| Optional supervisor `.research-supervision/` | Its contract, three gates and exact candidate verdict | Scoped independent findings and verdict |
| This workflow `.paper/workflow/` | Frozen stage plan and artifact-bound stage receipts; optional operations log records execution only | Progress, stale work, observed resource use and concrete next actions |

Reuse equivalent existing stores instead of competing with them. Before a
manuscript exists, workflow framing/idea records can live alongside a new research
brief. When the manuscript scaffold exists, read writer-v3 and use its actual
initializer for missing writer state only. Its initializer expects an existing
active manuscript; do not invent a completed draft to satisfy it. Existing
`.paper` files must survive workflow initialization unchanged.

For novelty-sensitive, multi-candidate, long or resumed idea work, use
[search-and-portfolio-control.md](search-and-portfolio-control.md). For long,
costly, parallel or autonomous execution, use
[research-operations.md](research-operations.md). Both controllers are optional
outside their stated scope and bind existing evidence instead of replacing it.
For a long, multi-stage, autonomous, or explicitly token-sensitive project, use
[token-efficiency.md](token-efficiency.md). Its paired evaluation and wait
barrier are derived orchestration evidence, not a replacement for the owner
records in the table above.

For accumulated user/mentor/AI comments, map the existing records using
[feedback-and-decisions.md](feedback-and-decisions.md). The workflow consumes
decisions and implementation evidence; it does not duplicate the writer's revision
ledger or the supervisor's findings. A current summary links to those owners.

For iterative revision, use [iterative-optimization.md](iterative-optimization.md).
Keep the cycle's selected issues and its single active issue in existing plan or
revision records; they are not new machine stages or a substitute for claim-level
evidence. Pass the active issue, permitted dependent edits, pending issues and
single-item versus continuous-cycle intent to each specialist and on resume.
For a material issue, also pass the affected frozen primary objectives,
protected invariants, trade-off bounds, paired evidence requirements, and the
rollback condition from
[non-regression-contract.md](non-regression-contract.md).

For an explicitly requested autonomous cycle, read
[continuous-revision.md](continuous-revision.md). The writer's
`.paper/revisions.yaml` remains the issue authority. The derived
`.paper/workflow/revision-cycle.json` may contain only the frozen contract,
manuscript and review hashes, issue IDs, queue, pause and escalation references.
If the revision ledger changes outside the controller, run its `sync` preview;
never silently refresh its ledger hash or preserve cached clean-review passes.
New v2 cycles also consume the project-local non-regression report named by the
frozen contract. That report is derived orchestration evidence: it points to
current specialist-owned evidence snapshots but does not replace claims, proofs,
results, citations, or their ledgers. Full reviews bind its current hash as well
as the manuscript hash. Legacy v1 cycle state remains readable without this
additional gate.

## What to hand off

Each substantive handoff identifies the object/version, exact inputs and source
locators, output files, actual verification, unresolved obligations, permitted
wording, and next consumer. Record required versus optional scientific
dependencies explicitly. A same-named theorem or table is not a version match.

Use the installed specialist's `research-release-contract` schema and validator
when crossing proof, simulation, source and writing boundaries. Do not replace
the writer's claim ledger with workflow receipts. A release contract is the
cross-skill view of the evidence, not a second editable source of its truth.

For theory-bearing handoffs, use
[proof-lineage.md](proof-lineage.md) and `scripts/proof_lineage.py` when the
provider can export the public interface. The manifest records only IDs,
versions, relationships, status, locators, hashes, and bounded release scope.
It must not duplicate theorem or proof prose. A consumable lineage is required
only when the project elects this interface; it cannot upgrade the provider's
release verdict or establish mathematical correctness.

For a simulation-deferred paper, retain the actual pending simulation objects
and prohibit result-dependent assertions. A scoped verified-theory delivery may
exclude those assertions from its required release closure, with that exclusion
made visible. Never remove a required dependency merely to obtain a green check.

## Stage helper commands

Resolve the installed workflow directory as `WORKFLOW` and the existing absolute
research project directory as `PROJECT`. The shell variables below are illustrative
path bindings, not paths to create blindly. Python 3.9+ on macOS/Linux is enough;
the scripts use the standard library and do not install anything.

```bash
python3 -B "$WORKFLOW/scripts/workflow_state.py" init \
  --project "$PROJECT" --paper-type methods --simulation deferred
```

Inspect the proposed plan, then repeat with `--write`. Defaults are a methods
paper with production simulations deferred. Choose `theory`, `empirical`, or
`hybrid` when appropriate; `--empirical required` adds an application to a
methods/theory paper. Empirical/hybrid papers cannot disable empirical evidence.
Use `--simulation not-applicable` only when simulations genuinely do not govern
the agreed contribution, never for a resource shortage.

Create a receipt as a normal project artifact, then preview and record it:

```bash
python3 -B "$WORKFLOW/scripts/workflow_state.py" record \
  --project "$PROJECT" --stage framing --state ready \
  --receipt "$PROJECT/research/receipts/framing.json"
```

Repeat with `--write` only after checking its actual artifacts. Example receipt:

```json
{
  "summary": "Research question, contribution boundary and acceptance criteria recorded.",
  "artifacts": ["research/brief.md"],
  "checks": {
    "scope": {
      "state": "pass",
      "evidence": ["research/brief.md"],
      "note": "The brief identifies the question, nonclaims and permitted work."
    }
  },
  "worker_id": "primary-worker",
  "reviewer_id": null,
  "next_action": "Compare candidate ideas and their cheapest falsifiers."
}
```

The example asserts a result only if the referenced brief actually exists and
contains the stated evidence. Do not bulk-fill every check with `pass`. Artifacts
are project-relative regular files, with no traversal or symlinks; generated
workflow state cannot serve as its own scientific evidence. Each pass check must
point to a file included in `artifacts`. Snapshot all load-bearing inputs and
outputs, including code/config and review records; omitted dependencies are not
inferred. Use existing artifact paths instead of reorganizing a project.

`ready` requires all applicable stage checks and current ready prerequisites.
`active` and `blocked` preserve partial work and a concrete `next_action`.
`deferred` is allowed only for production `simulation_run`. Missing real data,
an unproved required result, or non-runnable simulation preparation is blocked,
not hidden inside the simulation exception. Before prerequisites pass, work can
still be drafted/recorded as active; the gate restricts readiness, not useful work.

## Check meanings

The script's `STAGES` constant is the executable list. These check IDs are
receipt fields, not instructions to manufacture scientific support:

| Stage | Required checks |
| --- | --- |
| framing | `scope` |
| ideas | `feasibility`, `falsifiers` |
| literature | `source_claims`, `nearest_neighbors` |
| design | `identification`, `evidence_plan` |
| theory, when applicable | `proof_scope`, `independent_proof_review`; when the proof-lineage interface is used, also attach its current status report as evidence |
| empirical, when applicable | `data_lineage`, `inference`, `result_reproduction` |
| simulation_design, when applicable | `runnable_handoff`, `implementation_checks` |
| simulation_run, when applicable | `actual_results`, `calibration`, `mc_precision` |
| manuscript | `wording`, `citations`, `appendices` |
| verification | `cross_file`, `handoff_integrity`, `reproducibility`, `rendered_candidate` |
| review | `independent_scientific_review` |
| revision | `findings_resolved`, `semantic_sync` |
| delivery | `scope_label`, `handoff_complete` |
| submission candidate | `journal_policy`, `release_candidate`, `author_approval` |

For theoretical work, `identification` means a well-defined mathematical target
and assumptions, not mandatory causal identification. `appendices` means that
required supporting material is complete or an evidenced judgment that none is
needed. No accepted review findings can still satisfy `findings_resolved` through
a real no-open-findings report. Never invent a theorem, application or appendix.

Ready theory, review and submission receipts require distinct worker/reviewer
identifiers. This is an integrity check, not proof of independence. Preserve the
actual independently produced report, reviewer identity/scope and candidate
version. `author_approval` needs the author's actual approval for the candidate;
an AI reviewer cannot supply it, and recording it does not submit the paper.

## Resume and scope changes

```bash
python3 -B "$WORKFLOW/scripts/workflow_state.py" status --project "$PROJECT"
```

Read `outcome`, `stages`, `reasons`, `next_runnable`, `deferred`, and `next_actions`.
Rehashing catches changed/missing recorded artifacts. New prerequisite receipts
invalidate downstream readiness even if filenames have not changed. Unrecorded,
unrelated files do not invalidate work. Recheck and append receipts only after
the corresponding work is actually repaired; never edit old event history.

In a deliberately partial resume workspace, resolve the authoritative pointer,
active stage, dependency edges and bound artifact hashes first. Absence of an
artifact that is not bound by the active receipt is only a limit on what can be
reinspected; it does not reopen completed work, freshness, restoration, or future
package checks. Reopen a gate only when current state marks it active/blocked, a
dependency is unresolved, or an artifact named by an authoritative binding is
missing or has changed.

Production result arrival, or mutation of already-bound simulation evidence,
reopens manuscript and downstream verification/review/delivery. A deferred plan
can later record real `simulation_run` results without reinitialization. Preserve
the originally frozen execution intent; actual status comes from current evidence.
While production work is still running, record its handle as a v2 waiting
operation and prevent dependent operations from starting. Continue only branches
with no dependency on that result; do not draft result-dependent prose on a
speculative value merely to avoid waiting.

For a material change of paper scope, record the author's decision and a design
delta, then initialize a **new named track**, for example with
`--track revised-scope --paper-type hybrid --simulation deferred`. All three
commands accept `--track`; omitting it selects `main`. The main ledger remains
at `.paper/workflow/`; named tracks use `.paper/workflow/tracks/<name>/`.
Include the superseded track/plan identity and reason in the new framing brief.
The helper does not pick an active track: identify the active one explicitly in
the project brief and every resume command. It never merges approvals between
tracks. Reuse scientific artifacts after revalidation; new receipts must reflect
the new scope. An existing track cannot be overwritten by `init`.

## Cross-skill release check

The existing structure validator alone can accept a downstream PASS despite a
required consumed upstream PARTIAL/FAIL. Use this additional read-only check:

```bash
python3 -B "$WORKFLOW/scripts/check_release_handoff.py" \
  "$PROJECT/research-release-contract.json" \
  --validator "$WRITER/scripts/validate_research_contract.py" --pretty
```

Resolve `WRITER` to the trusted installed writer-v3 skill. The bridge executes
that validator as local code; do not pass a downloaded or project-supplied
untrusted script. Without `--edges`, every registered dependency conservatively
consumes all upstream applicable certificates. With `--edges`, provide a complete
`research-handoff-edges.v1` sidecar whose edges specify `consumer_claim_id`,
`dependency_claim_id`, `consumer_certificate`, `dependency_certificates`, and
boolean `required`. Every registered claim pair must be mapped; no new edge is
inferred. Scientific review must justify the mapping and any optional edge.
The script's help includes the exact sidecar example. Root errors and coverage
blockers may specify `certificate`; otherwise their claim-wide scope is retained.

The bridge separates `structural_validity`, `scientific_eligibility`,
`component_eligibility`, `release_vector_consistency`, and
`release_permitted_from_record`. The last field still concerns the **record**,
not mathematical truth or permission to publish. Exact source verification,
specialist checks and author approval remain separate. Without content bindings,
current file hashes also remain outside this check. For actual-file/fragment
bindings, add `--bindings` and `--project-root` as described in
[content-bindings.md](content-bindings.md); this feeds observed freshness issues
into the existing dependency graph without rewriting its authoritative records.

## Outcomes and exit codes

| Current evidence | Workflow outcome |
| --- | --- |
| Required non-simulation work unfinished/stale | `in-progress` |
| Scoped manuscript and runnable preparation ready; production simulation missing | `manuscript-ready-except-simulations` |
| Full manuscript delivered, candidate/author/journal approval not complete | `manuscript-ready-for-author-review` |
| All applicable recorded stages, candidate checks and approval ready | `submission-candidate` |

Workflow `status` returns 0 only for `submission-candidate`, 1 for a valid but
less complete outcome, and 2 for invalid input/state. `init`/`record` return 0
for a successful preview or write; this does not mean the paper is complete.
The handoff bridge returns 0 for consistent, eligible required recorded support,
1 for insufficient support/stale artifacts/contradictory GO, and 2 for invalid
input/structure/sidecar/validator. Inspect its release fields even after exit 0.
An exit 1 can be expected for an honest simulation-deferred contract; do not
weaken its evidence to make the command green.

Local hashes and history detect accidental or unanchored modifications, not
malicious replacement of the entire store. No state helper reads hidden reasoning,
authenticates a real person, verifies theorem truth, or provides background monitoring.
