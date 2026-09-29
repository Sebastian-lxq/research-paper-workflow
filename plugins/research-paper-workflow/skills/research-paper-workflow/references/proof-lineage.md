# Proof-lineage interoperability

Use this interface when a theory-bearing project needs to pass a proof lineage
from a specialist proof system into the paper workflow. The workflow consumes a
small, hash-bound projection; it does not copy the proof ledger or become the
authority for theorem truth.

## Authority and evidence ceiling

The proof specialist and the paper project continue to own theorem statements,
assumptions, proof obligations, proofs, counterexamples, reviews, and release
decisions. `proof-lineage-manifest.v1` contains only stable identifiers,
versions, typed relationships, project-relative locators, SHA-256 bindings, and
the specialist's bounded release state. It must not contain theorem or proof
prose merely to make the workflow self-contained.

`scripts/proof_lineage.py` checks the interface shape, graph integrity, active
root closure, required status records, reviewer-identity separation, safe paths,
locators, and byte hashes. It does not re-prove any result, establish that a
reviewer is independent, or upgrade the specialist's verdict. Its output always
keeps these scientific conclusions false.

## Public genealogy framework

A complete proof genealogy keeps five layers separate. A provider may implement
them with files, a database, or another skill, but must not let evidence from a
weaker layer silently promote a stronger one:

| Layer | Owns | Must not imply |
| --- | --- | --- |
| Knowledge navigation | domains, routes, neighbors, coverage frontiers, and explicit omissions | source fidelity or theorem truth |
| Theorem interface | versioned inputs, outputs, assumptions, topology, dependencies, locators, and failure boundaries | that the source proof is correct or usable in a project |
| Proof truth | frozen statements and assumptions, obligation ledgers, proof artifacts, counterexamples, validator receipts, and reviews | applicability to a different target |
| Project transfer | target-specific assumption implication, domain match, output-strength comparison, and unresolved axes | that downstream prose may exceed the transferred result |
| Workflow handoff | the smallest active-root closure, current hashes, provider verdict, and wording ceiling | a new proof verdict or reviewer independence |

The public provider interface is read-only and may expose five corresponding
operations. Implementations may choose different command or API names, but the
returned objects must preserve the same boundaries:

1. `coverage(query)` returns navigation scope, provenance, explicit omissions,
   and a coverage ceiling.
2. `routes(query)` returns compact proof-route candidates with input/output
   classes, dependencies, failure boundaries, and source references.
3. `theorem(object_id, version)` returns one exact theorem interface plus its
   separate source-fidelity and proof-truth statuses.
4. `transfer(object_id, target_id)` returns a target-scoped, axis-by-axis
   applicability record and blockers; it never closes the target automatically.
5. `export_lineage(target_id, roots)` produces the
   `proof-lineage-manifest.v1` projection consumed by this workflow.

Search counts, stars, route scores, and schema validity are scheduling or
integrity signals only. They cannot populate a proof-truth or project-transfer
status. Each operation should return stable IDs and locators first; full source
or proof content remains with the provider and is loaded only when needed.

## Manifest contract

The root object contains exactly:

- `schema`: `proof-lineage-manifest.v1`;
- `lineage_id`: stable identifier for this exported lineage;
- `producer`: `name` and `version` of the authoritative proof provider;
- `specialist_release`: `status` (`pass`, `partial`, or `fail`), its bounded
  `scope`, and exact downstream `permitted_wording`;
- `roots`: current claim object IDs intended for downstream consumption;
- `objects`: typed versioned nodes;
- `edges`: typed relationships between those nodes.

Every object contains `id`, `kind`, `version`, `status`, `required`, `actor`, and
nonempty `bindings`. Supported kinds are `claim`, `assumption-set`, `obligation`,
`lemma`, `proof`, `counterexample`, `review`, and `certificate`. Status is one of
`verified`, `open`, `false`, `externally-dependent`, `not-applicable`,
`superseded`, or `withdrawn`. `actor` is required for review nodes and must be
`null` elsewhere. A distinct recorded actor is an integrity signal only; it is
not proof of reviewer independence.

Each binding has exactly `role`, `path`, `sha256`, and `locator`. Paths are
ordinary project-relative POSIX files outside `.paper/workflow/`. A locator is
either `{"kind":"file"}` or unique UTF-8 marker boundaries:

```json
{"kind":"markers","start":"<!-- theorem:start -->","end":"<!-- theorem:end -->"}
```

The hash covers the entire file for a file locator and only the text between the
two markers for a marker locator. Never refresh a changed hash until the proof
provider has reviewed and versioned that change.

Supported relations are `depends-on`, `uses-assumptions`, `discharged-by`,
`reviewed-by`, `falsified-by`, and `supersedes`. Their direction is from the
consumer/current object to its supporting or historical object. In particular:

```text
claim --uses-assumptions--> assumption-set
claim --depends-on-------> obligation --discharged-by--> proof/certificate
claim --reviewed-by------> review
new claim --supersedes---> old claim
```

The controller enforces typed targets for assumptions, discharges, reviews,
counterexamples, and supersession, and rejects cycles in load-bearing support or
supersession. `depends-on` is reserved for proof-bearing dependencies; use the
more specific relation for assumptions, reviews, and counterexamples.

An active root is workflow-consumable only when it is verified, binds at least
one assumption set and proof obligation, reaches a verified review with a
distinct recorded actor, every load-bearing object is resolved, every verified
obligation reaches a verified proof or certificate, the specialist reports
`pass`, and all referenced bytes remain current. `not-applicable` is accepted
only when the specialist explicitly recorded it for an object in the closure.

## Controller interface

Run the read-only check from the paper project:

```bash
python3 "$WORKFLOW/scripts/proof_lineage.py" \
  --project /absolute/path/to/paper-project \
  --record theory/proof-lineage.json \
  --pretty
```

Exit `0` means the exact recorded handoff is structurally consumable. Exit `1`
means the manifest is valid but an open/stale/missing/release condition blocks
consumption. Exit `2` means the manifest, graph, path, or invocation is invalid.
The derived `proof-lineage-status.v1` report is rebuildable control evidence,
not a proof certificate.

## Provider adaptation

A provider with a richer canonical theorem registry should export only the
active root closure needed by this paper. Preserve its own object IDs and
versions where the identifier grammar permits; map its statement, assumptions,
obligation ledger, proof bundle, validator receipt, and fresh-context review to
bindings instead of translating their content. When the provider changes a
statement, assumption set, proof dependency, or authoritative artifact, create
or select the new provider version and regenerate the projection. Do not mutate
an old manifest to make a changed artifact appear current.
