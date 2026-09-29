# Capability and dependency resolution

Use this reference when a named specialist is absent, replaced by another
provider, or relevant to a public installation.

## Discover before routing

Inspect the current skill and tool catalog. A name in this workflow is a known
provider for a capability, not proof that the provider is installed. Read the
selected provider's current entrypoint before relying on its behavior.

The packaged machine-readable inventory is
[`../../../dependencies/skills.json`](../../../dependencies/skills.json).

## Capability fallback

When a preferred provider is missing:

1. state the missing capability and the stages or claims that depend on it;
2. look for an installed provider with the same substantive capability and
   evidence boundary;
3. if none exists, continue only work valid under every plausible output of the
   missing stage;
4. preserve runnable handoffs, inputs, expected outputs, and reopen conditions;
5. keep dependent manuscript language and release status pending.

Do not silently replace scholarly retrieval with unsupported memory, a proof
audit with model confidence, numerical validation with schema success, or
independent review with another persona in the same context.

## Public/private separation

Public installations contain no private expert adapter, corpus, memory, or
communication. A user may connect a separately governed private provider, but
that provider owns authorization, data access, egress, and evidence readiness.
The workflow sees only the capability and authorized outputs needed for the
current project.

## Version and evidence

Record a provider's name and version or source revision when its output becomes
load-bearing. Provider installation or health is operational evidence only; it
does not validate a scientific conclusion.
