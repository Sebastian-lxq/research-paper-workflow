# Empirical execution bridge

This bridge fills the portfolio's design-to-analysis handoff. It coordinates
actual data work; it is not a universal estimator library or a certificate that
a causal assumption is true. Use the existing project language/environment.
Choose a verified implementation for the exact design and consult its current
official method documentation before relying on unfamiliar behavior.

## Feasibility before commitment

Identify dataset, access rights, unit, geography, period, sampling frame, treatment
or exposure, outcome, timing, and the variation that could identify the target.
Inspect real schema and a permitted sample. Record where selection, attrition,
measurement, missingness or aggregation could change the estimand. If the
necessary variation or data do not exist, revise the design before full coding.

Keep raw files immutable. Put cleaning and estimation in reproducible scripts;
preserve input versions/checksums, data dictionary, join keys, duplicates,
exclusion reasons, sample counts, transformations, units and output logs.
Require assertions for many-to-many merges and sample changes that matter.
Synthetic test data can verify implementation but cannot supply empirical results.

## Freeze the analysis specification

In `empirical/analysis-plan.md`, record:

- estimand and population, identifying assumptions, estimable contrast;
- primary/secondary hypotheses, sample, time window, outcomes, treatment timing;
- covariates/fixed effects, estimator, weights, tuning and transformations;
- inference method and dependence/cluster unit, confidence level, multiplicity;
- diagnostics, sensitivity checks, missing-data treatment, exclusion rules;
- tables/figures, effect-size interpretation, failure conditions and alternatives;
- exploratory/confirmatory label and versioned deviations after results are seen.

Do not optimize control variables or samples to maximize significance. A
specification multiverse is descriptive sensitivity analysis only when its
selection and uncertainty are reported; it is not a substitute for a design.
Do not choose a conclusion first and search for a specification that returns it.

## Match design to implementation

| Design family | Required handoff question | Output must include |
| --- | --- | --- |
| OLS / fixed effects | Which variation remains after controls/FE, and what conditional comparison is identified? | Exact sample, design matrix/FE, uncertainty and justified interpretation |
| IV / GMM | Which moment restriction identifies which parameter, and how is weakness or misspecification handled? | Instrument/moment definitions, relevant diagnostics, stated inference validity |
| DiD / event study | What treatment/cohort/time comparison targets the estimand under the stated assumptions? | Timing/aggregation/controls, estimator, uncertainty, diagnostics and sensitivity |
| RDD | Which local contrast and continuity or randomization conditions identify the target? | Running variable/cutoff, bandwidth/fit choice, diagnostics and robust uncertainty |
| Synthetic control | Which donor/time structure identifies the counterfactual comparison? | Donor selection, fit, treatment timing, placebo/sensitivity and inferential scope |
| ML / prediction | Is the target predictive or causal, and which sample splitting prevents leakage? | Training/tuning/test boundaries, held-out metrics and uncertainty where justified |

There are no universal F-statistic, pre-period-count, fit-quality, or significance
thresholds in this workflow. Justify diagnostics and inference using the actual
method, sample and assumptions; invoke theory-v2 for nonstandard justification.
Do not turn a diagnostic passing into proof of identification.

Potential Python implementation sources, subject to exact-task verification:
[statsmodels](https://www.statsmodels.org/stable/index.html),
[linearmodels](https://bashtage.github.io/linearmodels/), and
[PyFixest](https://py-econometrics.github.io/pyfixest/quickstart.html).
These are references, not claims that the packages are installed or that every
design above is covered. Inspect the environment and select only what is needed.

## Execute and verify

Implement the smallest executable analysis first. Check a known-answer fixture,
numerical scale, missingness, estimation sample, standard-error settings,
clustering, weights and convergence. Compare a representative result against an
independent implementation or analytic case when feasible. Save warnings and
failures; a fallback that changes the estimator requires a method change record.

Run the actual analysis and planned diagnostics. Export machine-readable result
records and build tables/plots from them. Retain code/config/environment identity,
sample counts, estimate, uncertainty, units, and admissible interpretation.
Validate substantive size and uncertainty, not just stars or p-values.

## Bind an executable adapter and result

For a result used by the manuscript, write an `empirical-result-contract.v1`
record and validate it with `scripts/empirical_contract.py`. The record binds:

- claim IDs and the estimand;
- dataset identity/version/checksum, exact sample definition and observation count;
- the frozen analysis plan and any post-plan deviations;
- method family, verified implementation/version, exact argv, configuration and
  raw machine-readable output;
- inference settings and assumptions, estimates, uncertainty and units;
- diagnostics and their actual evidence;
- table/figure inputs and other result artifacts;
- a passed known-answer fixture, an independent implementation comparison when
  feasible, reviewed runtime warnings, unresolved failures, and the permitted
  interpretation ceiling.

The command is recorded as argv, not re-executed by the validator. The project
owns the method-specific adapter in its existing language and environment; this
workflow supplies a portable interface rather than an unverified universal
estimator library. Use an analytic or trusted small fixture that exercises the
same estimator/inference path. If no independent implementation supports the
exact method, record `not-feasible` with the concrete reason instead of
fabricating agreement; the known-answer check remains required.

```bash
python3 -B "$WORKFLOW/scripts/empirical_contract.py" \
  --project "$PROJECT" --record empirical/result-contract.json --pretty
```

Exit `0` means the record is structurally current and its execution checks are
release-eligible, `1` means a valid record still has blockers, and `2` means an
invalid/stale record. This is an empirical handoff gate, not proof of causal
identification, estimator correctness outside the recorded fixtures, or a
license to use causal language.

Deliver `empirical/HANDOFF.md` with
`claim → estimand → data/sample → specification → estimator/inference → result
artifact → table/figure → permitted interpretation`. The paper writer consumes
this plus actual results. If the user selects code review, `review-paper-code`
checks the whole mapping and `audit-analysis` checks a specific genuine Git diff.
Reproducibility can pass while causal interpretation remains unsupported.

## Branch failures

No data access, invalid identification, insufficient sample, unavailable runtime,
or failed estimation are separate blockers. Continue unrelated proof/literature
work and provide the concrete missing input or alternative. Do not label such
a paper complete except simulations: missing empirical evidence is an additional
unfinished requirement, not covered by the simulation exception.
