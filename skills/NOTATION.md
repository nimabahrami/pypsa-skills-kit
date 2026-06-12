# Notation & contributor guide (humans only)

This file is for human readers and contributors. It is NEVER loaded into model
context — it sits outside every skill folder, costs zero tokens, and may
therefore use plain prose and tables. The skill files themselves are written
in a deliberately compressed grammar optimized for LLM consumption; this page
is the translation key.

## Reading the compressed grammar

| Symbol / form | Meaning | Example |
|---|---|---|
| `->` | then / causes / route to / maps to | `infeasible -> references/infeasibility.md` |
| `\|` | alternatives or list separator | `HiGHS \| Gurobi \| CPLEX` |
| `!` | critical warning — the line prevents a known expensive bug | `! overnight CAPEX -> overstated ~10-20x` |
| `=` | definition / equals | `1 bus = 1 energy-balance equation` |
| `~` | approximately | `~700 tokens` |
| `A..B` / `A-B` | numeric range | `1e-2..1e6`, `0.85-0.95` |
| `w/`, `w/o` | with, without | `extendable w/ capital_cost<=0` |
| `VERB:` prefix | imperative instruction to the agent | `RUN:`, `SET:`, `CHECK:`, `READ:`, `VERIFY:`, `BUILD:`, `USE:`, `ADD:`, `COMPUTE:`, `STATE:` |
| CAPITALIZED word mid-sentence | load-bearing emphasis, not shouting | `marginal_cost is EUR per MWh of OUTPUT` |

Success criteria are written as parameters, never adverbs: "VERIFY weightings
sum=8760", not "make sure the weightings are correct".

## File anatomy (the three context levels)

1. **L1 — frontmatter `description:`** in every SKILL.md. Always in model
   context. It is the ROUTER: the trigger keywords decide which skill
   hydrates. Editing rule: never delete a trigger keyword without checking
   `evals.json`; trigger recall outranks brevity.
2. **L2 — SKILL.md body.** Loaded only when the skill triggers. Thin router:
   conventions, workflow, pointers to references. Should not restate
   reference content.
3. **L3 — `references/*.md`.** Loaded one file at a time, on demand. The
   actual domain knowledge.
4. **`scripts/*.py`** never enter context — only their stdout does. Put
   anything deterministic and checkable here, not in prose.

## Entry formats you will encounter

- Chart catalog: `PURPOSE | BUILD | CATCHES` per entry; output file number =
  catalog entry number.
- Diagnostics maps: `symptom -> chart/check -> root cause -> owning skill`.
- Screening ranges: `tech -> eff | VOM | capex | notes` flat bullets, all
  numbers are screening bounds, not procurement data.

## Hard rules for edits

1. **Zero fact loss.** Compression touches wording only; every number, unit,
   formula, API identifier, and file pointer survives verbatim.
2. **Single owner per fact.** If two files state the same threshold, one owns
   it and the other points at it. Sync contracts that exist today:
   chart-catalog.md <-> standard_plots.py (SKILL.md "Extending" rule);
   ranges-*.md <-> validate_network.py (physical-realism "Extending" rule);
   diagnostics.md root causes <-> interpreting-results.md sanity battery;
   power-flow-checks.md Boundary section (owner) <-> skills/README.md domain
   guard (pointer); loading base (s_max_pu) owned by ranges-grid.md and the
   reactive screening bound owned by ranges-generation.md — power-flow-checks.md
   points at both.
3. **Scaling rule** (README): new technology -> reference entries + validator
   assertions, never a new skill. New chart -> catalog entry + plot function
   + palette row. Only a new OPERATION may add a skill.
4. **Adversarial review.** Substantive content changes go through at least one
   red-team round (fresh reviewer instructed to refute, with numeric
   verification against a solved network) before merging. This protocol has
   caught fatal errors in every round it has been run.
5. **Before release:** `python skills/test_scripts.py` (must be 0 failures),
   `python skills/run_evals.py` (trigger precision), re-measure L1 tokens if
   descriptions changed (README token-economics section).

## Compatibility policy

Prose facts that depend on library behavior must name the version they were
verified against (e.g. "PyPSA 1.x stores upper-bound duals <= 0"). The suite
is currently verified against the pins in README "Compatibility". When a new
PyPSA major version lands: run test_scripts.py, then grep the suite for
version-sensitive claims (`assign_all_duals`, `mu_upper`, `optimize()`
return shape, component attribute names) and re-verify each.
