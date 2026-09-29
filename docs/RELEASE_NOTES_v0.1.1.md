# Research Paper Workflow v0.1.1

> The animated promotional asset originally shipped with this tagged source was
> removed from the current main branch. The live project site and README now use
> detailed capability documentation instead.

This release turns the initial Research Preview into a complete public entry
point: a new user can understand the boundary of the project, install it from
GitHub, inspect a 60-second synthetic demonstration, reproduce the structural
quick start, and report pilot feedback without private research material.

## Highlights

- Added a 60-second animated demo and a reproducible local render script.
- Added a standalone GitHub Pages project site with installation, workflow,
  evidence-boundary, and pilot entry points.
- Verified the open `SKILL.md` install path with the `skills.sh` CLI while
  retaining the two-command Codex Plugin installation.
- Added a public 20-minute pilot, a dedicated feedback issue form, and launch
  copy for English and Chinese research communities.
- Added a full synthetic case study that distinguishes structural workflow
  success from scientific validation.
- Updated every public install path and package identifier to the
  `XuQingAcademic` GitHub account.
- Clarified that the orchestration layer is general while the deepest current
  specialist routes target econometrics, statistics, and quantitative
  economics.

## Install

```bash
codex plugin marketplace add XuQingAcademic/research-paper-workflow
codex plugin add research-paper-workflow@research-paper-workflows
```

For agents using the open `SKILL.md` ecosystem:

```bash
npx skills add XuQingAcademic/research-paper-workflow --skill research-paper-workflow
```

## Verification boundary

The release package is built deterministically, includes an internal
`MANIFEST.sha256`, ships with an external checksum, and is produced by the tag
workflow with GitHub artifact attestation. Local and CI checks exercise the
public manifests, links, Python sources, bundled controller tests, repository
tests, and synthetic smoke path.

Those checks do not prove research novelty, theorem correctness,
identification, numerical performance, exhaustive literature coverage, or
publication readiness. Research Paper Workflow keeps those claims pending
until the corresponding evidence exists.

## Start here

- Project site: https://xuqingacademic.github.io/research-paper-workflow/
- Repository: https://github.com/XuQingAcademic/research-paper-workflow
- Synthetic case study: https://github.com/XuQingAcademic/research-paper-workflow/blob/v0.1.1/docs/SYNTHETIC_CASE_STUDY.md
- Pilot: https://github.com/XuQingAcademic/research-paper-workflow/blob/v0.1.1/docs/PILOT_PROGRAM.md
