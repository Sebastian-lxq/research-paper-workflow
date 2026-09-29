# Synthetic minimal-paper example

This directory is a public, synthetic starting point for testing the workflow.
It is intentionally not a solved paper and contains no unpublished manuscript,
private corpus, real participant data, or claimed scientific result.

## Scenario

A researcher wants to study whether a specification test can remain useful when
a nuisance function is estimated by a flexible learner. The example asks the
workflow to turn that broad direction into bounded candidate ideas, identify
nearest-neighbor search needs, and freeze the cheapest falsification probe before
any theorem or simulation result is claimed.

## Try it

From this directory, ask:

```text
Use $research-paper-workflow to inspect project-brief.md. Create the smallest
project-local workflow state needed to compare candidate mechanisms, record
missing literature evidence, and identify the cheapest safe next action. Do not
claim novelty or create numerical results.
```

Expected behavior is described in `expected-behavior.md`. The exact prose and
candidate ideas need not match it; the evidence and permission boundaries must.

From the repository root, the deterministic local smoke path can be run without
network access or plugin installation:

```bash
python3 scripts/smoke_example.py
```

It copies this example into a temporary directory, initializes a methods-paper
workflow with simulation deferred, reads the generated status, checks the
versioned state files, and removes the temporary copy. It does not generate a
paper, literature result, theorem, or simulated number.
