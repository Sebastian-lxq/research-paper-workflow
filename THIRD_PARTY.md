# Third-party skills and design provenance

This project names the other skills and public projects that materially shaped
the workflow. Attribution here serves two purposes: users can understand what
must be installed separately, and maintainers can distinguish interoperability
from copied implementation.

## What is bundled

No implementation code or prompt text from the projects below is bundled in
this repository. The workflow calls some separately installed skills by their
public names and locally reimplements selected coordination mechanisms. Those
upstream projects are not submodules and are not downloaded during installation.

The machine-readable inventory is
[`dependencies/skills.json`](plugins/research-paper-workflow/dependencies/skills.json).

## Separately installed skill integrations

| Skill | Upstream | Pinned revision inspected | License | Relationship |
| --- | --- | --- | --- | --- |
| `paper-lookup` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/paper-lookup) | `1e5eeff` | MIT | Runtime integration for scholarly discovery and retrieval provenance |
| `citation-management` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/1e5eeffbdad3749125afe7ab48a39694e27f181c/skills/citation-management) | `1e5eeff` | MIT | Runtime integration for metadata and bibliography verification |
| `deepread` | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills/tree/19392f7a08264ed00486a251f5b2098321771f94/research/deepread) | `19392f7` | MIT | Runtime integration for source argument reconstruction |
| `review-paper`, `review-paper-code`, `audit-analysis` | [claesbackman/AI-research-feedback](https://github.com/claesbackman/AI-research-feedback/tree/8abc36b5576eca04611b4d632260caace5f1a3b7/Skills) | `8abc36b` | MIT | Optional, explicit independent-review integrations |
| `humanizer` | [blader/humanizer](https://github.com/blader/humanizer/tree/9862685f575c65a8247f90369951df1b3416e3d6) | `9862685` | MIT | Optional prose pass after scientific claims stabilize |

The plugin does not install these skills automatically. At runtime it discovers
available providers and narrows its claims when a provider is missing.

## Public projects that influenced the design

The following projects informed a mechanism, not copied code:

- [obra/superpowers](https://github.com/obra/superpowers): verification before
  completion and observable evidence.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files):
  durable plans, decisions, and restartable work.
- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills):
  rival hypotheses, discriminating predictions, and falsification-oriented ideation.
- [Galaxy-Dawn/claude-scholar](https://github.com/Galaxy-Dawn/claude-scholar):
  question-to-evidence research contracts.
- [wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep):
  artifact-backed stage gates.
- [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills)
  and [brycewang-stanford/AER-skills](https://github.com/brycewang-stanford/AER-skills):
  method routing and empirical identification interfaces.
- [stanford-oval/storm](https://github.com/stanford-oval/storm): perspective-guided
  search and evolving knowledge structures.
- [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher):
  visible search breadth, progress, and cost telemetry.
- [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist): candidate
  portfolios and bounded baseline-to-experiment loops.
- [SamuelSchmidgall/AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory):
  phase telemetry, checkpoints, and review-to-plan return paths.

Detailed source-to-mechanism notes and rejected overclaims are preserved in
[`upstream-evidence.md`](plugins/research-paper-workflow/skills/research-paper-workflow/references/upstream-evidence.md).
Popularity is not treated as evidence of correctness or scientific validity.

## CI-only GitHub Actions

The following MIT-licensed Actions execute only in repository CI and are not
bundled into the plugin: `actions/checkout@v7`, `actions/setup-python@v7`,
`actions/upload-artifact@v4`, `github/codeql-action@v4`, and
`actions/attest@v4`. Their exact workflow entrypoints are tracked in
[`.github/actions-dependencies.json`](.github/actions-dependencies.json), and
Dependabot monitors the declared major versions. The release validator rejects
an Action that appears in a workflow without a matching attribution record.

## First-party companion interfaces

The workflow also recognizes `mine-econometrics-ideas`,
`prove-econometrics-theory-v2`, `audit-numerical-simulations-v2`, and
`write-econometrics-paper-v3`. They are first-party companion interfaces, are
not bundled in v0.1.1, and must not be represented as third-party work.

## Contribution rule

When a contribution copies or modifies upstream implementation or prompt text,
the pull request must identify the exact source path and revision, confirm
license compatibility, preserve required notices, and update this file. A link
or conceptual influence alone does not mean code was copied.
