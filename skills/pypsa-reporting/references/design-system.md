# Design system - modern utilitarian

Philosophy: Tufte data-ink ratio + contemporary finish. Nothing on canvas that doesn't encode data or aid reading. No 3D | no shadows | no decorative gradients | no rainbow colormaps. Restraint IS the modern look.

## Layout

- figure sizes: single chart 9x5 in (slides/screen) | 7x4.5 (documents) | diagnostic panel 12x8.
- export: PNG dpi=150 screen | 300 print | SVG for editable deliverables.
- small multiples > dual axes. No dual axes; MW and MWh never share a chart (capacity chart #6 = MW-only).
- whitespace: constrained_layout=True. Never squeeze 6 legends into one axes.

## Typography

- ONE sans-serif family throughout (DejaVu Sans default | Inter/Source Sans if project ships them — never mix).
- hierarchy: title 13-14 bold = TAKEAWAY sentence | axis labels 10-11 w/ units in brackets | ticks 9-10 | caption 8-9 gray #666 carrying run-type caveats.
- numbers: thousands separators | sensible rounding (no 7-digit EUR) | SI prefixes on axes (GW not 1000s of MW).

## Color

- carrier palette = scripts/plot_style.py CARRIER_COLORS — curated, colorblind-aware, community conventions (solar amber | wind blues | hydrogen magenta | gas orange | coal grays). USER/PROJECT CONFIG OVERRIDES.
- same carrier = same color in every figure. No exceptions.
- grays for context | ONE accent for highlighted series.
- sequential -> viridis/cividis | signed (duals, margins) -> diverging RdBu_r centered 0 | categorical -> carrier palette only.
- ! red reserved for failure states (shedding | violations) — never decorative.

## Axes + marks

- despine top/right | light y-grid only (alpha 0.25) | zero line emphasized when data crosses.
- direct-label line ends if <=5 series | legend outside axes otherwise (never on data).
- stacked areas: order by merit/role (baseload bottom | peakers top | storage at boundary | charging below zero) | load line near-black on top.
- ANNOTATE binding events on chart (VOLL hours shaded | caps = reference line + label).

## Interactive variants

plotly/web stack -> identical palette + restraint | tooltips replace direct labels | default static export still follows this document.

## Anti-patterns (refuse, offer utilitarian version)

- pie charts >3 shares | dual-axis line pairs (fake correlation) | truncated bar axes | rainbow heatmaps | per-figure bespoke palettes | legend-only ID of 12 series.
