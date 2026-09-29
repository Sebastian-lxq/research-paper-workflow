# CLI exit-code contract

Bundled commands separate an invalid invocation from a valid record that has not
yet reached its scientific or operational gate. Automation should read the JSON
payload as well as the process exit status.

## Shared meanings

| Exit | Meaning |
| --- | --- |
| `0` | The command completed and its command-specific success condition holds. For mutation commands, this means the requested preview or write was structurally accepted—not that a scientific claim is true. |
| `1` | The input and state were structurally usable, but the requested gate is not satisfied, work remains, attention is required, or the executed probe failed normally. This is an expected research-state outcome. |
| `2` | Invalid input, unsafe path, malformed or stale state, integrity failure, unsupported transition, or controller refusal. |
| `124` | `exploration_probe.py run` exceeded its explicit timeout and stopped the process group. |

Argument parsing performed by Python's `argparse` may also return `2` before a
controller emits its normal JSON error object.

## Command-specific success conditions

| Controller | `0` | `1` | Other |
| --- | --- | --- | --- |
| `workflow_state.py` | `init`/`record` accepted, or `status` reached `submission-candidate` | Valid `status` is still in progress | `2` invalid state or input |
| `revision_cycle.py` | Mutation/preview accepted, or `status.ready` is true | Valid revision cycle is not ready | `2` invalid state or transition |
| `resume_view.py` | Build has no unresolved required mappings, or saved view is current | Build remains unresolved or saved view is stale | `2` invalid adapter/view |
| `check_release_handoff.py` | Registered release conditions are eligible | Structurally valid record is not release-eligible | `2` structural/input/validator failure |
| `review_handoff.py` | Requested stage or integrity verification succeeded | Not used | `2` refusal or integrity/input failure |
| `exploration_probe.py` | Probe command succeeded, or decision appended | Probe command exited nonzero or could not launch | `2` invalid request; `124` timeout |
| `idea_portfolio.py` | Candidate recommendation is eligible | Portfolio is valid but blocked from recommendation | `2` invalid portfolio |
| `research_operations.py` | Event accepted, or status has no attention/stale artifact | Valid status requires attention or contains stale artifacts | `2` invalid event/state |
| `empirical_contract.py` | Contract is release-eligible within its evidence ceiling | Contract is valid but has blockers | `2` invalid contract |
| `proof_lineage.py` | Hash-bound lineage projection is workflow-consumable | Manifest is valid but release, closure, review-record, or freshness blockers remain | `2` invalid manifest, graph, path, or invocation |
| `token_evaluation.py` | Measured reduction and protected non-regression are established | Evaluation is valid but that conclusion is not established | `2` invalid evaluation |
| `check_companions.py` | Inventory completed, including when providers are missing | Not used | `2` invalid manifest or request |

The authoritative machine-readable set for each entrypoint is
[`controllers.json`](../plugins/research-paper-workflow/controllers.json). Exit
status never upgrades the evidence ceiling documented for that controller.
