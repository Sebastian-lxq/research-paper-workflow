# Synthetic case study: from a broad methods question to a bounded next action

This case study shows what Research Paper Workflow does before a paper has a
verified literature claim, theorem, dataset, or numerical result. It uses the
public [`minimal-paper`](../examples/minimal-paper/README.md) example and makes
no claim that the proposed research direction is novel or feasible.

## Starting brief

The synthetic researcher asks whether a specification test can remain useful
when a nuisance function is estimated by a flexible learner. The starting
folder contains a short project brief, but no authoritative literature map,
proof, simulation output, empirical result, or manuscript claim.

The workflow receives one explicit instruction:

```text
Use $research-paper-workflow to inspect project-brief.md. Create the smallest
project-local workflow state needed to compare candidate mechanisms, record
missing literature evidence, and identify the cheapest safe next action. Do not
claim novelty or create numerical results.
```

## What the workflow is allowed to do

At this point it may classify the project provisionally, expose missing
evidence, compare genuinely different mechanisms, specify a cheap falsifier,
and initialize resumable state. It may also continue preparation that remains
valid under plausible future findings.

It may not say that the idea is new, that an assumption is sufficient, that a
test controls size, or that a simulation performs well. Each of those claims
requires evidence from a specialist stage that does not yet exist.

## The first pass

The orchestration layer treats this as a methods-paper project and preserves
five separate questions:

| Stage | Inspectable question | Initial disposition |
| --- | --- | --- |
| Framing | What estimand or testing target is actually being protected? | Runnable |
| Literature | Which nearest-neighbor methods already address the same failure mode? | Pending retrieval and reading |
| Theory | What theorem interface and assumptions would a candidate mechanism require? | Blocked by framing and literature |
| Simulation | Which data-generating process could cheaply falsify the mechanism? | Design may proceed; production results deferred |
| Writing | Which sentences are supported now? | Scope and open questions only |

This separation matters. A candidate mechanism can be recorded without being
called novel; a simulation design can be drafted without inventing a number;
and independent setup can continue while result-dependent prose remains gated.

## Persisted handoff

When writing is authorized, the workflow creates compact, versioned state under
`.paper/workflow/`. The state records the paper type, stage gates, blocker,
next runnable action, and resume conditions. Specialist records remain the
authoritative sources for literature, proofs, simulations, empirical results,
and manuscript claims.

The deterministic controller smoke path demonstrates the structural part of
this handoff:

```bash
python3 scripts/smoke_example.py
```

Its expected output is:

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

The check establishes that initialization and gating behaved as specified. It
does not establish novelty, theorem correctness, identification, numerical
performance, or publication readiness.

## The bounded deliverable

The useful first output is not a finished paper. It is a decision surface:

- the broad direction has been converted into explicit research dependencies;
- nearest-neighbor literature remains visibly unresolved;
- result-independent setup can continue;
- production simulation and result-dependent writing remain deferred;
- the next safe action is the earliest unmet evidence requirement, not the most
  impressive-looking paragraph.

That state can be resumed after literature, proof, or simulation evidence is
added. If new evidence defeats the candidate mechanism, the recorded falsifier
and reopen conditions make the change auditable instead of silently rewriting
the project's history.

## Try the same path

Follow the [one-minute quick start](QUICKSTART.md) for the synthetic example, or
use the [20-minute pilot](PILOT_PROGRAM.md) to test installation, one resume,
and one evidence-boundary failure report.
