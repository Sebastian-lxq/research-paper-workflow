# Release process

## Local candidate checks

Run:

```bash
python3 scripts/run_checks.py
```

The command must finish with no failures. Review `git diff --check` and ensure
the working tree contains no private research material.

Build the distributable archive with:

```bash
python3 scripts/package_plugin.py
```

Packaging fails if its automatic archive self-verification fails. Verify an
existing or downloaded candidate without rebuilding it using:

```bash
python3 scripts/verify_release.py dist/research-paper-workflow-0.1.0.zip
```

The tag-triggered packaging workflow repeats the checks and uploads the ZIP plus
its SHA-256 sidecar as workflow artifacts. In a public repository it also uses
GitHub's OIDC-backed attestation action to publish build provenance for the ZIP.
Creating a GitHub Release remains an explicit maintainer action.

Verify both files from the directory containing them:

```bash
shasum -a 256 -c research-paper-workflow-0.1.0.zip.sha256
```

After extraction, verify every packaged file from the plugin root:

```bash
shasum -a 256 -c MANIFEST.sha256
```

The internal manifest intentionally excludes itself. Both checks establish byte
identity only; neither authenticates the publisher until the release also has a
trusted signature or provenance attestation.

After the public tag workflow succeeds, verify the GitHub attestation with the
GitHub CLI against the selected repository owner. The first real attestation
remains external evidence and must not be marked complete from workflow syntax
alone.

## Version contract

The following values must match:

- `plugins/research-paper-workflow/plugin.json` version;
- `.codex-plugin/plugin.json` version;
- `CITATION.cff` version;
- the newest `CHANGELOG.md` release heading.

Use semantic versions. Breaking state-schema changes require a new schema
identifier plus an explicit migration or coexistence rule. During the pre-1.0
preview, choose the semantic version according to the compatibility policy in
`docs/STATE_SCHEMAS.md`; never silently change the shape behind an existing
identifier. Do not increment versions only to force a local cache refresh.

## Evidence review

Before tagging a release:

1. identify every changed rule, controller, schema, and public claim;
2. verify `schemas.json` and the migration policy when a record format changes;
3. run the tests that cover those exact surfaces;
4. update claim boundaries and known limitations;
5. retain failed or superseded evaluation records outside the public package
   when they contain restricted material;
6. verify that public fixtures are synthetic or redistributable;
7. update third-party provenance when integrations or source-derived mechanisms
   change.

## GitHub release

Create a signed or annotated tag such as `v0.1.0`, generate release notes from
the changelog, and mark unstable builds as prereleases. Require the CI status
check on the default branch before release.

Publishing to the universal Plugins Directory is a separate external action and
requires its own submission and review. A GitHub release alone does not perform
that publication.
