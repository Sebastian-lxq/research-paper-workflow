# Quality-constrained token efficiency

Read this reference for a long, multi-stage, autonomous, or explicitly
token-sensitive project. The objective is **less model work for the same frozen
research obligation**, not shorter prompts at any scientific cost. Token limits
are resource constraints; they never waive evidence, proof, simulation,
citation, reproducibility, or independent-review gates.

## What may and may not be claimed

There are three distinct claims:

1. **Policy active**: the context, cache, routing, waiting, and rollback rules in
   this reference are being followed.
2. **Tokens reduced in one frozen comparison**: baseline and candidate token
   buckets were actually observed or comparably estimated, and the candidate
   used fewer tokens.
3. **Bounded non-regression passed**: the same frozen inputs and rubric were
   used, all protected checks passed for both runs, and the candidate evidence
   is current.

Only (2) plus (3) warrants “measured token reduction with bounded
non-regression,” and only for that comparison. A shorter context, cache hit,
successful unit test, or model self-rating alone does not establish unchanged
research quality. General “quality did not decline” remains unproved without a
representative evaluation across projects and fresh reviewers.

## Default control policy

Apply the following order. Stop as soon as the resource objective is met; do not
stack every technique by default.

### 1. Remove work before compressing content

- Resume from the earliest stale dependency, not from stage one.
- Load the active manuscript/object, exact dependent records, and the smallest
  set of current evidence needed for the next decision.
- Reuse a valid receipt only when its input, code/config, source version, and
  output hashes still match. A matching filename or prose summary is not a
  cache key.
- Do not reopen settled searches, rejected candidates, verified proofs, or
  completed cells merely because a new conversation began.
- Avoid speculative branches whose output cannot be used before a pending
  upstream result arrives.

This is the preferred **lossless** saving layer: progressive disclosure,
deduplication, exact locators, durable state, and dependency-aware execution.

### 2. Build a minimal evidence packet

For each worker or model call, supply:

- the current objective and acceptance criterion;
- exact authoritative object IDs and versions;
- only the dependency subgraph that can affect the decision;
- source locators or artifact paths with current hashes;
- protected scientific invariants and wording ceiling;
- the expected structured output and escalation condition.

Put stable instructions and schemas in the reusable prefix; put current task
facts and evidence after them. Do not paste whole ledgers, full conversation
history, or unrelated references when IDs and exact locators suffice. A compact
resume view is a navigation aid, not new scientific truth.

### 3. Retrieve narrowly, then widen on evidence

Start with object IDs, headings, locators, citation neighborhoods, or graph
neighbors that match the active obligation. Widen retrieval when:

- the current packet cannot answer a load-bearing question;
- contradictory evidence appears;
- the nearest-neighbor boundary is unresolved;
- a proof, result, or citation dependency is missing;
- the narrow route repeatedly fails the frozen check.

Retrieval recall is not source verification. Reopen the exact source/version
before adopting a claim.

### 4. Cache only reproducible work

Cache identity must include all inputs that can change the answer: task and
rubric version, source/artifact hashes, code/config, model/tool version when
material, and the applicable authorization/scope. Invalidate on any such
change. Safe default candidates are deterministic parsing, rendering, metadata
resolution, unchanged evidence packets, and completed offline computations.

Do not semantically cache an open-ended novelty judgment, theorem verdict,
author decision, or final scientific review as though wording similarity made
the task identical. A cache hit may save execution; it cannot upgrade the
evidence status of the cached result.

### 5. Route by risk and escalate, not by cost alone

- Use local tools for file discovery, hashes, schema checks, compilation,
  deterministic transforms, and numerical execution.
- Use a lighter model for bounded extraction, classification, formatting, or
  known-schema conversion when deterministic checks can reject mistakes.
- Use the standard scientific route for substantive synthesis.
- Use the strongest available reasoning/review path for theorem construction,
  ambiguous identification, novelty boundaries, conflicting evidence, and
  final load-bearing review.

Every lower-cost route needs a concrete escalation trigger: schema failure,
missing evidence, inconsistency, ambiguity, failed protected check, or repeated
repair. Do not downgrade a load-bearing scientific task solely because a token
budget is tight.

### 6. Constrain outputs and retries

Request the smallest complete deliverable in the specialist's native schema.
Prefer IDs, statuses, locators, deltas, and bounded explanations over repeated
restatement of the full project. Validate structured outputs locally and repair
only the failing field or dependency. Never make a rubric easier to avoid a
retry.

### 7. Parallelize only independent, useful branches

Parallel work saves wall time but can increase total tokens and reconciliation
cost. Start a branch only when its inputs are stable, its result is useful under
every plausible outcome of currently running prerequisites, and overlap with
other branches is low. Merge by artifact IDs and evidence locators, not by
having every worker re-summarize every other worker.

Several model personas in one context are not independent reviews. Fresh final
review remains governed by the applicable specialist workflow.

### 8. Run offline work outside the reasoning loop

Numerical simulation, compilation, rendering, indexing, local tests, and other
non-model work do not need continued model narration. Launch or attach to the
actual process, persist its handle, then apply the wait barrier below. Record
model tokens as zero only when the operation genuinely made no model call and
the measurement source says so; unknown usage remains `null`.

### 9. Evaluate and roll back

Freeze task inputs, rubric, protected checks, baseline, strategies, and rollback
conditions before inspecting the candidate result. Use
`scripts/token_evaluation.py` for a hash-bound paired record. Reject the
candidate when any baseline-passing protected check becomes `fail` or
`unknown`, even if token use falls sharply. A candidate with unknown usage may
be valid work, but no token-reduction claim follows.

## Wait barrier for simulations and other offline jobs

The decision is based on dependency, not internet access:

| Situation | Required action |
| --- | --- |
| A later claim, table, diagnostic, or choice depends on the running job | Save the handle and enter `waiting`; suspend the dependent action until terminal evidence arrives. |
| Work is independent of every plausible job result | Continue that bounded work; record no dependency edge to the job. |
| Work would probably be rewritten after the result | Do not start it. Waiting is cheaper and more reliable than speculative drafting. |
| A local process can be awaited directly | Use the process/session wait mechanism. Do not spend model turns polling it. |
| A remote batch or scheduler cannot be held open | Persist its job ID and resume condition; use event-driven notification or one scheduled check. Repeated unchanged model polls are prohibited. |
| The job exits, times out, or produces malformed output | Record the actual terminal or blocked state and inspect the artifact. Never infer success from elapsed time. |

Use `research-operation-event.v2` in the operations log. `waiting` requires a
real `kind`, `handle`, `resume_condition`, and
`dependent_actions_suspended: true`. A downstream v2 operation cannot enter
`started` or `succeeded` until every declared dependency has succeeded. The
controller still permits genuinely independent operations.

Example wait event:

```json
{
  "schema": "research-operation-event.v2",
  "operation_id": "simulation-production-1",
  "stage": "simulation",
  "activity": "Run the frozen production simulation.",
  "state": "waiting",
  "recorded_at": "2026-09-28T09:01:00+08:00",
  "worker_id": "local-simulator",
  "usage": {
    "wall_seconds": 60,
    "tokens": 0,
    "cost_usd": 0,
    "compute_seconds": 240,
    "source": "Local process metrics; no model call."
  },
  "provider": "local",
  "artifacts": [],
  "blocker": null,
  "next_action": "Await the process terminal event and validate its result manifest.",
  "dependencies": [],
  "wait": {
    "kind": "process",
    "handle": "session-42",
    "resume_condition": "The process exits and the result manifest is present.",
    "dependent_actions_suspended": true,
    "next_check_at": null
  }
}
```

## Protected content and compression boundary

Default to exact or lossless representations for:

- theorem statements, assumptions, nulls, estimands, rates, and proof
  obligations;
- equations, algorithms, code/config, random-number lineage, solver failures,
  replication counts, diagnostics, tables, figures, and numerical results;
- source versions, quotations, locators, citation keys, closest-paper
  comparisons, and contradictory evidence;
- author locks, scope decisions, permissions, rejected findings, rollback
  conditions, and independent-review verdicts.

Bounded lossy summaries may be used for non-authoritative background narrative,
old discussion detail, or navigation when every protected check is explicitly
guarded and the exact source remains available. Never use a lossy summary as the
sole support for a scientific claim or as a replacement for a current artifact.

## Measurement contract

Count only observed provider usage or a named tokenizer estimate. Normalize
input into mutually exclusive `uncached_input_tokens` and
`cached_input_tokens`, plus `output_tokens`; otherwise totals may double-count
or omit cache usage. Bind the tokenizer/provider normalization to an
`accounting_key` and compare only runs with the same measurement class and key. Record
latency, monetary cost, and compute separately in the operations log; fewer
tokens need not mean lower cost or shorter wall time.

The evaluation record contains:

- frozen input and rubric snapshots;
- nonempty protected checks;
- each optimization mechanism, fidelity, guarded checks, and rollback trigger;
- different baseline/candidate run IDs;
- complete quality-check coverage and current evidence snapshots;
- observed or explicitly unavailable token buckets.

Run:

```bash
python3 -B "$WORKFLOW/scripts/token_evaluation.py" \
  --project "$PROJECT" \
  --record "$PROJECT/research/token-evaluation.json"
```

Exit `0` means the recorded candidate used fewer comparable tokens and both
runs passed all frozen protected checks. Exit `1` is a valid record without
that joint conclusion; exit `2` is invalid or stale evidence. Even exit `0` is
bounded to the recorded comparison and does not certify general scientific
quality.

## Public GitHub mechanisms inspected on 2026-09-28

“High citation” is not a native GitHub metric. The table uses repository stars
as a dated popularity proxy and inspects the repository mechanism; stars do not
establish correctness, scientific quality, or local effectiveness. Counts are
approximate snapshots. No third-party code is vendored.

| Repository | Approx. stars | Mechanism considered | Local decision |
| --- | ---: | --- | --- |
| [microsoft/LLMLingua](https://github.com/microsoft/LLMLingua) | 6.7k | Prompt compression and long-context compression | Use only as bounded-lossy context reduction outside protected scientific objects; require paired checks. |
| [zilliztech/GPTCache](https://github.com/zilliztech/GPTCache) | 8.2k | Semantic response caching | Adopt hash/version-bound reuse for reproducible tasks; reject similarity-only reuse for open scientific judgments. |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 66.1k | Selective persistent memory | Persist decisions, IDs, evidence locators, and reopen conditions instead of full transcripts. |
| [letta-ai/letta](https://github.com/letta-ai/letta) | 24.9k | Stateful agents and memory tiers | Separate compact active state from durable authoritative artifacts; never treat memory as evidence. |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 42.4k | Durable execution, checkpoints, stateful graphs | Resume from hash-bound stage state and dependency edges; do not replay completed stages. |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | 52.3k | Indexing and selective retrieval | Retrieve the smallest stage-relevant evidence packet, then reopen exact sources. |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 26.6k | Explicit retrieval/routing pipelines and usage metadata | Make routing and escalation visible; keep actual usage distinct from unknown values. |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | 36.1k | Graph-based local/global retrieval | Use graph neighborhoods for literature and dependency recall, not as claim verification. |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | 39.9k | Dual-level entity/relationship retrieval and fewer model calls | Use dual-level retrieval only when both object and relation context matter; avoid full-corpus prompts. |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 91.4k | Document parsing, chunk provenance, grounded retrieval | Preserve source/chunk locators and inspect the exact passage before claim adoption. |
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | 31.5k | Perspective-guided research and evolving outlines | Search by materially different perspectives and reuse the evidence map; do not equate a generated report with verified literature. |
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | 29.6k | Decomposed subtopics, parallel research, source traces | Parallelize stable independent questions only; retain source provenance and cost observations. |
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | 38.4k | Metric-driven prompt/program optimization | Optimize against a frozen, representative rubric; do not tune the rubric after seeing failures. |
| [guidance-ai/guidance](https://github.com/guidance-ai/guidance) | 21.8k | Constrained generation and offline grammar tests | Use constraints to prevent malformed outputs and expensive retries; constraints do not verify content. |
| [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) | 15.9k | Structured generation | Require exact schemas for controller records and repair only invalid fields. |
| [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | 5.5k | Calibrated strong/weak model routing | Route bounded tasks downward with an explicit escalation threshold; keep final scientific boundaries on the strong path. |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 59.7k | Multi-provider routing, caching, fallback, and spend tracking | Normalize observed usage and record net routing cost; do not infer savings from model labels alone. |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 35.1k | Tracing, token/cost tracking, datasets, and evaluation | Bind savings claims to actual traces plus paired quality evaluation; unknown usage stays unknown. |
| [microsoft/autogen](https://github.com/microsoft/autogen) | 61.2k | Save/load state, pause/resume, model-client cache | Persist state at stable boundaries and resume it; do not repeatedly rehydrate full chat history or snapshot a running inconsistent state. |
| [PrefectHQ/prefect](https://github.com/PrefectHQ/prefect) | 23.9k | Dependency-aware workflows, caching, retries, event automation | Use an event-driven wait barrier for offline jobs and input/code-bound cache keys; no model polling loop. |

The useful synthesis is not a single compressor. It is a fail-closed controller:
**lossless work elimination first, selective retrieval second, cache/routing and
structured outputs third, lossy compression only at the edge, and paired
quality evidence before claiming success.**
