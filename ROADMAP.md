# Roadmap

## v0.1.x — public preview hardening

- Run the full repository check on a clean second macOS or Linux host.
- Publish sanitized, fully synthetic behavioral fixtures.
- Add a documented compatibility matrix for Codex and ChatGPT plugin surfaces.
- Replace remaining dated local-portfolio history with provider-neutral guidance.
- Decide whether to support Windows locks or keep POSIX-only support explicit.

## v0.2 — companion distribution

- Publish or bundle first-party companion skills with stable version contracts.
- Add a capability resolver that reports installed providers and degradation
  before beginning a project.
- Add migration tests for every public project-state schema.
- Provide a complete public end-to-end example from question to release package.

## v0.3 — external validation

- Run an independent evaluator against a frozen rubric.
- Run a second-paper holdout distinct from the calibration project.
- Run a paired real-paper token/quality evaluation before making efficiency
  claims.
- Publish an evidence matrix containing only redistributable fixtures and results.

## v1.0 criteria

- clean installation and checks on at least two supported hosts;
- stable, documented state schemas with migrations;
- all bundled dependencies and licenses reproducibly resolved;
- required CI and review protections on the default branch;
- no private or unpublished material in repository history;
- at least one fully public, independently reviewable end-to-end case;
- project claims aligned with the evidence actually released.
