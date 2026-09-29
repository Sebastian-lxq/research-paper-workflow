# Research operations and human steering

Use the operations log for long, costly, multi-provider, parallel, autonomous,
or frequently resumed work. Do not require it for a short local edit or a single
cheap lookup whose outcome already fits the authoritative research record.

`.paper/workflow/operations.jsonl` is an append-only operational control plane.
It records observed execution, costs, failures, blockers and next actions. It
does not own claims, literature judgments, proof obligations, simulation truth,
empirical conclusions, author decisions, or reviewer verdicts.

## Event contract

Create a project-local JSON event with schema `research-operation-event.v1` for
ordinary observed execution. Use backward-compatible
`research-operation-event.v2` when dependencies or a wait barrier matter:

```json
{
  "schema": "research-operation-event.v1",
  "operation_id": "literature-search-1",
  "stage": "literature",
  "activity": "Run the deanchored nearest-neighbor search.",
  "state": "succeeded",
  "recorded_at": "2026-09-27T09:05:00+08:00",
  "worker_id": "primary-worker",
  "usage": {
    "wall_seconds": 300.5,
    "tokens": null,
    "cost_usd": null,
    "compute_seconds": 12.0,
    "source": "Local timer and provider response"
  },
  "provider": "OpenAlex",
  "artifacts": ["research/search-log.md"],
  "blocker": null,
  "next_action": "Compare the strongest verified neighbor."
}
```

Version 1 states are `started`, `succeeded`, `failed`, `blocked`, and
`cancelled`. Version 2 adds `waiting` plus two required fields on every event:
`dependencies` and `wait`. `dependencies` is a stable array of earlier
operation IDs. `wait` is null except while `state` is `waiting`, when it must
contain `kind`, a real process/thread/batch/scheduler/external `handle`, a
`resume_condition`, `dependent_actions_suspended: true`, and an optional
timezone-aware `next_check_at`.

Do not use repeated model turns to poll a simulation, build, render, index, or
other offline job. Save its handle and use the process/session wait mechanism.
If an external system cannot be awaited directly, prefer event notification or
one scheduled check. A downstream v2 operation cannot be `started` or
`succeeded` until all declared dependencies have succeeded; unrelated work may
continue with no dependency edge. Read
[token-efficiency.md](token-efficiency.md) for the full decision rule.

Completed and failed work may be recorded as the first observed event; a live
operation can instead progress from `started`. A terminal success cannot be
silently reopened under the same operation ID. Use a new ID for a new attempt,
or a permitted retry transition after a recorded failure/blocker.

Record only actually observed usage. Unavailable token, monetary, compute, or
wall-time values remain `null`, never zero. State the measurement source when a
value is present. A failure or blocker requires the concrete reason and next
action. Artifact paths are snapshotted; later mutation is reported as stale.

## Commands and control view

Preview an append, then write it:

```bash
python3 -B "$WORKFLOW/scripts/research_operations.py" record \
  --project "$PROJECT" --event research/operation-event.json
python3 -B "$WORKFLOW/scripts/research_operations.py" record \
  --project "$PROJECT" --event research/operation-event.json --write
```

Produce a compact machine or human view:

```bash
python3 -B "$WORKFLOW/scripts/research_operations.py" status \
  --project "$PROJECT"
python3 -B "$WORKFLOW/scripts/research_operations.py" status \
  --project "$PROJECT" --format markdown
```

The status aggregates only each operation's latest observed usage, separately
counts unknown measures, and surfaces active/waiting/failed/blocked work plus
stale artifacts. Use it at resume points and before asking the author for a
material choice. The author should see the current decision, evidence gap,
resource use, and concrete alternatives—not an undifferentiated activity
transcript.

Exit `0` means no recorded operation currently needs attention and no latest
artifact is stale; exit `1` means attention is required; exit `2` means invalid
state. No exit code establishes scientific validity or paper readiness.
