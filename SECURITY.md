# Security policy

## Supported versions

| Version | Security updates |
| --- | --- |
| 0.1.x | Yes |
| Earlier or unversioned local copies | No |

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose unpublished
research, credentials, private corpora, arbitrary file contents, or command
execution. Use GitHub's private vulnerability reporting for the repository once
the remote is created. If that channel is unavailable, contact the maintainer
through the private contact method listed on the repository owner profile.

Include:

- affected version and platform;
- the smallest reproducer that does not contain confidential data;
- expected and observed behavior;
- impact and any known workaround.

Do not access data that is not yours, and do not include real secrets in a
report. Maintainers will acknowledge a valid private report, investigate it,
and coordinate disclosure after a fix or mitigation is available.

## Security boundaries

- `exploration_probe.py` can execute a user-selected local command. Treat project
  files and commands as untrusted until reviewed; the workflow does not grant
  permission to run an otherwise unauthorized command.
- Project state may contain unpublished claims, file hashes, and local paths.
  Keep it in the research project, not in this public repository.
- Companion skills may use network services. Their own permission, privacy, and
  authentication policies remain authoritative.
- A successful schema, manifest, or hash check does not authenticate the truth
  or authorship of scientific evidence.

Repository maintainers should enable secret scanning, push protection, private
vulnerability reporting, and required CI checks on the default branch.
