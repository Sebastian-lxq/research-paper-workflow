# Companion-skill dependency model

Research Paper Workflow is an orchestrator, not a universal implementation of
literature search, theorem proving, simulation, or manuscript production.

The installable plugin contains the orchestration skill and deterministic
controllers. Companion skills are discovered at runtime. The authoritative
inventory is
[`dependencies/skills.json`](../plugins/research-paper-workflow/dependencies/skills.json).

## Resolution rules

1. Inspect the skills actually available in the current environment.
2. Prefer a named provider only when it is installed and its current entrypoint
   has been read.
3. If a provider is missing, identify the capability—not merely the package
   name—that is unavailable.
4. Continue work whose validity does not depend on that capability.
5. Leave dependent claims and stages explicitly pending.
6. Never report manager health, installation, or a schema pass as scientific
   validation.

## Relationship types

- **First-party companion:** maintained alongside this workflow but distributed
  separately in v0.1.1.
- **Third-party integration:** an independently maintained skill that may be
  invoked when installed; its code is not bundled.
- **Design influence:** a public project whose mechanism informed a local,
  independent implementation; it is not a runtime dependency.

The exact third-party sources and licenses are listed in
[`THIRD_PARTY.md`](../THIRD_PARTY.md).

CI-only GitHub Actions are a separate dependency surface. They are not runtime
companions and are not packaged with the plugin; their machine-readable
inventory is [`.github/actions-dependencies.json`](../.github/actions-dependencies.json).
