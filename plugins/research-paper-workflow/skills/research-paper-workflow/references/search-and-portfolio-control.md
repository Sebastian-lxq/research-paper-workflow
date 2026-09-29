# Search frontier and candidate portfolio control

Use this control for novelty-sensitive idea work, several materially different
candidates, a long or resumed search, or an autonomous run whose stopping basis
must be inspectable. A short discussion, one algebraic observation, or a bounded
closed-corpus comparison can remain in the existing Markdown idea record.

The scientific idea record remains authoritative. The optional
`research/idea-portfolio.json` is an orchestration sidecar: it binds that record
and its evidence by hash, exposes open search paths and candidate decisions, and
does not restate full arguments or become a second claims ledger.

## Candidate portfolio

Track candidates before the research design is frozen. Each entry has a stable
ID and locator in the idea record, the current S/O/R/F formation codes, the full
contribution fingerprint, the cheapest discriminating probe, actual search work,
planned and observed resource use, the decision, and evidence-based reopen
conditions. Candidate statuses are `active`, `parked`, `rejected`, and at most
one `selected` candidate.

Generate independent mechanisms when that could expose a better solution, but
do not impose a candidate quota. Distinct formation signatures are an advisory
diversity signal, not a score. Allocate the next small budget to the unresolved
candidate whose probe can most change the decision. Do not rank candidates by a
model's unsupported number, citation count, or ease of implementation. Preserve
failed probes and rejected candidates instead of silently replacing them.

Serial revision after the paper spine is frozen is unchanged: the continuous
revision controller still works on one active issue. Portfolio parallelism is
for pre-freeze idea and discriminating-experiment exploration, not simultaneous
unrelated manuscript edits.

## Search frontier

For a selected candidate, record all eight possible coverage paths. A path may
be `checked`, `open`, or `not-applicable`; the last state needs a substantive
reason. `checked` requires a current evidence artifact.

| Path | Question |
| --- | --- |
| `named-method` | Does work under the candidate's current names cover it? |
| `functional-deanchored` | Does a search without preferred names/authors find the same capability? |
| `citation-graph` | Do references, citing papers, and recommendations reveal a closer neighbor? |
| `version-lineage` | Do working-paper, journal, appendix, correction, or later versions cover it? |
| `direct-implication` | Is the claim a special case, corollary, equivalent expression, or routine derivation? |
| `component-composition` | Do existing components already combine to deliver the claimed capability? |
| `cross-domain` | Does another field use different terminology for the same structure? |
| `contradictory-evidence` | Is there a result, failure, or impossibility that defeats the proposed contribution? |

At least one targeted and one executed deanchored query are required before a
candidate is selected. Bind the strongest reasonable nearest neighbors to exact
versions and locators. A selected candidate must have no material open path, a
recorded stop reason, and a probe that survived its stated criterion. These are
eligibility conditions for the bounded wording “no core overlap was identified
in the recorded search”; they do not prove global novelty or recall.

Stop the current round when all recorded material paths have been resolved and
additional searches no longer change the candidate decision, or when the agreed
budget is exhausted and the verdict remains `investigate`. Never convert an
open material path into `not-applicable` merely to obtain a green status. New
versions, a changed contribution fingerprint, or a recorded `reopen_if` event
reopen only the affected paths.

## Validator

Resolve the installed workflow directory as `WORKFLOW` and run:

```bash
python3 -B "$WORKFLOW/scripts/idea_portfolio.py" \
  --project "$PROJECT" --record research/idea-portfolio.json --pretty
```

Exit `0` means the selected candidate satisfies the controller's recorded
eligibility checks, `1` means the file is valid but the portfolio is not ready
to recommend a candidate, and `2` means invalid or stale state. Inspect the
reported blockers. The validator checks exact fields, evidence hashes, query
modes, coverage/frontier consistency, probe status, and reopen conditions. It
does not execute literature searches, judge paper content, or certify novelty.
