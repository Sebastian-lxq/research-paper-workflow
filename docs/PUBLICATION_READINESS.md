# Publication readiness

## Locally complete for v0.1.0

- [x] Portable Agent Plugin manifest and Codex compatibility manifest.
- [x] Repo-local marketplace with a stable plugin identifier.
- [x] English and Chinese usage documentation.
- [x] MIT license, citation metadata, support, conduct, contribution, privacy,
      terms, and security policies.
- [x] Software citation uses the collective contributor name; personal email and
      ORCID are intentionally omitted because they are optional and no companion
      paper is required.
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

- [ ] Choose the GitHub owner/repository name and add the remote URL.
- [x] Configure the initial Git commit identity. A public display name and the
      repository owner's GitHub `noreply` address are sufficient; this is separate
      from `CITATION.cff` and does not require publishing a personal email.
- [x] Replace generic publisher metadata with the selected public publisher.
- [x] Add public HTTPS URLs for website, privacy policy, and terms to the OpenAI
      interface metadata after the repository exists.
- [ ] Create the initial commit, push the repository, and enable required CI,
      secret scanning, push protection, and private vulnerability reporting.
- [ ] Run the GitHub Actions matrix and inspect its actual results.
- [ ] Verify the first tag artifact's GitHub provenance attestation.
- [ ] Install from the Git-backed marketplace in a clean Codex environment.
- [ ] Submit to the universal Plugins Directory only when the maintainer wants
      public directory publication.

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
