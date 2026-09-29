# Evidence-first material re-review

Use when checking repairs to load-bearing conclusions or serious review issues. Reuse existing issue IDs and closure records. A spelling correction does not require this protocol. This derived handoff bundle is not a second findings or claims database.

1. Give a fresh criteria worker only the original issues and acceptance requirements. Freeze an issue-complete criterion result before showing manuscript changes or the response letter. Criteria may allow equivalent scientifically adequate repairs; don't encode the author's preferred solution.
2. In another fresh context, give the frozen criteria, old/new manuscript and actual supporting evidence. Ask for an issue-complete verdict, reason and evidence locators. Preserve unresolved issues and evidence-based disagreement. Seal this result before revealing the response.
3. Only then provide the response letter and sealed evidence verdict to a fresh response-check context. Check whether the reply accurately describes the evidence and repair. A persuasive reply cannot substitute for a missing change. If the reply identifies genuinely overlooked evidence, retain the original verdict and record the new evidence, reason and superseding finding; don't silently overwrite it.

The controller can know all inputs, but stage workers receive only their packet. Use actual separate dispatches without inherited conversation, and retain their requests, results and context IDs. Renaming roles within one context does not provide this separation. Filesystem packets do not enforce access controls against a worker with broader tools; constrain the dispatch and inspect actual operation records. No claim of authenticated isolation or scientific correctness follows from hashes.

## Runnable packet helper

Use the workflow skill's `scripts/review_handoff.py` with a new output directory. Input spec:

```json
{
  "schema_version": "review-handoff-spec.v1",
  "project_root": "/absolute/project",
  "issues": [{"issue_id": "R1", "criterion": "Reported rates agree with current evidence and retain its scope."}],
  "old": ["old.md"],
  "new": ["main.md"],
  "evidence": ["results.json"],
  "response": ["response.md"]
}
```

All source paths are project-relative. The controller records their hashes. Commands:

```text
python scripts/review_handoff.py prepare spec.json /absolute/new-review-bundle
python scripts/review_handoff.py criteria /absolute/new-review-bundle criteria-result.json
python scripts/review_handoff.py evidence /absolute/new-review-bundle evidence-result.json
python scripts/review_handoff.py reveal /absolute/new-review-bundle
python scripts/review_handoff.py verify /absolute/new-review-bundle
```

`prepare` publishes `stage1/` only; send that directory, never `.controller/`, to the criteria worker. Criteria result schema is `review-handoff-criteria.v1`, with `issues: [{issue_id, criterion}]`. It must cover exactly the original IDs. Submit it to `criteria`, then dispatch the generated `stage2/` packet to the evidence worker.

Evidence result schema is `review-handoff-evidence.v1`, with `issues: [{issue_id, status, reason, evidence_locators: [{path, locator}]}]`. Status is `resolved` or `unresolved`; every issue needs at least one locator in registered old/new/evidence files. Submit it to `evidence`, which publishes `stage3/`; `reveal` returns its verified path. The response worker uses this packet and writes findings to the project's existing review record.

`verify` is read-only. Changed sources or sealed packet/results make the bundle stale: preserve it and create a new scoped review bundle after actual repair. Do not refresh hashes to disguise a changed version. The helper checks completeness, sequence and file integrity; it cannot decide whether criteria or evidence are substantively adequate, or certify the response-stage judgment.
