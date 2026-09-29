# Third-party skills and design provenance

This package integrates with separately installed third-party skills and was
informed by public research-agent projects. It bundles none of their
implementation code or prompt text.

## Runtime skill integrations

| Skill | Upstream | Revision inspected | License | Bundled |
| --- | --- | --- | --- | --- |
| `paper-lookup`, `citation-management` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `1e5eeffbdad3749125afe7ab48a39694e27f181c` | MIT | No |
| `deepread` | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | `19392f7a08264ed00486a251f5b2098321771f94` | MIT | No |
| `review-paper`, `review-paper-code`, `audit-analysis` | [claesbackman/AI-research-feedback](https://github.com/claesbackman/AI-research-feedback) | `8abc36b5576eca04611b4d632260caace5f1a3b7` | MIT | No |
| `humanizer` | [blader/humanizer](https://github.com/blader/humanizer) | `9862685f575c65a8247f90369951df1b3416e3d6` | MIT | No |

See [`dependencies/skills.json`](dependencies/skills.json) for the
machine-readable capability inventory and missing-provider policy.

## Design influences

Mechanisms were independently implemented after inspecting public materials
from `obra/superpowers`, `OthmanAdi/planning-with-files`,
`K-Dense-AI/scientific-agent-skills`, `Galaxy-Dawn/claude-scholar`,
`wanshuiyin/Auto-claude-code-research-in-sleep`,
`brycewang-stanford/Auto-Empirical-Research-Skills`,
`brycewang-stanford/AER-skills`, `stanford-oval/storm`,
`assafelovic/gpt-researcher`, `SakanaAI/AI-Scientist`, and
`SamuelSchmidgall/AgentLaboratory`.

Exact mechanism notes, source links, and rejected overclaims are in
[`references/upstream-evidence.md`](skills/research-paper-workflow/references/upstream-evidence.md).
Popularity is not treated as evidence of correctness or scientific validity.

If future versions copy or modify upstream implementation or prompt text,
maintainers must add exact provenance and every notice required by the upstream
license before release.
