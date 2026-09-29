# Compatibility matrix

Last local and hosted-CI verification: 2026-09-29.

| Surface | Version or environment | Evidence | Status |
| --- | --- | --- | --- |
| macOS Python | 3.9.6 | Public-release validation, syntax compilation, 208 workflow tests, 12 repository integration tests, schema/workflow/dependency mutation checks, release-tamper checks, CLI help checks, and isolated quick-start plus offline-wait smoke tests | Passed locally and in hosted CI |
| macOS Python | 3.12.14 | Same complete local check suite | Passed |
| Codex CLI | 0.144.1 | Added the Git-backed marketplace at `v0.1.0`, installed the previously absent plugin, confirmed version `0.1.0` is enabled, and ran an installed controller entry point | Passed |
| Linux Python | 3.9, 3.10, 3.12, 3.13 | [GitHub Actions CI run 36582213072](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36582213072) | Passed |
| macOS Python | 3.10, 3.13 | [GitHub Actions CI run 36582213072](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36582213072) | Passed |
| GitHub CodeQL | Python source scan | [CodeQL run 36582213075](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36582213075) | Passed |
| GitHub release artifact | `v0.1.1` | [Packaging run 36582960420](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36582960420); external SHA-256, internal manifest, and GitHub provenance verified for digest `905d19646d3dca1a2572386ffb1cbef4c431bb16c5f076a5570617c644095dcd` | Passed |
| GitHub Pages | Deployed from `site/` by GitHub Actions | [Pages run 36588102495](https://github.com/XuQingAcademic/research-paper-workflow/actions/runs/36588102495); public URL returned HTTP 200; the current site exposes detailed capability and case-study links and contains no video reference | Passed |
| skills.sh CLI | 1.7.0 | Discovered the nested skill without `--full-depth`; installed the public GitHub source into an isolated project with scripts and references present | Passed; public directory indexing remains pending |
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
