# Bundled controllers

All controllers use the Python standard library and are packaged under
`plugins/research-paper-workflow`. Their machine-readable registry is
[`controllers.json`](../plugins/research-paper-workflow/controllers.json).
Their record formats and compatibility states are separately indexed in
[`schemas.json`](../plugins/research-paper-workflow/schemas.json) and explained
in [State schemas and compatibility](STATE_SCHEMAS.md).

Run a CLI's `--help` before its first use. The repository release validator does
the same for every declared CLI so a broken entrypoint fails CI. Automation must
also follow the [CLI exit-code contract](EXIT_CODES.md): exit `1` commonly means
“valid but not ready,” not malformed input.

| Controller | Main interface | Purpose and evidence ceiling |
| --- | --- | --- |
| `workflow_state.py` | `init`, `record`, `status` | Stores orchestration receipts and readiness dependencies; it does not certify science. |
| `revision_cycle.py` | `init`, `add`, `select`, `transition`, `review`, `sync`, `status`, `retrospective` | Enforces one active revision issue, hash-bound review, and non-regression evidence. |
| `resume_view.py` | `build`, `check` | Rebuilds a read-only view from explicitly mapped records; it does not authorize work. |
| `check_release_handoff.py` | contract plus trusted validator | Checks transitive certificate consumption and release-vector consistency. |
| `review_handoff.py` | `prepare`, `criteria`, `evidence`, `verify`, `reveal` | Freezes evidence-first re-review packets and reveal order. |
| `exploration_probe.py` | `run`, `decide` | Runs an explicitly authorized argv command with bounded recording; it is not a security sandbox. |
| `idea_portfolio.py` | project and portfolio record | Checks candidate/search control fields without certifying novelty. |
| `research_operations.py` | `record`, `status` | Records observed operations, blockers, artifacts, resource use, and offline wait dependencies. |
| `empirical_contract.py` | project and empirical record | Checks executable result bindings; success does not establish identification. |
| `proof_lineage.py` | project and lineage record | Checks a proof-lineage projection, closure, statuses, and hashes; success does not establish theorem truth or reviewer independence. |
| `token_evaluation.py` | project and paired evaluation record | Reports savings only when comparable usage falls and every protected check passes. |
| `check_companions.py` | optional skill roots, text or JSON | Discovers known provider names; availability is not scientific validation. |
| `content_bindings.py` | Python library | Shared safe-path, regular-file, fragment, and hash validation. |

## Path convention

In the examples below, set `PLUGIN` to the installed plugin root and `WORKFLOW`
to its bundled skill:

```bash
PLUGIN=/absolute/path/to/research-paper-workflow
WORKFLOW="$PLUGIN/skills/research-paper-workflow"
python3 "$WORKFLOW/scripts/workflow_state.py" --help
```

Project-specific commands, schemas, and safety conditions remain in the linked
skill references; this page is an entrypoint inventory, not a replacement for
those contracts.
