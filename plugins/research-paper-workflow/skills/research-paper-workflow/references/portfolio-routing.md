# Capability routing

This public workflow routes by research object and required evidence, not by a
maintainer-specific inventory. Re-discover available skills and tools at runtime.
For missing or alternative providers, use
[dependency-resolution.md](dependency-resolution.md).

## Core capability map

| Research object | Preferred known provider | Required evidence boundary |
| --- | --- | --- |
| Candidate ideas and substantive overlap | `mine-econometrics-ideas` | Candidate mechanism, nearest neighbors, falsifiers, actual probes, and reopen conditions; no novelty certificate |
| Scholarly discovery | `paper-lookup` | Query and retrieval provenance; discovery is not source verification |
| Citation metadata | `citation-management` | DOI/identifier and bibliographic verification for identified records |
| Source reconstruction | `deepread` | Claims, evidence, assumptions, and locators from supplied sources |
| Econometric theory | `prove-econometrics-theory-v2` | Claim-scoped assumptions, proof obligations, adversarial checks, release ceilings, and an optional hash-bound proof-lineage projection |
| Numerical simulation | `audit-numerical-simulations-v2` | DGP/cell binding, RNG and failure lineage, precision, resume, and manuscript ceilings |
| Manuscript | `write-econometrics-paper-v3` | Sentence-level evidence ceilings, source versions, result provenance, and release audit |
| Optional prose cleanup | `humanizer` | Style-only pass after scientific claims stabilize; protected math, numbers, citations, and terminology |

The provider names are interoperability points, not bundled dependencies. The
machine-readable inventory in the plugin package records source revisions and
licenses for third-party integrations.

## Independent review

Use an independent review provider only when requested or required by the
project contract. Known optional providers include `review-paper`,
`review-paper-code`, and `audit-analysis`. They remain explicit integrations and
are not installed by this plugin.

Several reviewer roles in one context do not establish independence. Give a
reviewer the exact claim, artifacts, evidence, and frozen criteria—not the
desired verdict.

## Optional private providers

A project may connect an explicitly authorized expert-supervision or private
corpus provider. This public workflow neither names nor bundles private expert
instances. The provider's own access, egress, consent, evidence, and audit rules
remain authoritative.

## Environment probes

Check the actual project runtime before promising execution. Python, R, LaTeX,
data access, network endpoints, and statistical packages are project-dependent.
Unknown availability remains unknown until probed. Artifact-generation runtimes
and scientific-computation runtimes may differ.
