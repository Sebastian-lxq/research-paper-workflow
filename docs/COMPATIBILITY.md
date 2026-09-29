# Compatibility matrix

Last local and hosted-CI verification: 2026-09-29.

| Surface | Version or environment | Evidence | Status |
| --- | --- | --- | --- |
| macOS Python | 3.9.6 | Public-release validation, syntax compilation, 208 workflow tests, 12 repository integration tests, schema/workflow/dependency mutation checks, release-tamper checks, CLI help checks, and isolated quick-start plus offline-wait smoke tests | Passed locally and in hosted CI |
| macOS Python | 3.12.14 | Same complete local check suite | Passed |
| Codex CLI | 0.144.1 | Added the Git-backed marketplace at `v0.1.0`, installed the previously absent plugin, confirmed version `0.1.0` is enabled, and ran an installed controller entry point | Passed |
| Linux Python | 3.9, 3.10, 3.12, 3.13 | [GitHub Actions CI run 36551279086](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36551279086) | Passed |
| macOS Python | 3.10, 3.13 | [GitHub Actions CI run 36551279086](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36551279086) | Passed |
| GitHub CodeQL | Python source scan | [CodeQL run 36551279138](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36551279138) | Passed |
| GitHub release artifact | `v0.1.0` | [Packaging run 36552893525](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36552893525); external SHA-256, internal manifest, and GitHub provenance verified for digest `74164c80c29aabd4c9fab4bb5490fa3e8a05d2422e230f2ba663fff7b5232eb9` | Passed |
| skills.sh CLI | 1.7.0 | Discovered the nested skill without `--full-depth`; installed the public GitHub source into an isolated project with scripts and references present | Passed |
| ChatGPT desktop local marketplace | Current supported client | Repo marketplace prepared | Pending installation test |
| Universal Plugins Directory | Public submission | Portable ZIP prepared | Not submitted |
| Windows | Any | POSIX file locks are used by state controllers | Unsupported in v0.1.1 |

“Passed” is limited to the listed test suite. It does not establish scientific
validity, a clean second-host install, or compatibility with future client
versions.

## Updating this matrix

Record the exact interpreter and client versions, the command run, and whether
the environment was a clean host. Do not promote a configured CI job to “passed”
until its actual run completes. Treat same-host interpreter changes and
second-host portability as different evidence.
