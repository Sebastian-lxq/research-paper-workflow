# Research Paper Workflow

[![CI](https://github.com/XuQingAcademic/research-paper-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/XuQingAcademic/research-paper-workflow/actions/workflows/ci.yml)
[![Tag](https://img.shields.io/github/v/tag/XuQingAcademic/research-paper-workflow?label=tag)](https://github.com/XuQingAcademic/research-paper-workflow/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-3da9fc.svg)](LICENSE)
[![skills.sh compatible](https://img.shields.io/badge/skills.sh-compatible-14b8a6.svg)](https://www.skills.sh/docs)

[简体中文](README.zh-CN.md) · [Changelog](CHANGELOG.md) ·
[Security](SECURITY.md) · [Privacy](PRIVACY.md) ·
[Compatibility](docs/COMPATIBILITY.md) ·
[Pilot program](docs/PILOT_PROGRAM.md) ·
[Synthetic case study](docs/SYNTHETIC_CASE_STUDY.md) ·
[State schemas](docs/STATE_SCHEMAS.md) ·
[CLI exit codes](docs/EXIT_CODES.md) ·
[Third-party provenance](THIRD_PARTY.md) ·
[Project site](https://xuqingacademic.github.io/research-paper-workflow/)

A general, evidence-grounded research-paper workflow with first-class support
for econometrics and quantitative economics.

Research Paper Workflow coordinates idea discovery, literature, research
design, proofs, empirical evidence, simulation, writing, independent review,
revision, and reproducible delivery while keeping every scientific claim
bounded by the evidence that actually exists. Its orchestration and state model
can support quantitative research across fields; its deepest documented routes,
interfaces, and examples currently target econometrics, statistics, and
quantitative economics.

> **Status: v0.1.1 Research Preview.** The bundled controllers have local
> regression coverage, but this release is not a guarantee of novelty,
> mathematical correctness, identification, publication, or exhaustive
> literature coverage. See [claim boundaries](docs/CLAIMS.md).

## Who it is for—and what five minutes gives you

| You are working on… | The workflow helps you… |
| --- | --- |
| Econometric theory or statistical methods | Keep idea, literature, proof, simulation, and writing dependencies explicit |
| A quantitative paper with incomplete evidence | Identify the first unmet requirement and continue only independent safe work |
| A long-running or multi-session research project | Persist compact state, job handles, blockers, and resume conditions |
| Research-agent infrastructure | Reuse a portable orchestration layer while supplying your own domain validators |

Within the first five minutes, a conforming run should produce a provisional
project classification, visible evidence gaps, the next bounded action, and—if
authorized—a resumable `.paper/workflow/` state. It should **not** manufacture a
literature finding, theorem, numerical result, or novelty claim.

## Install and start

Add the GitHub marketplace and install the plugin:

```bash
codex plugin marketplace add XuQingAcademic/research-paper-workflow
codex plugin add research-paper-workflow@research-paper-workflows
```

Start a new Codex thread in a quantitative-research project and paste:

```text
Use $research-paper-workflow to inspect the current project, identify the next
unmet evidence requirement, and continue every branch that is safe to advance.
```

Optional verification:

```bash
codex plugin list
```

The output should include
`research-paper-workflow@research-paper-workflows` as installed and enabled.

For agents that use the open `SKILL.md` ecosystem, a skill-only installation is
also available through [skills.sh](https://skills.sh/):

```bash
npx skills add XuQingAcademic/research-paper-workflow --skill research-paper-workflow
```

This route installs the workflow skill and its referenced files; the Codex
plugin command above additionally installs the repository's plugin metadata.

## What the workflow actually does

The workflow is an orchestration and evidence-control layer. It does not replace
the specialist that searches literature, proves a theorem, audits a simulation,
or estimates a model. It decides what evidence is required, which work can move
now, which work must wait, and what must be preserved so the project can resume
without silently changing its scientific claims.

| Capability | What it does | Inspectable output |
| --- | --- | --- |
| Project intake | Reads the current manuscript, code, state, instructions, and available results; provisionally classifies the paper as theory, methods, empirical, or hybrid | Current objective, paper type, available artifacts, and first unmet requirement |
| Idea discovery | Builds materially different candidate mechanisms, attaches nearest-neighbor search needs, cheap falsifiers, decision criteria, and reopen conditions | Candidate portfolio rather than a single prematurely selected idea |
| Literature governance | Separates retrieved, screened, and deeply read sources; prevents unverified abstracts or search snippets from supporting novelty language | Search frontier, coverage gaps, source status, and bounded novelty wording |
| Research design | Freezes the estimand, target population, identification logic, assumptions, comparison set, and the evidence needed for each intended claim | Design contract and explicit dependencies between claims and evidence |
| Theory and proof handoff | Routes theorem work to an installed specialist and exchanges hash-bound lineage summaries without copying a second proof truth store | Theorem interfaces, dependency graph, proof status, and unresolved obligations |
| Empirical evidence | Keeps data provenance, estimation contract, diagnostics, robustness checks, and claim permissions distinct | Result contract showing what an empirical artifact may and may not support |
| Simulation control | Distinguishes smoke, pilot, and production runs; records real offline-job handles and solver failures; blocks result-dependent prose while a run is incomplete | Registered job, wait state, resume condition, failure lineage, and result scope |
| Writing and citation control | Allows structure and source-bounded prose to continue while withholding sentences that depend on missing literature, proofs, or results | Manuscript permissions, unresolved citation needs, and claim-level blockers |
| Independent review | Checks scientific dependencies, evidence ceilings, reproducibility, and release claims separately from schema validity | Review findings and a bounded release decision rather than a generic pass |
| Continuous revision | Defines what must improve, what cannot regress, acceptable trade-offs, paired before/after evidence, rollback conditions, and a final whole-paper review | Non-regression contract and auditable revision decision |
| Resumable state | Persists versioned stage status, next safe action, blocker, job handle, and reopen condition under `.paper/workflow/` | Compact state that can be resumed across sessions without recreating finished work |
| Reproducible delivery | Separates structural checks from scientific readiness and packages verified public artifacts with deterministic hashes and provenance | Release status, checksum, manifest, and explicit remaining limitations |

### Execution model

1. Inspect existing evidence before proposing work.
2. Freeze the immediate objective and the evidence each claim requires.
3. Route only to specialist capabilities that are actually installed.
4. Continue branches that remain valid under plausible future results.
5. Keep dependent work pending when literature, proof, data, or simulation is missing.
6. Persist the next action, blocker, and resume condition instead of treating a
   partial run as completion.

Try the synthetic, privacy-safe example in
[`examples/minimal-paper`](examples/minimal-paper/README.md), or run its
deterministic controller smoke path:

```bash
python3 scripts/smoke_example.py
```

The smoke path initializes a methods-paper workflow, records simulation as
deferred, identifies `framing` as the next runnable stage, and makes no
scientific-result claim. See the full [quick-start walkthrough](docs/QUICKSTART.md).
For the complete input-to-handoff narrative, read the
[synthetic case study](docs/SYNTHETIC_CASE_STUDY.md).

## Why this project exists

Research agents often fail between specialist tasks: an idea loses its nearest
neighbor evidence, a proof gap does not propagate to the manuscript, a pilot is
reported as a production result, or a long simulation is polled repeatedly while
result-dependent prose keeps moving. This workflow makes those handoffs explicit.

### Scope and specialization

The workflow core is deliberately domain-extensible: projects can reuse its
evidence gates, resumable state, offline-job handling, and non-regression review
without being economics papers. Econometrics is the current reference domain,
not an exclusivity boundary. The included proof-lineage interface and the
first-party companion routes are designed most specifically for econometric
theory, statistical methods, and quantitative economics; other fields need
their own specialist providers for domain-level validation.

Core mechanisms include:

- candidate portfolios, falsifiers, search frontiers, and reopen conditions;
- hash-bound stage receipts without creating a second scientific truth store;
- proof, empirical, simulation, and writing capability handoffs;
- a layered proof-genealogy framework and hash-bound active-lineage adapter without bundled proof content;
- paired non-regression evidence for material revisions;
- append-only operational telemetry and resumable state;
- handle-bound waits for offline jobs while independent work continues;
- release checks that distinguish structural success from scientific validity.

## Package layout

```text
.
├── .agents/plugins/marketplace.json       # repo-local marketplace
├── plugins/research-paper-workflow/       # installable portable plugin
│   ├── plugin.json                        # portable Agent Plugins manifest
│   ├── .codex-plugin/plugin.json          # Codex compatibility metadata
│   ├── controllers.json                   # CLI/library and exit-code inventory
│   ├── schemas.json                       # state-format lifecycle inventory
│   ├── dependencies/skills.json           # companion capability inventory
│   └── skills/research-paper-workflow/    # skill, references, scripts, tests
├── examples/minimal-paper/                # synthetic public example
├── scripts/                               # repository validation
└── docs/                                  # architecture and release contracts
```

The layout follows the current OpenAI Agent Plugins structure: a plugin has a
root `plugin.json` and discovers skills under `skills/`; the compatibility
manifest remains for Codex clients that still use it.

## Alternative local installation

Requirements:

- Codex or ChatGPT desktop with local plugin support;
- Python 3.9 or newer;
- macOS or Linux for the v0.1.x controller scripts.

For local development, clone the repository, add that checkout as a marketplace,
then install the plugin:

```bash
git clone https://github.com/XuQingAcademic/research-paper-workflow.git
cd research-paper-workflow
codex plugin marketplace add "$PWD"
codex plugin add research-paper-workflow@research-paper-workflows
```

Restart the desktop app or start a new Codex session after installation. The
repo marketplace is defined in `.agents/plugins/marketplace.json`.

For development without installation, point Codex at
`plugins/research-paper-workflow` as a plugin capability directory.

## Additional usage paths

Open a quantitative-research project and ask:

```text
Use $research-paper-workflow to inspect the current project, identify the next
unmet evidence requirement, and continue every branch that is safe to advance.
```

For a synthetic project with no private data, start from
[`examples/minimal-paper`](examples/minimal-paper/README.md).
The runnable [`offline-wait example`](examples/offline-wait/README.md) shows why
result-dependent work pauses on a registered handle while unrelated work may
continue.

Early users can follow the public [20-minute pilot](docs/PILOT_PROGRAM.md) and
report the first installation, routing, state, or evidence-boundary problem
through the dedicated issue form or GitHub Discussions.

The workflow discovers companion skills at runtime. Missing providers do not
silently become successful stages: the workflow continues only unaffected work,
reports the missing capability, and narrows its claims. See
[dependency resolution](docs/DEPENDENCIES.md).

Inspect companion availability without changing the environment:

```bash
python3 plugins/research-paper-workflow/scripts/check_companions.py
```

The report deliberately labels scientific validation as “not assessed.” See
[Bundled controllers](docs/CONTROLLERS.md) for the public CLI and library
entrypoints and their evidence ceilings. Machine record names, compatibility,
and migration rules are indexed in [State schemas](docs/STATE_SCHEMAS.md).

## Development and verification

Run the complete local check:

```bash
python3 scripts/run_checks.py
```

This validates public-release hygiene and manifests, checks internal Markdown
links, compiles Python sources, runs the bundled workflow and repository tests,
and exercises the synthetic quick start in an isolated temporary project.

Build the standalone plugin archive with:

```bash
python3 scripts/package_plugin.py
```

The archive is deterministic for a fixed source tree and is written under
`dist/`, which is excluded from version control. Packaging also writes a
sidecar `.sha256` checksum for release verification. The archive itself contains
`MANIFEST.sha256`, which binds every packaged file except the manifest itself.
The build self-verifies. A downloaded candidate can be checked portably with:

```bash
python3 scripts/verify_release.py dist/research-paper-workflow-0.1.1.zip
```

GitHub Actions runs the same check on Linux and macOS across supported Python
versions. Windows is not claimed in v0.1.1 because several controllers use
POSIX file locks; contributions that add an equivalent tested lock backend are
welcome.

Current local evidence covers Python 3.9.6 and 3.12.14 on macOS. Configured but
unrun CI combinations remain pending in the [compatibility matrix](docs/COMPATIBILITY.md).

## Privacy and public/private separation

This repository intentionally excludes:

- unpublished manuscript excerpts and private evaluation cases;
- private mentor corpora, profiles, memory, or communications;
- project-local `.paper/` and supervision state;
- API keys, credentials, personal absolute paths, and raw research data.

Public examples must be synthetic, openly licensed, or contributor-owned and
explicitly cleared for redistribution. See [Security](SECURITY.md) and
[Contributing](CONTRIBUTING.md).

## Third-party skills

Yes—skills and public projects that materially support or influence the workflow
should be named. This repository records runtime integrations, pinned inspected
revisions, licenses, design influences, and whether code is bundled in
[THIRD_PARTY.md](THIRD_PARTY.md). The short rule is:

- interoperability: name the provider and version;
- design influence: cite the source and the adopted mechanism;
- copied or modified implementation: also preserve all required license notices.

No third-party skill implementation is bundled in v0.1.1.
CI-only GitHub Actions are also attributed separately in
`.github/actions-dependencies.json`; they are development infrastructure, not
runtime research capabilities.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Behavioral changes should include tests
for the changed invariant, and scientific claims must state the exact evidence
scope. Please report vulnerabilities privately as described in
[SECURITY.md](SECURITY.md).

## Citation and license

This is a software project and does not require a companion paper. Software
citation metadata is in [CITATION.cff](CITATION.cff); the maintainer's public
contact email is included, while ORCID remains optional and omitted. References,
runtime integrations, and GitHub projects used or consulted are attributed in
[THIRD_PARTY.md](THIRD_PARTY.md). The project is released under the
[MIT License](LICENSE). See [Privacy](PRIVACY.md) and [Terms](TERMS.md).
Third-party projects retain their own licenses.
