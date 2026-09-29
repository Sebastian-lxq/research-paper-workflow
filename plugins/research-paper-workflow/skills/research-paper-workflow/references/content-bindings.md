# Bind recorded objects to current content

Read when a proof, result table or other load-bearing object must be matched to
current files during a cross-skill handoff. Existing `workflow_state.py` stage
receipts already rehash their registered files. This adapter fills the narrower
contract-to-content gap; it does not replace those receipts or create another
claims database.

## Register an explicit match

Use `research-content-bindings.v1` with a `bindings` array. Each entry identifies
exactly one existing `object_id` or `artifact_id` and supplies:

| Field | Meaning |
| --- | --- |
| `record_sha256` | SHA-256 of the entire existing object/artifact record as canonical JSON: `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`, `allow_nan=False`, UTF-8. This binds the version/content/scope declaration or artifact support IDs. |
| `path` | Project-relative file path, without traversal or escaping symlinks. |
| `sha256` | SHA-256 of the exact file bytes or selected fragment bytes. |
| `locator` | `{"kind":"file"}` or `{"kind":"markers","start":"unique start marker","end":"unique end marker"}`. |
| `record_snapshot` | Optional for artifacts: the exact baseline artifact record, whose canonical digest must equal `record_sha256`. Retain it when precise support-change propagation is needed. It is baseline evidence, not a second editable current record. |

A marker fragment is the UTF-8 bytes strictly between the two exact markers,
excluding the markers while retaining whitespace/newlines. Each marker must
occur exactly once and the start must precede the end. Repeated, missing or
reversed markers are unresolved; the tool does not guess a LaTeX theorem from
a similarly named label. Use stable, explicit comments as markers when suitable.
Whole-file binding supports arbitrary bytes; marker binding requires valid UTF-8.

Register these expected hashes only after identifying the actual version and
checking the match. On change, retain the previous evidence, update the owning
object/version and rerun its affected checks before re-binding. Recomputing an
expected hash does not restore a scientific PASS. A record hash and a byte hash
serve different purposes: do not mechanically replace an existing semantic
`content_hash` or `scope_hash` with a raw file hash.

Objects govern their existing claims; artifacts use their existing `claim_ids`
support bindings. The sidecar cannot add scientific dependencies, claims or
certificates. Bind a table to the claims it actually supports, not every claim in
the paper. Keep any required versus optional dependency mapping in the existing
typed edge sidecar and justify it scientifically.

## Check and interpret

```bash
python3 -B "$WORKFLOW/scripts/check_release_handoff.py" \
  "$PROJECT/research-release-contract.json" \
  --validator "$WRITER/scripts/validate_research_contract.py" \
  --bindings "$PROJECT/research-content-bindings.json" \
  --project-root "$PROJECT" --pretty
```

Resolve these variables to existing trusted skill and project directories. Add
the existing `--edges` option when using typed certificate dependencies. Both
content options are required together; absence preserves the legacy record-only
meaning. These checks are read-only and require no additional authorization gate.

The report distinguishes `unchanged`, `changed`, `missing`,
`locator_unresolved` and `unbound`, with the corresponding record match. A same-ID
object whose version or scope record changed cannot silently reuse its old
binding. A missing required binding is unknown, not a verified match. Coverage
is evaluated for the required claim closure and its supporting artifacts;
unrelated optional branches do not block that closure merely because they have
not been bound.

Content failures become local reasons on the supported claims and propagate
through the already registered certificate graph. A changed table therefore
reopens its supported conclusions and their consumers; a separately bound,
unchanged theorem fragment on another branch remains reusable. Reports retain
recorded state/freshness and show the derived state requiring review separately.
The original contract, source files and old review evidence are not rewritten.

Do not let changing an artifact's `claim_ids` erase the old support obligation.
When the artifact record no longer matches, a valid `record_snapshot` lets the
checker propagate to both its old and current supported claims. If old support
cannot be recovered or mapped to current claims, it reports
`support_ownership_unknown` and withholds content eligibility for the required
closure. Current optional ownership alone cannot establish that the old artifact
was unrelated. Record-matching bindings without a snapshot remain compatible.

Matching bytes verifies the registered content match only. It does not establish
mathematical truth, correct table interpretation, the completeness of unregistered
dependencies, reviewer independence or permission to submit. Missing or changed
material limits its affected claims; continue authorized unaffected work.
