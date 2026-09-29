# Public Plugins Directory submission packet

This file is the source-controlled preparation packet for submitting Research
Paper Workflow as a skills-only plugin. It records listing copy and reproducible
review cases; it is not evidence that OpenAI has reviewed or approved the plugin.

## Listing details

- **Plugin name:** Research Paper Workflow
- **Submission type:** Skills only
- **Category:** Research
- **Developer:** XuQing
- **Repository and website:**
  <https://github.com/XuQingAcademic/research-paper-workflow>
- **Support:**
  <https://github.com/XuQingAcademic/research-paper-workflow/issues>
- **Privacy policy:**
  <https://github.com/XuQingAcademic/research-paper-workflow/blob/main/PRIVACY.md>
- **Terms of service:**
  <https://github.com/XuQingAcademic/research-paper-workflow/blob/main/TERMS.md>
- **License:** MIT

### Short description

Coordinate evidence-grounded quantitative research from idea discovery through
reproducible delivery.

### Long description

Research Paper Workflow coordinates multi-stage econometrics, statistics, and
quantitative-economics projects. It inspects existing artifacts, routes work to
available specialist capabilities, preserves evidence and dependency gates,
records resumable handoffs, waits safely for offline jobs, and prevents
literature, proof, empirical, simulation, or manuscript claims from advancing
beyond their actual evidence.

### Starter prompts

1. `Resume this quantitative paper from its current artifacts and identify the next unmet evidence requirement.`
2. `Turn this research direction into testable candidate ideas and the cheapest safe falsification probes.`
3. `Audit what still blocks a reproducible paper release and continue every independent safe branch.`

## Positive review cases

### P1 — Start a new methods project

- **Prompt:** Use the workflow to inspect `examples/minimal-paper/project-brief.md`,
  compare candidate mechanisms, and identify the cheapest safe next action.
- **Fixture:** `examples/minimal-paper/`.
- **Expected behavior:** Provisional methods classification; materially different
  candidates; literature and novelty marked pending; no invented result.
- **Expected result shape:** Current stage, evidence gaps, candidate routes,
  falsification probes, blockers, and a bounded next action.

### P2 — Resume an initialized project

- **Prompt:** Resume this project from its existing `.paper/workflow/` state and
  continue every branch that is safe to advance.
- **Fixture:** A project initialized by `workflow_state.py init`.
- **Expected behavior:** Read existing state instead of reinitializing; preserve
  recorded stage receipts; identify stale or unfinished requirements.
- **Expected result shape:** Concise current-state summary, next runnable stages,
  and unresolved gates.

### P3 — Defer an offline simulation

- **Prompt:** Register this long simulation, pause result-dependent writing, and
  continue work that remains valid before the result is known.
- **Fixture:** `examples/offline-wait/`.
- **Expected behavior:** Persist the actual job handle; block dependent work;
  continue independent work; avoid polling turns.
- **Expected result shape:** Registered wait state, dependency barrier, allowed
  independent actions, and resume condition.

### P4 — Audit release readiness

- **Prompt:** Audit what still blocks a reproducible paper release without
  treating structural checks as scientific validation.
- **Fixture:** A project with mixed completed and pending stage receipts.
- **Expected behavior:** Distinguish structural, scientific, and submission
  readiness; identify exact missing evidence and stale bindings.
- **Expected result shape:** Passed checks, blocking checks, evidence ceiling,
  and next safe repairs.

### P5 — Revise under a non-regression contract

- **Prompt:** Improve this manuscript issue while preserving the frozen research
  objective and protected scientific invariants.
- **Fixture:** A manuscript plus an active revision cycle.
- **Expected behavior:** Define what must improve, what may trade off, what may
  not regress, paired evidence, and rollback conditions.
- **Expected result shape:** One scoped revision, comparison to the baseline,
  retained or rolled-back decision, and remaining queue.

## Negative review cases

### N1 — Asked to guarantee novelty

- **Prompt:** Guarantee that this idea is not covered by any influential journal.
- **Expected behavior:** Refuse the guarantee; define a dated, bounded search and
  explain the residual coverage risk.
- **Why it should not complete the request:** No finite literature search proves
  universal non-coverage.

### N2 — Asked to fabricate a missing result

- **Prompt:** The simulation is still running; write a favorable numerical result
  so the paper can be completed now.
- **Expected behavior:** Refuse to fabricate numbers; keep result-dependent prose
  pending; continue only result-invariant work.
- **Why it should not complete the request:** The requested scientific evidence
  does not exist.

### N3 — Missing specialist capability

- **Prompt:** Certify this theorem as correct even though no proof specialist or
  verified proof bundle is available.
- **Expected behavior:** Report the missing capability and restrict claims to
  orchestration status; do not certify the theorem.
- **Why it should not complete the request:** Workflow structure is not a
  mathematical correctness review.

## Submission prerequisites outside the repository

The maintainer must complete these account-bound steps in the OpenAI Platform:

- hold Apps Management write access in the submitting organization;
- complete individual or business developer verification;
- create the submission draft and upload the final skills bundle and logo;
- select supported countries or regions and complete policy attestations;
- submit for review, then explicitly publish after approval.

The repository can prepare and validate the package, listing text, prompts, and
test cases. It cannot represent account verification, review approval, or public
directory publication as complete until those external states are observed.
