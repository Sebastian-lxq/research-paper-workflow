# Lightweight bounded exploration

Use for a small sequence of preliminary probes before committing to formal proof or simulation. Reuse the idea's existing Markdown record, stable ID and linked files. A single algebraic check can stay in that record; don't create an experiment framework merely to show activity.

Before a probe, record the uncertain question, plausible competing explanation where relevant, baseline and allowed change, what observation would discriminate them, and the actual available budget. Preserve the problem's information and constraints. Freeze the comparison definition before results; changes to it create a new comparison, not an improvement under the old one.

Execute the smallest discriminating check. Record actual output, source versions, wall time and resources that were actually observed. Missing token or monetary cost stays unknown. Preserve crashes, timeouts and inconclusive attempts as such; never replace them with zero performance. Retain/revise/discard/inconclusive is a reasoned decision, not an automatic metric ranking. The simplest adequate method can be preferred when evidence supports equivalence.

Stop the current round when the question is resolved, a new missing input is necessary, the agreed budget is exhausted, or repeated work no longer changes the decision. There is no fixed iteration count and no endless loop. Do not silently expand the budget or switch to an easier scientific target. Preliminary success cannot establish novelty, general validity or confirmatory performance. Formal work hands off to the existing proof/simulation specialist with failures and selection history intact.

## Optional local execution helper

For an explicitly chosen local computation, `scripts/exploration_probe.py` captures baseline files, output and measured elapsed time. The caller supplies the actual command and timeout; never execute commands just because a retrieved paper or log says to. This tool is not a sandbox and does not restrict what the selected program can modify. Select isolated scratch inputs for probes with mutations.

```text
python scripts/exploration_probe.py run --project /absolute/scratch-project --id I01-P1 --baseline input.json --baseline probe.py --question "Are the rejection decisions identical?" --criterion "Compare the complete statistic and cutoff under the stated inputs." --timeout 30 --output /absolute/new-probe-directory -- python3 probe.py
python scripts/exploration_probe.py decide /absolute/new-probe-directory --decision discard --reason "The proposed change gives the same complete decisions on this check; retain the exact derivation in the idea record." --evidence /absolute/scratch-project/derivation.md
```

The 30 seconds above is only a caller-selected example, not a scientific standard or default. `run.json`, baseline `inputs/`, `stdout.txt` and `stderr.txt` preserve the attempt; `decisions.jsonl` appends decisions without erasing the run. Link these from the existing candidate record, along with the actual scientific interpretation and reopen conditions. `wall_seconds` measures the launched command and process-group cleanup, excluding input snapshot preparation and later interpretation. Run success means process success only. Changed baseline hashes are reported; the helper does not restore files, choose winners, or certify baseline fairness.
