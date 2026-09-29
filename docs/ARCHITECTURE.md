# Architecture

## Authority boundaries

The workflow coordinates existing scientific records instead of replacing them:

```text
author/project decisions
          |
          v
workflow plan and stage receipts
    |          |          |
    v          v          v
literature   proofs   empirical/simulation
    \          |          /
     \         v         /
      manuscript and release audit
```

- Manuscript claims, citations, and author locks remain in the paper project.
- Proof ledgers own mathematical obligations and verification status.
- A proof-lineage manifest may expose a minimal read-only graph of versioned
  objects and hash-bound locators; it never becomes the proof authority.
- Simulation manifests own cells, RNG lineage, precision, and failures.
- Empirical records own data identity, estimators, inference, and diagnostics.
- Workflow state stores only plans, dependencies, receipts, blockers, and
  pointers to those authorities.

## Bundled controllers

The plugin ships deterministic scripts for:

- workflow stage state and release handoffs;
- content and artifact bindings;
- revision queues and non-regression contracts;
- resumable feedback views;
- idea portfolios and bounded exploration probes;
- empirical result contracts;
- proof-lineage interoperability and freshness checks;
- append-only operation logs and offline wait barriers;
- paired token/quality evaluation.

All state mutations preview by default where the underlying controller supports
that mode. Structural success never certifies scientific truth. Public record
identifiers, lifecycle states, and migration rules are indexed in
[State schemas and compatibility](STATE_SCHEMAS.md); executable validators in
the owning controllers remain the structural specification.

## Public/private boundary

The public repository contains only reusable instructions, controllers, tests,
and synthetic examples. Unpublished evaluation cases, private mentor adapters,
communications, and project state live outside the repository. Optional private
integrations may implement the same public capability interfaces without being
named or bundled here.
