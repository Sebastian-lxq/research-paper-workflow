# Privacy

Research Paper Workflow is a skills-only plugin. The bundled controllers run on
local project files and do not include an analytics service, account system,
remote database, or bundled network server.

## Data handled locally

Depending on the user's project, the workflow may read or create:

- manuscript text, bibliographies, code, tables, and figures;
- project-local `.paper/` state, hashes, receipts, and review records;
- proof, empirical, and simulation artifacts supplied by the user;
- process identifiers, timing, and resource observations for authorized jobs.

These files remain in the user's chosen workspace unless the user separately
authorizes a connected tool or companion skill to transmit them.

## Companion skills and external services

Some optional companion skills search scholarly services, retrieve documents,
or use connected applications. They are not bundled by this plugin and retain
their own privacy, authentication, permission, and data-retention behavior. The
workflow must not treat installation as authorization to send private material.

## Public repository boundary

The repository rejects known personal absolute paths, private-adapter IDs,
common secret formats, generated caches, and the local portfolio snapshot. Its
examples are synthetic. Automated checks reduce accidental disclosure risk but
do not replace contributor review.

## User responsibility and deletion

Users control their local project files and may remove workflow state using
ordinary filesystem tools after reviewing the target. Removing the plugin does
not automatically delete research-project artifacts. Back up material that must
be retained before deleting local state.
