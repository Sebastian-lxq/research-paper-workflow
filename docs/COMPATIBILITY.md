# Compatibility matrix

Last local and hosted-CI verification: 2026-09-29.

| Surface | Version or environment | Evidence | Status |
| --- | --- | --- | --- |
| macOS Python | 3.9.6 | Public-release validation, syntax compilation, 208 workflow tests, 12 repository integration tests, schema/workflow/dependency mutation checks, release-tamper checks, CLI help checks, and isolated quick-start plus offline-wait smoke tests | Passed locally and in hosted CI |
| macOS Python | 3.12.14 | Same complete local check suite | Passed |
| Codex CLI | 0.144.1 | `plugin add` and `plugin marketplace` command surfaces inspected; manifest and marketplace validated | Packaging compatible; installation not performed |
| Linux Python | 3.9, 3.10, 3.12, 3.13 | [GitHub Actions CI run 36551279086](https://github.com/Sebastian-lxq/research-paper-workflow/actions/runs/36551279086) | Passed |
| macOS Python | 3.10, 3.13 | [GitHub Actions CI run 36551279086](https://github.com/Sebastian-lxq/research-paper-workflow/actions/runs/36551279086) | Passed |
| GitHub CodeQL | Python source scan | [CodeQL run 36551279138](https://github.com/Sebastian-lxq/research-paper-workflow/actions/runs/36551279138) | Passed |
| ChatGPT desktop local marketplace | Current supported client | Repo marketplace prepared | Pending installation test |
| Universal Plugins Directory | Public submission | Portable ZIP prepared | Not submitted |
| Windows | Any | POSIX file locks are used by state controllers | Unsupported in v0.1.0 |

“Passed” is limited to the listed test suite. It does not establish scientific
validity, a clean second-host install, or compatibility with future client
versions.

## Updating this matrix

Record the exact interpreter and client versions, the command run, and whether
the environment was a clean host. Do not promote a configured CI job to “passed”
until its actual run completes. Treat same-host interpreter changes and
second-host portability as different evidence.
