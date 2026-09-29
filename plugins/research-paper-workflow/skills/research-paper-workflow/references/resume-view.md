# Rebuild a short current-work view

Use when resuming from existing feedback and project records. The output is a
disposable navigation view; current source records remain authoritative. It does
not create author decisions, grant authorization, certify evidence, or initialize
another `.paper` store. For unstructured records, read the actual notes and use the
existing feedback-index template only when an equivalent store is absent.

## Partial-workspace rule

A resume fixture, handoff, or checkout may intentionally contain the active
pointer, status record, and a hash-bound subset rather than every historical
scientific artifact. Verify every artifact named by the authoritative
active-state binding. For an unbound referenced artifact that is absent, report
that fresh reinspection is unavailable in this workspace; do not call the
recorded completed stage stale, reopen it, or make restoration a prerequisite
unless the active status or dependency contract explicitly requires current
presence. The next action follows the true open gate in the active record.

## Map fields, not a new database

Create a small configuration with `schema_version: research-resume-adapter.v1`, file paths,
JSON pointers and field mappings. It does not contain copies of decisions or
claims. `objective` and `active_version` each select a value using `{path,pointer}`.
`issues`, `decisions`, `evidence` and `artifacts` each select an existing JSON array
using `{path,pointer,fields}`; field values are JSON pointers within each row.
Use project-relative paths. For example, an issue array in `research-notes.json`
at `/issues` can map `id` to `/id`, `status` to `/state` and `next_action` to
`/next_step` without changing that source format.

| Collection | Mapped concepts |
| --- | --- |
| issues | id, status, summary, version, next_action |
| decisions | id, status, summary, version, topic, explicit supersedes array |
| evidence | id, status, summary, version |
| artifacts | id, path, version, issue_id, relation |

For a historical file affected by a new target, optionally map
`artifacts.relation_version` to the version of that recorded impact assessment.
Keep `version` as the file's actual recorded version. Without this optional
mapping, relation scope uses `version`; an explicitly mapped but missing value
is unknown. Issue and relation version must match the current active issue and
target before a relation is displayed as affected or unrelated.

Optional `source_kind` and `source_locator` preserve the original user message,
user-relayed mentor advice, publication or review location. Missing origin stays
unknown; the notes file itself is not evidence that the user authorized a change.
The view includes the source record's path/pointer/hash for direct reopening.

Use `status_map` only to translate known source values to the corresponding
canonical state. Issues use active/pending/completed/blocked/rejected/deferred/
superseded; decisions use adopted/pending/rejected/deferred/superseded; evidence
uses available/withdrawn/superseded. Artifact relation is affected/unrelated/
unknown, with an explicit `relation_map` if needed. These are recorded states,
not new scientific or authorization judgments. Do not map a proposal to checked
work, or a missing record to withdrawn evidence, to make a view look complete.

For Markdown, optional `quotes:[{path,heading}]` selects a unique complete heading
line, such as `## Current handoff summary`. It displays the source text with its
locator; it does not infer decision state or permission from arbitrary prose.
Missing or duplicate headings remain unresolved. This is intentionally not a
general Markdown table migration tool.

## Generate and check

```bash
python3 -B "$WORKFLOW/scripts/resume_view.py" build \
  --project "$PROJECT" --adapter resume-adapter.json --format markdown
python3 -B "$WORKFLOW/scripts/resume_view.py" build \
  --project "$PROJECT" --adapter resume-adapter.json --format json > "$PROJECT/current-view.json"
python3 -B "$WORKFLOW/scripts/resume_view.py" check \
  --project "$PROJECT" --view current-view.json
```

Redirect a view to an appropriate file inside the project when persistence is
useful; source records are never written by the tool. Use `--previous` with an
existing derived view for a bounded change comparison. That previous view does
not supply current facts or revive old decisions. Rebuild after a meaningful
change; do not hand-edit a cached view into apparent freshness.

The current issue comes from explicit active state. More than one active issue
is a conflict, not a reason to choose the most recent row. Zero active issues may
be correct during collection or after completion; do not invent an active issue
or start the next queued one merely to fill the display. Read the actual user
request and cycle state for the permitted continuation.

Effective decisions follow explicit adopted replacements and their supersession
relationships. Dates alone do not settle conflicting adopted decisions. A
pending/rejected/deferred suggestion cannot cancel an adopted decision, and an
explicitly superseded decision is not revived. Preserve unresolved links and
conflicts rather than guessing a current null or model.

## Changes and evidence boundaries

Show the actual current target/version, current issue, active decisions and their
historical predecessors, newly listed or explicitly withdrawn evidence, affected
and unrelated artifacts, and the current issue's next action. Reuse affected/
unrelated declarations from their source and identify the issue they refer to;
do not infer dependencies from matching names. Keep adopted, implemented, checked
and scientifically established separate.

Mapped project artifacts receive a current file-existence/hash observation as
part of the view's freshness evidence. A hash matches bytes, not the correctness
of the recorded version or scientific claim. A saved view whose mapped source
or observed artifact changes is stale; missing and unresolved sources are visible.

Cached reports may be included as `{path,pointer,dependencies}`. Dependencies
select an existing array with mapped `path` and `sha256` fields. Without input
bindings, their freshness is unknown. Even matching registered input hashes is
only `registered-inputs-unchanged`, not a new run or proof that all inputs were
registered. Cached report text never supplies missing issue/decision authority.
For current workflow or content checks, run the existing trusted helper on actual
inputs and use its scoped evidence; never execute arbitrary project commands to
make a summary appear verified.
