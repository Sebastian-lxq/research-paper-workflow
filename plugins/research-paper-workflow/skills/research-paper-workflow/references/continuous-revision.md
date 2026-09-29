# Continuous revision mode

Read this reference when the user asks to keep revising a paper without a new
instruction for every dimension. This mode extends the ordinary one-active-issue
optimization cycle. It does not create a second claims or evidence database and
does not authorize submission, external communication, new data access, or
unbounded computation.

The target is `manuscript-ready-for-author-review`. A fixed round count or a
single paper score is not a stopping rule.

## Activate and freeze the cycle

Start from the current manuscript, writer `.paper/` state, specialist ledgers,
workflow status, feedback and author decisions. Use the writer initializer first
if `.paper/revisions.yaml` does not exist, and use `workflow_state.py init` first
if `.paper/workflow/plan.json` does not exist. Do not let the revision controller
initialize or replace those owners.

Create a project-local contract such as:

```json
{
  "schema": "paper-revision-contract.v2",
  "cycle_id": "author-review-2026-09",
  "mode": "continuous-revision",
  "objective": "Resolve the selected revision cycle to an author-reviewable manuscript.",
  "manuscript": {"path": "main.tex", "version": "draft-v7"},
  "scope": {
    "allowed_paths": ["main.tex", "sections", "appendix", "tables", "code"],
    "locked_paths": ["sections/author-note.tex"],
    "authorized_operations": [
      "edit-manuscript",
      "edit-proof",
      "edit-simulation-code",
      "run-local-compute",
      "update-project-state"
    ]
  },
  "resources": {
    "compute_limit": "local smoke/pilot plus the already authorized production inventory",
    "data_access": ["existing project data"],
    "external_access": false
  },
  "confidentiality": "local-only",
  "target": "manuscript-ready-for-author-review",
  "expert_authorization": {
    "status": "confirmed",
    "primary": "mentor-primary",
    "roundtable_members": [
      "mentor-primary",
      "mentor-secondary",
      "mentor-third"
    ],
    "source_locator": "current task: project-start authorization",
    "one_round_per_issue": true
  },
  "non_regression": {
    "primary_objectives": [
      {
        "id": "OBJ-author-review-readiness",
        "description": "Resolve the load-bearing defects that prevent an author-reviewable manuscript.",
        "baseline_locator": "baseline/revision-audit.md",
        "improvement_criterion": "Every admitted load-bearing defect is closed with current scientific evidence."
      }
    ],
    "protected_invariants": [
      {
        "id": "INV-scientific-scope",
        "description": "Preserve the maintained estimand or null, theorem scope, evidence ceilings and result provenance unless an author decision explicitly supersedes them.",
        "baseline_locator": "baseline/candidate-manifest.json",
        "preservation_check": "Current specialist ledgers and manuscript claims agree on these objects and their verified scope."
      }
    ],
    "allowed_tradeoffs": [],
    "paired_evidence_requirements": [
      {
        "id": "PAIR-cycle-objective",
        "baseline_locator": "baseline/revision-audit.md",
        "candidate_locator": "verification/final-revision-audit.md",
        "criterion": "Apply the same load-bearing defect and scientific-consistency checks to baseline and candidate."
      }
    ],
    "rollback": {
      "trigger_conditions": [
        "A protected scientific invariant regresses.",
        "The primary objective is not improved after bounded rework.",
        "An allowed trade-off exceeds its frozen bound."
      ],
      "restore_locator": "baseline/candidate-manifest.json",
      "required_action": "rework"
    },
    "whole_candidate_dimensions": [
      "research-positioning",
      "theory",
      "method",
      "simulation",
      "empirical",
      "notation",
      "writing",
      "integration"
    ],
    "report_path": "verification/non-regression-report.json"
  },
  "stop_conditions": [
    "no-open-p0-p1",
    "required-workflow-stages-ready",
    "current-artifacts-bound",
    "two-independent-clean-reviews",
    "p2-p3-closed-or-deferred"
  ],
  "pause_conditions": [
    "research-target-change",
    "evidence-insufficient-choice",
    "compute-budget-exceeded",
    "external-or-confidentiality-change",
    "external-action",
    "repeated-blocker"
  ]
}
```

New cycles require `paper-revision-contract.v2`. Legacy v1 states remain
readable so an existing project can resume, but they do not acquire a
machine-enforced non-regression report retroactively. Read
[non-regression-contract.md](non-regression-contract.md) to define the project-
specific fields; remove review dimensions that are genuinely inapplicable rather
than filling them with fictional evidence.

The controller accepts JSON-compatible YAML only. `allowed_paths` are explicit
project-relative files or directories; they are not globs. The named expert
panel must already be authorized in the current project. The controller records
and enforces that authorization but does not invoke an explicit-only mentor or
roundtable by itself.

Preview initialization, then write it:

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" init \
  --project "$PROJECT" --contract "$PROJECT/revision-contract.json"
python3 -B "$WORKFLOW/scripts/revision_cycle.py" init \
  --project "$PROJECT" --contract "$PROJECT/revision-contract.json" --write
```

The frozen state lives at `.paper/workflow/revision-cycle.json`. It contains the
contract, manuscript hash, issue IDs, queue, review references, pause and expert
escalation state. It never copies issue text, claims, proof evidence, results or
citations from their canonical owners.

The v2 non-regression block freezes what “positive” means before edits are
evaluated: at least one primary objective, at least one protected invariant, the
explicitly allowed trade-offs, paired evidence, rollback rules, and applicable
whole-candidate dimensions. Its report path is derived orchestration evidence,
not a second scientific ledger.

## Audit before queueing work

Audit only the active candidate and evidence needed for this cycle. Cover these
areas where applicable:

1. research question, estimand or null, motivation and contribution boundary;
2. assumptions, statements, proof obligations and rates;
3. statistic, algorithm, calibration and implementability;
4. simulation design, code/config, actual execution and result lineage;
5. data, estimand, inference and empirical result reproduction;
6. notation and mathematical object identity;
7. manuscript logic, citations, interpretation and limitations;
8. cross-file, table/figure, evidence-version and reproducibility consistency.

Also run the author-interrogation check. A fresh reader should be able to answer,
from the manuscript itself: What is H0 or the estimand? What object is built and
how? What is new relative to the nearest procedure? Which assumptions support
the guarantee? What did the simulation or empirical analysis actually run and
show? What is the practical meaning and stated limit? A failed answer becomes a
bounded issue; it is not repaired only in chat.

Do not equate a simulation plan, runnable code, pilot run, production run and
validated result. Give them separate evidence locators and preserve actual R/B,
failure lineage and version.

## Add canonical issues

Add the audit findings to the writer-owned `.paper/revisions.yaml` through an
issue package. The controller adds `cycle_id`, manuscript version, status,
implementation attempts and verification fields without changing schema version
1 or rewriting unrelated revision records.

New cycles require a v2 issue package. It adds a focus check to the existing
scientific fields: the issue must state how it relates to the frozen objective,
the concrete consequence of leaving it unresolved, and why it belongs in the
current cycle. Existing v1 cycles remain valid, but apply the same judgment when
resuming them.

```json
{
  "schema": "paper-revision-issues.v2",
  "issues": [
    {
      "id": "REV-THEORY-01",
      "problem": "The maintained null and theorem scope are inconsistent.",
      "severity": "P0",
      "area": "theory",
      "source": {"kind": "workflow-audit", "locator": "audit/theory.md#scope"},
      "affected_objects": ["null", "theorem:main", "abstract", "conclusion"],
      "depends_on": [],
      "acceptance_criteria": [
        "The statement and proof use the same maintained null.",
        "A fresh independent reviewer accepts the repaired object and scope."
      ],
      "objective_link": "The maintained null and theorem are load-bearing parts of the frozen paper objective.",
      "consequence_if_unresolved": "The headline guarantee would refer to a different null from the proof.",
      "admission_basis": "material-research-effect",
      "author_gate": false,
      "reopen_if": ["The maintained null, theorem statement or proof input changes."],
      "root_cause": "skill-gap"
    }
  ]
}
```

`admission_basis` is one of `direct-user`, `dependency`,
`release-requirement`, or `material-research-effect`. It records why the issue
entered this cycle; it does not prove materiality. If `objective_link` and
`consequence_if_unresolved` cannot be stated concretely, keep the finding in the
ordinary backlog. Generic claims such as “improve clarity” or “optimize further”
do not admit an issue to the active queue.

Write each issue's acceptance criteria so they identify the affected frozen
objective, invariant, trade-off, or paired comparison when applicable. The
issue schema remains unchanged: keep those links in concrete criterion text
rather than creating another issue authority.

Valid severities are `P0` scientific invalidity or evidence conflict, `P1`
major claim/evidence/contribution gap, `P2` reproducibility or cross-artifact
gap, and `P3` exposition or formatting. Valid areas are
`research-positioning`, `theory`, `method`, `simulation`, `empirical`,
`notation`, `writing`, and `integration`. `root_cause` is one of `skill-gap`,
`execution-miss`, `tool-failure`, `input-insufficient`, or
`scientific-unknown`; leave it `null` until evidence supports classification.

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" add \
  --project "$PROJECT" --issues "$PROJECT/revision-issues.json"
python3 -B "$WORKFLOW/scripts/revision_cycle.py" add \
  --project "$PROJECT" --issues "$PROJECT/revision-issues.json" --write
```

Dependency order outranks severity. Among dependency-ready issues, the
controller orders P0 through P3 and preserves source order within a severity.
There can be only one `active`, `verifying`, or `blocked_author` issue. Necessary
dependent edits belong to the active issue; independent findings remain queued.

## Execute one issue and verify it

Select the next dependency-ready issue:

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" select --project "$PROJECT" --write
```

Route the issue to the owning specialist. Preserve the issue ID, manuscript
hash, allowed dependent edits and acceptance criteria in the handoff. After the
actual files change, record an implementation event:

```json
{
  "schema": "paper-revision-event.v1",
  "action": "implemented",
  "issue_id": "REV-THEORY-01",
  "worker_id": "theory-worker-01",
  "locators": ["sections/theory.tex", "appendix/proofs.tex"]
}
```

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" transition \
  --project "$PROJECT" --event "$PROJECT/revision-event.json" --write
```

This binds the new manuscript hash, increments the actual attempt count, moves
the issue to `verifying`, and clears prior full-candidate reviews. It does not
assert that the listed edit is correct.

An issue review is a project artifact:

```json
{
  "schema": "paper-revision-review.v1",
  "review_id": "REV-THEORY-01-R1",
  "review_scope": "issue",
  "issue_id": "REV-THEORY-01",
  "reviewer_id": "independent-reviewer-01",
  "reviewer_context_id": "fresh-context-2026-09-16-a",
  "candidate_sha256": "<current manuscript SHA-256>",
  "severity": "none",
  "locator": "reviews/REV-THEORY-01-R1.md",
  "evidence": ["reviews/REV-THEORY-01-R1.md", "proof/release-status.json"],
  "verdict": "accepted",
  "next_action": ""
}
```

The reviewer must differ from the candidate worker. `rework` or `rejected`
requires a concrete next action and returns the same issue to `active`; the
controller does not skip ahead. `accepted` closes the issue and makes its
dependency-ready successors selectable.

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" review \
  --project "$PROJECT" --review "reviews/REV-THEORY-01-R1.json" --write
```

If an accepted prerequisite later changes, use a `reopen` event. The controller
reopens that issue and its accepted/deferred descendants, while leaving unrelated
issues intact. Any material candidate edit resets the two-review convergence
count. If `.paper/revisions.yaml` was edited by an authorized external writer,
run `sync` and inspect the preview before writing; synchronization always clears
cached clean reviews.

## Pause only at the frozen author gates

Use a `pause` event only for the contract's pause conditions. A pause identifies
one issue when possible and produces one consolidated author question. A
`repeated-blocker` pause requires three recorded substantive implementation
attempts. Resume only with a locator to the resolving author decision.

P0 and P1 issues cannot be deferred. P2 or P3 may be deferred only with an
explicit reason and `nonblocking: true`; this is an attested decision, not proof
that the issue is harmless. External submission or communication is never a
transition in this controller.

## Trigger one bounded expert escalation

The controller permits `escalate` only when all are true:

- the issue is P0 or P1;
- one substantive implementation attempt exists;
- its fresh issue review returned `rework` or `rejected`;
- a named panel was frozen in the project contract;
- this issue has not used an escalation before.

The event points to a project-local evidence packet. After the gate passes, the
agent must explicitly invoke the already authorized supervisor/mentor/roundtable
interfaces according to their current instructions. Run exactly one bounded
round for the concrete dispute. Preserve dissent and request a discriminating
proof or experiment when evidence cannot decide; votes do not establish truth.

## Converge on one frozen candidate

After all issues are accepted or validly deferred, bind the final candidate with
a `candidate` event. Then create the current
`paper-non-regression-report.v1` at the contract's `report_path`. It must cover
every frozen ID and whole-candidate dimension exactly once, bind the current
manuscript and contract hashes, and use current `{path, sha256}` evidence
snapshots. `retain` passes only when objectives are `improved`, invariants are
`preserved`, trade-offs are `within-bound`, paired comparisons are `pass`, and
whole-candidate dimensions are `pass`. `unknown`, stale evidence, missing IDs,
`rework`, or `rollback` prevents convergence.

Only after that report passes, obtain two full reviews with:

- `review_scope: full`, `issue_id: null`, `severity: none`, and `verdict: accepted`;
- the exact same current manuscript SHA-256;
- two different reviewer IDs and two different fresh-context IDs;
- reviewers distinct from candidate workers;
- review artifacts whose hashes remain current;
- the non-regression report listed in each review's `evidence` and the same
  current report hash bound into both review records.

An adverse full review must link a newly recorded or reopened issue. It clears
the clean-review count and returns the issue and declared dependents to the queue.

`status` reports `manuscript-ready-for-author-review` only when the issue ledger
is current, every cycle issue is accepted/deferred, no P0/P1 remains, manuscript
hashes match, the non-regression report passes, two full reviews remain fresh
for both that manuscript and report, and workflow stages `manuscript`,
`verification`, `review`, `revision`, and `delivery` are ready for the same
candidate. A manuscript edit invalidates the report; a report edit invalidates
the clean reviews. The controller validates structure, coverage and hashes but
cannot certify mathematics, evidence quality or true reviewer independence.

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" status --project "$PROJECT"
```

## Feed only reusable findings to Skill maintenance

At cycle end, run:

```bash
python3 -B "$WORKFLOW/scripts/revision_cycle.py" retrospective --project "$PROJECT"
```

The result contains only issue IDs, areas and cause classes; it omits problem
text and never promotes a single project's finding into a global rule. A global
candidate requires recurrence in at least two projects, or one reproducible
severe failure plus an independent holdout. Send that bounded candidate through
the environment's skill-maintenance process with frozen baseline/candidate
artifacts and rubrics. Do not let this paper cycle edit global skills automatically.
