# Publication readiness

## Locally complete for v0.1.1

- [x] Portable Agent Plugin manifest and Codex compatibility manifest.
- [x] Repo-local marketplace with a stable plugin identifier.
- [x] English and Chinese usage documentation.
- [x] MIT license, citation metadata, support, conduct, contribution, privacy,
      terms, and security policies.
- [x] Software citation uses the maintainer's public GitHub identity and public
      contact email; ORCID remains optional and omitted, and no companion paper
      is required.
- [x] Two-command Git-backed installation and bilingual 60-second walkthrough.
- [x] A 60-second animated synthetic demo and a standalone GitHub Pages site.
- [x] An isolated `skills.sh` CLI discovery and installation check for the
      packaged `SKILL.md` tree.
- [x] A public pilot guide, dedicated feedback form, and reusable bilingual
      launch materials.
- [x] Public Plugins Directory listing copy, starter prompts, and five positive
      plus three negative review cases prepared in a source-controlled packet.
- [x] Human-readable and machine-readable third-party provenance.
- [x] Machine-readable controller and state-schema inventories with release-time
      completeness checks and an explicit preview migration policy.
- [x] Public proof-lineage framework and hash-bound interoperability controller,
      without bundled theorem content or project proof ledgers.
- [x] Machine-readable CLI exit-code declarations and command-specific public guidance.
- [x] Public/private separation and synthetic example.
- [x] Public-release validator, companion discovery, and deterministic ZIP build.
- [x] External archive checksum plus an internal per-file hash manifest.
- [x] Isolated offline smoke tests for quick-start initialization and handle-bound waits.
- [x] Linux/macOS CI matrix, CodeQL workflow, packaging workflow, and Dependabot.
- [x] Public-repository provenance-attestation workflow and attributed CI Action inventory.
- [x] Bundled workflow controller tests pass locally.
- [x] Plugin and skill scaffolds pass the bundled validators.
- [x] The complete local check passes on macOS with Python 3.9.6 and 3.12.14.

## Requires repository-owner input or an external action

- [x] Choose the GitHub owner/repository name and add the remote URL.
- [x] Configure the initial Git commit identity. A public display name and the
      repository owner's GitHub `noreply` address are sufficient; this is separate
      from `CITATION.cff` and does not require publishing a personal email.
- [x] Replace generic publisher metadata with the selected public publisher.
- [x] Add public HTTPS URLs for website, privacy policy, and terms to the OpenAI
      interface metadata after the repository exists.
- [x] Create the initial commit, push the repository, and enable required CI,
      secret scanning, push protection, and private vulnerability reporting.
- [x] Run the GitHub Actions matrix and inspect its actual results.
- [x] Verify the first tag artifact's GitHub provenance attestation.
- [x] Publish a formal v0.1.1 GitHub Release with ZIP, external checksum,
      release notes, and verified provenance.
- [x] Deploy the public GitHub Pages site and enable repository Discussions.
- [x] Open the public pilot recruitment in
      [Discussion #2](https://github.com/XuQingAcademic/research-paper-workflow/discussions/2).
- [x] Submit the skill to `awesome_codex_skills` in
      [Issue #12](https://github.com/flaqai/awesome_codex_skills/issues/12).
- [ ] Confirm `skills.sh` has completed asynchronous public indexing after the
      verified CLI installation event; do not display its install-count badge
      while the badge reports `resource not found`.
- [ ] Wait for the third-party `awesome_codex_skills` curator's decision.
- [x] Install from the Git-backed marketplace with no prior copy of this
      marketplace or plugin in the Codex profile.
- [ ] Complete OpenAI developer verification, create the external submission,
      submit it for review, and publish after approval. Repository-side materials
      are prepared in [the submission packet](PLUGIN_DIRECTORY_SUBMISSION.md).

## Scientific maturity gates beyond an alpha release

- [ ] Clean second-host execution.
- [ ] Fully public end-to-end paper example.
- [ ] Independent external evaluator against a frozen rubric.
- [ ] Second-paper holdout distinct from the calibration project.
- [ ] Paired real-paper token/quality evaluation before efficiency claims.

The last group limits scientific and portability claims; it does not prevent a
carefully labeled Research Preview release.

`CITATION.cff` describes how to cite this software release. References, runtime
integrations, and GitHub projects that influenced the design are attributed in
`THIRD_PARTY.md`; they are not presented as authors of this repository.
