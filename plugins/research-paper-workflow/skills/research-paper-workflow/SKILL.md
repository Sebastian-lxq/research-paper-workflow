---
name: research-paper-workflow
description: Coordinate an econometrics or quantitative-economics paper from research ideas through literature, design, proofs, empirical evidence, manuscript, independent review, revision, and a submission package. Use for an end-to-end paper workflow or resuming a multi-stage research project; route single proof, simulation, or editing requests directly to the specialist skill.
---

# Research Paper Workflow

Turn a research question into a source-grounded, reproducible manuscript using
the research capabilities available in the current environment. Own sequencing,
handoffs, and continuity;
delegate scientific decisions to the relevant specialist. The deliverable may
be a complete paper or an explicitly simulation-deferred manuscript, depending
on the user's instruction and the evidence actually available.

## Start from the actual project

Read the active manuscript, project instructions, existing `.paper/` state, and
the smallest set of current results needed to identify the next unmet objective.
Respect existing filenames, language, programming environment, and author
decisions. Do not initialize a second claims database or rebuild finished work.
For a new project, infer a reasonable working question and paper type, propose
concrete candidate ideas, and continue low-cost research while material author
choices are pending. Do not require a completed idea before helping generate it.

Resolve capabilities from the skills and tools actually available in the
current environment; never assume the maintainer's local portfolio is installed.
Read [dependency-resolution.md](references/dependency-resolution.md) when a
specialist named below is missing, supplied by a different provider, or relevant
to a public installation. Continue work that remains valid without the missing
capability, keep dependent stages pending, and report the bounded gap. A generic
fallback may organize evidence, but it must not inherit a specialist skill's
release claims or validation status.

Classify the paper as `theory`, `methods`, `empirical`, or `hybrid`. Classify
simulation execution as `run`, `deferred`, or genuinely `not-applicable`.
Limited compute is `deferred`, never `not-applicable`. Default to bounded smoke
and pilot work until measured resource needs justify production runs.

Read [stage-playbook.md](references/stage-playbook.md) for the next relevant
stages and [handoffs-and-state.md](references/handoffs-and-state.md) for every
multi-stage project. Use [portfolio-routing.md](references/portfolio-routing.md)
to resolve ownership. Load each selected skill's actual `SKILL.md` and required
references before invoking it. Installed availability and current project
instructions outrank this routing map.

For every theory-bearing cross-skill handoff, also read
[proof-lineage.md](references/proof-lineage.md). Consume only the specialist's
hash-bound lineage projection; do not copy theorem or proof content into workflow
state or interpret a valid graph as mathematical verification.

When feedback accumulates, the research target changes, or work resumes across
stages, read [feedback-and-decisions.md](references/feedback-and-decisions.md).
Reuse the project's existing feedback and decision records; distinguish advice
collected from changes authorized, implemented and checked. Carry forward a short
current-state summary derived from those records, not a competing claims ledger.
When the existing records have explicit structured fields, use the read-only
[resume-view.md](references/resume-view.md) adapter to rebuild that summary and
check whether a saved view is stale. Unmapped prose still needs source reading;
a generated view cannot authorize work or settle scientific questions.

For iterative paper optimization, use
[iterative-optimization.md](references/iterative-optimization.md). A cycle can
contain several issues from eight optional areas; execute one selected issue at
a time, including its necessary dependent edits. There is no fixed three-round
count or theory/notation/writing order. Preserve whether the user requested one
item or continuous completion of the selected cycle; do not turn serial work
into repeated approval stops or parallel edits to unrelated issues.
Keep the frozen paper objective and manuscript spine above the local issue
queue. Admit a newly discovered item to the active cycle only when its relation
to that objective and the concrete consequence of leaving it unresolved can be
stated. Reassess the whole queue after each accepted item; do not keep following
the vocabulary or formatting neighborhood of the last edit.
For every material cycle, also read
[non-regression-contract.md](references/non-regression-contract.md) and define
what must improve, what must not regress, bounded trade-offs, paired evidence,
rollback conditions, and final whole-candidate review dimensions. Keep this
lightweight in ordinary single-item work and machine-checkable in continuous
revision. This contract supports a bounded non-regression claim; it does not
promise that every paper dimension improves.
Newly initialized continuous cycles also enforce the v2 issue package's
objective-link and admission fields; legacy v1 cycle state remains readable for
project continuity.

When the user requests one-start autonomous revision through an author-reviewable
candidate, also read [continuous-revision.md](references/continuous-revision.md).
Freeze its project contract, keep `.paper/revisions.yaml` as the issue authority,
and use `scripts/revision_cycle.py` for the single-active queue, hash-bound
reviews, author pauses and convergence checks. New cycles require
`paper-revision-contract.v2`; its current non-regression report is a readiness
gate, and accepted full reviews bind both the manuscript and that report. Legacy
v1 cycles remain readable but do not gain a retroactive machine-enforced report.
Continuous mode does not authorize
named experts, new compute, external access or submission; those must be present
in the frozen contract and remain subject to their own skills and permissions.

## Move the paper forward

1. **Frame and generate ideas.** Use `mine-econometrics-ideas` for candidate discovery and substantive comparison, reading its current entrypoint. Reuse existing candidate IDs, nearest-neighbor evidence, rejection reasons and actual probes; consume its handoff rather than create a second idea ledger. For an already selected mature idea, reopen only material gaps. Identify the scientific question, friction,
   estimand or testing target, proposed change, and who benefits. Compare a few
   materially different candidate ideas, their nearest neighbors, feasibility,
   and cheapest falsifiers. Preserve the reasons and explicit evidence-based reopen conditions for rejected or parked ideas; a resumed task or new title does not by itself reverse them.
   For novelty-sensitive work, several candidates, a long/resumed search, or an
   autonomous run, read [search-and-portfolio-control.md](references/search-and-portfolio-control.md).
   Bind the existing idea record to its optional controller sidecar and use
   `scripts/idea_portfolio.py`; do not copy the scientific argument into a second
   ledger. The controller exposes candidate diversity, actual probes, search
   frontiers, stop reasons and reopen conditions but never certifies novelty.
2. **Search and verify literature.** Use `paper-lookup`, then
   `citation-management` and `deepread`. Reopen exact source versions and
   locators before adopting a claim. Build a nearest-neighbor comparison and a
   dated search record; unresolved close neighbors constrain novelty language.
   Compare equivalent statistics and calibration as well as proof routes; state
   the actual new capability, insight and motivating problem before drafting
   contribution language. In controlled searches, keep named-method,
   deanchored-functional, citation, version, implication/equivalence,
   component-composition, cross-domain and contradictory-evidence paths visible;
   mark a path not applicable only with a substantive reason.
3. **Freeze the research design.** Choose the claim and paper spine; establish
   identifying assumptions, proof obligations, data availability, computation
   needs, benchmarks, failure criteria, and evidence required for each claim.
   Specify exploratory versus confirmatory work before examining outcomes. For repeated preliminary probes, read [exploration-loop.md](references/exploration-loop.md); preserve baseline, actual costs, failed attempts and decisions.
   For a long, costly, parallel, multi-provider or autonomous run, also read
   [research-operations.md](references/research-operations.md) and use the
   append-only operations log. Keep unknown resource measures null; aggregate
   operational state without moving scientific truth out of specialist records.
   For a long, multi-stage, autonomous, or explicitly token-sensitive project,
   also read [token-efficiency.md](references/token-efficiency.md). Reduce work
   losslessly before considering compression, protect scientific objects, and
   require a frozen paired evaluation before claiming quality-preserving token
   savings.
4. **Develop the required evidence.** Use
   `prove-econometrics-theory-v2` for theory,
   [empirical-bridge.md](references/empirical-bridge.md) for real-data design and
   execution, and `audit-numerical-simulations-v2` for Monte Carlo design,
   implementation, validation, and eventual production results. For theory
   handoffs, validate the active roots, typed dependencies, artifact bindings,
   specialist release state, and recorded review identity with
   `scripts/proof_lineage.py`. A proof gap or stale lineage binding blocks only
   its dependents; it does not prevent verified unrelated work. This controller
   does not re-prove the result or establish reviewer independence.
   For manuscript-bearing empirical results, validate the hash-bound adapter,
   known-answer fixture, inference settings, diagnostics, output and
   interpretation ceiling with `scripts/empirical_contract.py`; a green
   structural contract does not establish identification.
   Independent branches may run in parallel in ordinary development. During
   item-by-item optimization, any delegated work must serve the same active issue;
   leave independent optimization items queued until their turn.
   When a simulation or other offline job is running, do not spend model turns
   polling it. Persist the actual process/job handle and wait. Suspend every
   result-dependent action; continue only work that remains valid under every
   plausible result. The wait barrier and dependency edges are recorded with
   `research-operation-event.v2` as described in the token and operations
   references.
5. **Compose the manuscript as evidence matures.** Use
   `write-econometrics-paper-v3`. Begin useful setup and literature prose early,
   then write verified results and appendices, and finally reconcile abstract,
   introduction, title, and conclusion with delivered evidence. Drafting is
   allowed while evidence is pending; completing result-dependent claims is not.
   When the user requests de-AI editing or a final prose-humanization pass, the
   writer may compose the installed `humanizer` with its academic-humanizer
   profile. Apply it only after scientific claims are stable and verify protected
   equations, numbers, terminology, citations, and claim strength. The required
   output remains formal academic prose.
   The writer's terminology governance is binding across the workflow: prefer
   the established term used by the closest verified literature, preserve its
   scope, and record provenance for canonical terms. Do not coin a label for
   novelty, stylistic variety, or branding. An author-defined term needs a
   concrete gap, a definition, a mapping to the nearest literature terminology,
   and a recorded author decision before release use.
   Choose the requested reader-facing form: manuscript prose/proof, an explanation,
   or a meeting brief. Do not turn a short framework briefing into a full paper
   workflow or generate multiple formats the user did not need.
6. **Reproduce and challenge.** Check data-to-table/code-to-theorem alignment,
   citations, numbers, assumptions, builds, and rendered pages. Obtain fresh
   independent review; turn each supported finding into a bounded repair and
   verification task. Keep rejected findings with reasons. For a material
   revision, compare the current candidate with the frozen baseline against the
   primary objectives, protected scientific invariants, bounded trade-offs, and
   whole-candidate dimensions before treating the change as retained.
7. **Package and support revision.** Deliver manuscript source and rendered
   PDF, bibliography, appendices, reproducibility instructions, result provenance,
   limitations, and journal-specific materials. For material R&R re-review, use [evidence-first-review.md](references/evidence-first-review.md) to freeze criteria and assess manuscript evidence before revealing the response letter. Map every comment to
   evidence, edits, affected claims, and a verified response. Actual submission
   or external communication requires the user's instruction.

These are dependencies, not a rule to restart at step one. Resume at the earliest
stale or unfinished requirement and continue unaffected branches. Do not promise
that any arbitrary idea admits a new theorem or publishable conclusion; record
a falsified idea or infeasible design and develop a reviewable alternative.

## Optional expert supervision and independent roles

Preserve explicitly requested expert, roundtable, and review invocations and
authorizations across the active task. Do not interpret this workflow's name as
a literal invocation of an explicit-only component. If a compatible governed
supervision provider is installed and explicitly requested, let that provider
own its contract, expert selection, evidence readiness, private-source
boundaries, state, and gates. Read its actual instructions. Private expert
profiles, corpora, memory, and communications are never assumed, bundled, or
opened by this public workflow.

For ordinary end-to-end work, an independent generic reviewer can challenge the
design and final candidate without invoking a named expert. When the user
authorizes `review-paper`, `review-paper-code`, or `audit-analysis`, use those
specialized reviews in their applicable scope. See the runnable prompt profiles
in [usage-profiles.md](references/usage-profiles.md).

Give reviewers the claim, exact artifacts and evidence, not the desired verdict.
Use fresh contexts for final scientific checks. Batch parallel reviews within
available capacity; several roles in one worker are not independent reviewers.
Do not stack a multi-role review, expert roundtable, and supervisor at every
step. Escalate a concrete unresolved question only when it warrants it.

## Handle incomplete simulations honestly

`deferred` applies to production computation, not to the entire simulation
branch. Complete the design, runnable implementation where feasible, tests,
resource estimate, frozen run instructions, expected result schema, resume
procedure, and table-generation interface. Report any part that remains blocked.
Never insert fabricated measurements or use pilot results as confirmatory ones.

Bind a compute estimate to the full requested experiment inventory, including
expensive learners, reusable completed cells, missing cells and invalidated cells
that need reruns. A reduced option is a separate scope, not completion of the
original inventory. Consume the simulation skill's timing and precision evidence.

Keep simulation-dependent sentences and exhibits explicitly pending. Deliver a
coherent manuscript covering verified theory, literature and real-data evidence,
plus a separately identified simulation handoff. The available outcome is
`manuscript-ready-except-simulations`, not `submission-candidate`. When production
results arrive, validate their versions and actual replication records, rebuild
exhibits, update affected claims, rerun independent review and final packaging.

## Persist progress without duplicating scientific truth

The writer's `.paper/` files own claims, citations, exhibits, and author locks.
Proof ledgers, simulation manifests, and `.research-supervision/` retain their
own authority. Use `.paper/workflow/` only for the orchestration plan and
hash-bound stage receipts pointing to those artifacts. An existing equivalent
workflow store may be adapted instead; do not overwrite it.

The optional proof-lineage manifest is likewise a specialist-produced,
project-local interoperability record. It preserves identifiers, versions,
relationships, locators, hashes, status, and release scope only. The workflow
may rebuild `proof-lineage-status.v1`, but neither that report nor the manifest
may replace the specialist's obligation ledger, proof bundle, validator receipt,
or review.

For qualifying long-running work, the optional operations log under the same
directory owns only execution telemetry and blockers. For qualifying idea work,
the project-local portfolio sidecar owns only candidate/search control and binds
the authoritative idea record. Neither store may duplicate or override claims,
source judgments, proofs, results, reviews or author decisions. At resume, check
their current status before repeating searches, probes or provider calls.
The optional token evaluation is likewise derived control evidence: it binds a
frozen task/rubric, protected checks, observed usage, and paired evidence. It
does not become a second scientific ledger or weaken any specialist gate.

The bundled `scripts/workflow_state.py` supports `init`, `record`, and `status`.
Mutations preview by default and need `--write`. It derives readiness from exact
artifacts, checks, and current prerequisite receipts. It does not certify
mathematics or infer that a reviewer really inspected a file. Human-readable
review evidence and specialist verification remain necessary. See
[handoffs-and-state.md](references/handoffs-and-state.md) for commands and scope.
For cross-skill contracts that need current file or explicit fragment checks,
use [content-bindings.md](references/content-bindings.md). Reuse the existing
object/artifact IDs and dependency graph; do not refresh a hash to conceal an
unreviewed version change.

For an explicitly activated continuous-revision cycle,
`scripts/revision_cycle.py` previews `init`, `add`, `select`, `transition`,
`review`, and `sync` mutations unless `--write` is supplied. Its status can
establish controller convergence only; it cannot certify a theorem, result,
source claim or reviewer independence. The v2 controller validates current
evidence hashes and the frozen non-regression decision, but the report's
substantive judgments still require specialist evidence and independent review.
Do not use its state as scientific evidence or bypass specialist release
contracts.

## Deliver the actual requested scope

For a time-bounded, artifact-scored, or externally evaluated task, begin by
reading the request and enumerating its exact required files and checks. Write
the required artifacts as soon as the needed evidence is available, validate
them directly, and preserve partial progress before optional exploration. Reuse
unchanged valid receipts. Do not run Git status or history commands in a
workspace that has no repository metadata.

Use three explicit phases when a deadline is stated: by the end of the first
third every required file exists with its full schema and an honest provisional
state; by the end of the second third the decisive evidence and direct checks
are complete; the final third is reserved for targeted repair, serialization,
and return. Do not begin an optional project-wide scan in the final phase. A
failing optional assertion is recorded and investigated only when it can change
a required result; it does not justify withholding otherwise valid required
artifacts until the process is killed.

For a resume task, resolve the active pointer, verify the declared active-state
bindings and inspect the lock semantics, then write the requested resume
artifacts before opening large claim, citation, exhibit, or revision registries.
Read those registries only when a required output field remains unresolved.

Once the required artifacts exist and their direct checks pass, produce the
final response promptly. Run larger project audits or dependency test suites
only when the request calls for them, the implementation changed, a direct
check failed, or a material uncertainty remains. Reserve enough of the stated
time limit to serialize final artifacts and return a response; a broader clean
check must not turn an otherwise complete scoped delivery into a timeout.

In a deliberately partial resume workspace, absence of an artifact that is not
part of the authoritative active-state binding is an availability limit for
fresh reinspection. It does not by itself reopen completed work or create a new
freshness gate. Reopen a stage only when the active status records it as open,
a required dependency is incomplete, or a bound current artifact is missing or
has the wrong hash. Future submission-package files do not become prerequisites
for the current recorded next action merely because they are absent.

Lead with completed work, remaining scientific blockers, and next action.
Distinguish draft, simulation-deferred manuscript, and submission candidate.
Report actual tests and external checks, not proposed checks. An empirical-only
paper need not invent a theorem, a theory paper need not invent an application,
and unavailable optional tools should not block unrelated progress.

For the dated GitHub comparison and adopted mechanisms, read
[upstream-evidence.md](references/upstream-evidence.md). Stars prioritize source
inspection; they are not evidence of scientific correctness or novelty.
