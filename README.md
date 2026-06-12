<p align="center">
  <img src="assets/pypsa-skills-kit.png" alt="PyPSA Skills Kit - industry-grade energy modeling skills" width="100%">
</p>

# PyPSA Skills Kit

Nine industry-grade AI agent skills for [PyPSA](https://pypsa.org) energy system modeling. This is the judgment layer that isn't in any documentation: which storage representation to pick before you build the wrong one, why your revenue number is 10–30% too optimistic before a lender sees it, what a five-digit CO₂ shadow price actually means, and why turning on unit commitment silently deletes your prices.

Works with **Claude Code**, **Kiro**, **Antigravity**, **Windsurf**, and any AI coding tool that supports markdown skill/rules files. Works with vanilla PyPSA **and** workflow frameworks (PyPSA-Eur, PyPSA-Earth).

---

## Why this kit

**Deep, not broad.** These skills cover the PyPSA layer only. For AC voltage detail, dynamics, protection, or distribution feeders, use an AC-tool suite (e.g. [PowerSkills](https://github.com/Power-Agent/PowerSkills)) — the kit knows its boundary and routes away from non-PyPSA stacks. It does screen the AC feasibility of optimized dispatch in-suite (`n.pf`, slack-distributed, assumption-stated) and hands off violations with numbers attached.

**Every script and every code snippet is tested.** A suite-level smoke test compiles every bundled script, solves a synthetic network, runs the validator and figure generator on it, and extracts and executes the fenced linopy recipes from the reference files. Trigger routing is eval-tested: 29-case suite, last full run 2026-06-12 scored 29/29 (adversarial negatives 7/7 rejected every run).

**Token-efficient by architecture.** ~23k tokens of expertise total; a typical task loads ~2.6k (~1.2k always-on index + one skill + one reference). The other ~90% stays on disk. Verification runs as code, not context: the validator is ~3.8k tokens of Python the model never reads — only its ~200-token report enters the conversation.

**Adversarially reviewed.** Content went through red-team rounds with numeric verification against solved networks. This caught, among other things, a sign inversion in merchant price interfaces and an LP wash-trading trap in multi-market co-optimization.

---

## Installation

The skills are plain markdown files — drop them into whatever folder your AI tool scans for skills/rules.

### Claude Code

```bash
# As a plugin (recommended)
claude plugin marketplace add https://github.com/nimabahrami/pypsa-skills-kit
claude plugin install pypsa-skills
# Skills invoked as: /pypsa-skills:pypsa-solve-and-debug

# Per project (no plugin)
cp -r skills/pypsa-* /path/to/your/project/.claude/skills/
# Skills invoked as: /pypsa-solve-and-debug

# Single session (no install)
claude --plugin-dir /path/to/pypsa-skill
```

### Kiro

```bash
# Per project
cp -r skills/pypsa-* /path/to/your/project/.kiro/skills/

# Global (all workspaces)
cp -r skills/pypsa-* ~/.kiro/skills/
```

Skills load automatically or via `/pypsa-solve-and-debug` slash commands.

### Antigravity

```bash
# Per project
cp -r skills/pypsa-* /path/to/your/project/.agent/skills/

# Global (all workspaces)
cp -r skills/pypsa-* ~/.gemini/antigravity/skills/
```

### Windsurf

Windsurf uses rules files rather than a skill folder. Add references to the skills you want in your `.windsurfrules` or `.windsurf/rules/pypsa.md`:

```bash
# Copy skills into your project
cp -r skills/pypsa-* /path/to/your/project/.windsurf/skills/

# Then reference them in .windsurfrules or .windsurf/rules/pypsa.md
echo "When working on PyPSA models, load context from .windsurf/skills/pypsa-*/SKILL.md" >> .windsurfrules
```

---

## Usage

Skills activate two ways in tools that support automatic trigger matching:

**Automatically** — describe your problem and the matching skill loads:
```
my optimization returns infeasible
what does this battery earn trading day-ahead and intraday?
```

**Explicitly** — call one by name (Claude Code / Kiro / Antigravity):
```
/pypsa-solve-and-debug barrier stalls with numerical difficulties
/pypsa-reporting results/networks/solved.nc dispatch + price duration
/pypsa-physical-realism my_model.nc
```

> In Claude Code with the plugin installed, prefix with the namespace: `/pypsa-skills:pypsa-solve-and-debug`

---

## The nine skills

| Skill | What it answers |
|---|---|
| [`pypsa-network-modeling`](skills/pypsa-network-modeling/SKILL.md) | How do I build or extend the network correctly? (+ PyPSA-Eur/Earth config-first workflows) |
| [`pypsa-sector-coupling`](skills/pypsa-sector-coupling/SKILL.md) | How do I represent heat, hydrogen, transport, and industry? |
| [`pypsa-custom-constraints`](skills/pypsa-custom-constraints/SKILL.md) | How do I express behavior in linopy — and prove it landed? |
| [`pypsa-physical-realism`](skills/pypsa-physical-realism/SKILL.md) | Is this model physically sane? (executable validator included) |
| [`pypsa-market-design`](skills/pypsa-market-design/SKILL.md) | Is the market representation right? Nodal/zonal, flow-based, reserves, congestion economics |
| [`pypsa-asset-economics`](skills/pypsa-asset-economics/SKILL.md) | Is this a defensible business case? Foresight/merchant/fee bias corrections, multi-market revenue |
| [`pypsa-data-pipelines`](skills/pypsa-data-pipelines/SKILL.md) | Where do realistic inputs come from? atlite, technology-data, fuel and CO₂ prices |
| [`pypsa-solve-and-debug`](skills/pypsa-solve-and-debug/SKILL.md) | Why won't it solve, and what do the results mean? |
| [`pypsa-reporting`](skills/pypsa-reporting/SKILL.md) | How do I turn a solved network into figures that double as bug detectors? |

---

## Suite tooling

```bash
# Smoke test: compile + solve + validate + plot (run before every release)
python skills/test_scripts.py

# Trigger-precision evals (LLM judge over the skill descriptions)
python skills/run_evals.py

# Domain guard: is this project actually PyPSA?
python skills/detect_stack.py .
```

---

## Documentation

- [`skills/README.md`](skills/README.md) — internal architecture: operations-as-skills, JIT token economics, scaling rules, maintenance cadence
- [`skills/NOTATION.md`](skills/NOTATION.md) — contributor guide: compressed notation, edit rules, sync contracts

---

## Compatibility

Verified against PyPSA 1.0.7, pandas 2.3, HiGHS 1.13, linopy 0.6, and PyPSA-Eur v2026.02.0. Version-sensitive facts name their version inline.

## License

[MIT](LICENSE)
