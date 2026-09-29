# Research preview pilot

Research Paper Workflow is recruiting a small first cohort of researchers who
are willing to test an inspectable, evidence-gated workflow rather than a
one-shot paper generator. The target is 5–10 pilot users in econometrics,
statistics, quantitative economics, or adjacent quantitative fields.

## Who should participate

The pilot is a good fit if you have one of the following:

- a public or synthetic research brief that is still at the idea or design stage;
- a methods paper with a proof, simulation, or literature dependency that is easy
  to lose across sessions;
- an existing project where you want the workflow to identify the next unmet
  evidence requirement;
- experience building research-agent infrastructure and an interest in testing
  state, handoff, or non-regression contracts.

Do not use unpublished manuscript text, confidential data, private referee
reports, credentials, or other material you cannot share with your selected
execution environment. The public issue tracker should contain only material you
are authorized to disclose.

## A 20-minute pilot path

1. Install the plugin using the two commands in the
   [quick start](QUICKSTART.md), or install the skill through `skills.sh`.
2. Run the bundled synthetic example before trying a real project.
3. Ask the workflow to inspect a research brief and identify the first unmet
   evidence requirement.
4. Check whether it distinguishes blocked, runnable, and result-dependent work.
5. Resume once and confirm that it reads existing `.paper/workflow/` state rather
   than starting again.
6. Report the first confusing instruction, incorrect route, missing dependency,
   or useful outcome.

## What useful feedback looks like

Please include:

- operating system and Python version;
- installation route (`codex plugin` or `skills.sh`);
- a public or synthetic prompt;
- expected behavior and actual behavior;
- whether the issue concerns installation, routing, state, scientific boundary,
  documentation, or another area;
- the smallest safe artifact needed to reproduce it.

Use the repository's **Pilot feedback** issue form, or start a GitHub Discussion
when the question is exploratory rather than a reproducible defect.

## What the pilot does not validate

A successful run does not establish novelty, mathematical correctness,
identification, simulation validity, publication readiness, or exhaustive
literature coverage. Pilot feedback improves the workflow's usability and
observable behavior; specialist scientific claims retain their own evidence
requirements.

