---
name: pypsa-reporting
argument-hint: [solved_network.nc] [figures wanted]
description: Utility-grade charts + visual reports from solved PyPSA networks. Triggers: plot | chart | visualize | figure | report results | present results | dispatch stack | energy balance plot | price duration curve | SOC / storage cycling plot | cost stack | capacity expansion chart | curtailment plot | network map | diagnostic panel | show binding hours/caps on a chart | make results presentable. PyPSA results only — NOT pandapower|PSS/E|PowerWorld, NOT non-energy data; stack ambiguous? VERIFY pypsa imports/deps first.
---

# PyPSA Reporting

Charts = instruments, not decoration: every catalog figure doubles as a bug detector. Boundary: numeric interpretation + sanity battery = pypsa-solve-and-debug | plausibility judgment = pypsa-physical-realism | this skill RENDERS.

Two layers, always this order:
1. diagnostic layer = compact panel (energy balance | prices | SOC | shedding) FIRST on every solved network. Diagnostics wrong -> STOP, fix model before presentation figures.
2. presentation layer = deliverable figures matching study question.

## Adapt, don't impose

- DETECT user's plotting stack from their code (matplotlib default | plotly/altair/web -> carry palette + restraint, not the API).
- scripts/standard_plots.py = runnable generator AND copy-from pattern library — lift single functions into user's own reporting flow.
- project palettes/configs OVERRIDE bundled palette.

## Workflow

1. READ references/design-system.md before any figure (palette | typography | layout | data-ink rules).
2. PICK figures from references/chart-catalog.md — each entry: PURPOSE | BUILD | CATCHES.
3. Canonical set in one shot: `python scripts/standard_plots.py solved_network.nc --outdir figures` (imports scripts/plot_style.py | optional assets/pypsa-report.mplstyle).
4. anything suspicious -> references/diagnostics.md = symptom -> chart -> root cause -> owning skill.

## Non-negotiable conventions

- carrier colors CONSISTENT across every figure of a report. plot_style.py owns mapping | user config overrides | never ad hoc per figure.
- diagnostic panel ships w/ EVERY report, even single-figure asks.
- remaining hard rules (takeaway titles | units on axes | caveat captions | binding-event annotation — ! clean chart of a constrained system = lie of omission) = references/design-system.md, loaded by workflow step 1.
- caption caveat wording: run type | weather year | foresight -> pypsa-solve-and-debug/references/interpreting-results.md Reporting discipline | market caveats -> pypsa-market-design | revenue caveats -> pypsa-asset-economics.

## Handoffs

- numbers wrong -> pypsa-physical-realism validator -> pypsa-solve-and-debug/references/infeasibility.md.
- shedding panel non-empty -> pypsa-solve-and-debug scripts/diagnose_infeasibility.py localizes; this skill only SHOWS it.
- revenue/economics figures: print all THREE bias caveats — perfect foresight | merchant-vs-system | wholesale-vs-asset price (fees/levies) — (pypsa-asset-economics) in the CAPTION, not a footnote.

## Extending

- new chart -> catalog entry (PURPOSE|BUILD|CATCHES) AND plot_* function in standard_plots.py AND palette row if new carrier. All three, or catalog/script drift.
