# Contributing

Thank you for improving Research Paper Workflow. Contributions are welcome when
they preserve evidence boundaries and remain useful beyond one private project.

## Before opening a pull request

1. Create a focused branch and describe the user-visible problem.
2. Keep private manuscripts, corpora, credentials, personal paths, and project
   state outside the repository.
3. Add or update tests when behavior, schemas, or a release invariant changes.
   Update `plugins/research-paper-workflow/schemas.json` and
   `docs/STATE_SCHEMAS.md` whenever a public record format changes.
4. Run `python3 scripts/run_checks.py`.
5. Update `CHANGELOG.md` for user-visible changes.
6. Update `THIRD_PARTY.md` when a source, integration, copied implementation, or
   license obligation changes.

## Scientific and evidentiary changes

A pull request that changes a scientific workflow rule should state:

- the failure or capability gap being addressed;
- which claims or stages are affected;
- what must not regress;
- the fixture or real task used to evaluate it;
- what the evaluation does **not** establish.

A schema validator, prompt-string assertion, or same-author self-review is not
evidence of broad scientific improvement. Preserve failures and limitations.

## Code changes

- Support Python 3.9 or newer on the platforms declared in `README.md`.
- Prefer the standard library unless a dependency has a clear, maintained need.
- Keep writes atomic where a controller already promises atomicity.
- Preserve backward readability of public state schemas or include a tested
  migration.
- Never reuse an existing schema identifier for a different input or output
  shape. Input contracts and derived reports require distinct identifiers.
- Do not add network access to offline controllers without documenting the
  endpoint, data sent, permission boundary, and failure behavior.

## Third-party material

Conceptual influence, runtime interoperability, and copied code are different.
If code or prompt text is copied or modified, identify the exact source path and
revision, verify the license, preserve required notices, and explain why a new
dependency is justified. Do not copy material merely because it is public.

## Pull request review

Pull requests should be small enough to review against their stated objective.
Maintainers may ask for a synthetic reproducer when a report depends on private
research material. Security-sensitive reports should follow `SECURITY.md`
instead of a public issue.
