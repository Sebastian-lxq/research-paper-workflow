# Quick-start walkthrough

This walkthrough gives a new user one bounded success path in about one minute.
It uses only the synthetic project in this repository and does not claim a new
scientific result.

## 1. Install

```bash
codex plugin marketplace add XuQingAcademic/research-paper-workflow
codex plugin add research-paper-workflow@research-paper-workflows
```

Start a new Codex thread after installation.

## 2. Open the example

Clone the repository if you do not already have a quantitative-research project:

```bash
git clone https://github.com/XuQingAcademic/research-paper-workflow.git
cd research-paper-workflow/examples/minimal-paper
```

The example asks whether a specification test can remain useful when a nuisance
function is estimated by a flexible learner. It contains no unpublished paper,
private source, participant data, or claimed result.

## 3. Run the workflow

Paste this prompt in a new Codex thread whose project is `minimal-paper`:

```text
Use $research-paper-workflow to inspect project-brief.md. Create the smallest
project-local workflow state needed to compare candidate mechanisms, record
missing literature evidence, and identify the cheapest safe next action. Do not
claim novelty or create numerical results.
```

The exact prose and candidate ideas may differ. A conforming run should:

- keep novelty pending until identified sources are read;
- compare materially different candidate mechanisms, not title variants;
- attach a cheap falsifier and a reopen condition to retained or parked routes;
- continue setup that remains valid under plausible future results;
- report missing companion capabilities without pretending they ran.

## 4. Inspect the result

The run should make its current state, next safe action, pending evidence, and
blocked result-dependent work inspectable. The orchestration layer stores only
workflow state and hash-bound handoffs under `.paper/workflow/`; specialist
records remain authoritative for literature, proofs, simulations, empirical
results, and manuscript claims.

For a deterministic offline check of the controller path, return to the
repository root and run:

```bash
python3 scripts/smoke_example.py
```

Expected output shape:

```json
{
  "example": "minimal-paper",
  "initialized": true,
  "status_schema": "paper-workflow-status.v1",
  "paper_type": "methods",
  "simulation": "deferred",
  "scientific_result_claimed": false
}
```

This smoke path verifies initialization, state schema, the initial `framing`
gate, and the absence of a fabricated scientific result. It does not substitute
for a complete agent run or validate a scientific claim.

## Where to go next

- Read [the architecture](ARCHITECTURE.md) for component boundaries.
- Read [dependency resolution](DEPENDENCIES.md) when companion skills are
  missing.
- Run the [offline-wait example](../examples/offline-wait/README.md) to see how
  long simulations suspend dependent work without blocking independent work.
- Use [support](../SUPPORT.md) for installation help and the repository's issue
  templates for reproducible bug reports or feature requests.
