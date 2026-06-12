#!/usr/bin/env python3
"""plot_style.py - shared palette and matplotlib styling for PyPSA reports.

Import from sibling scripts (`from plot_style import apply_style, color_for, savefig`)
or copy into the user's codebase. Project/user palettes OVERRIDE this default:
pass overrides to color_for via set_overrides() or merge into CARRIER_COLORS.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

# Semantic colors shared across report figures. Red is reserved for failure
# states (shedding, overload) - see references/design-system.md.
INK = "#1A1A1A"          # load lines, zero/reference lines
ALERT_RED = "#DD1C1A"    # shedding, limit lines, failure annotations
ACCENT_BLUE = "#3D6FB6"  # single-series lines (price duration, duals)
MUTED_TEXT = "#666666"   # captions, empty states, fine print
SWATCH_DARK = "#4A4A4A"  # legend proxy for an emphasized bar segment
SWATCH_LIGHT = "#C9C9C9"  # legend proxy for a faded bar segment

# Curated, colorblind-aware default palette aligned with community conventions
# (solar amber, wind blues, hydrogen magenta, gas orange, coal grays).
CARRIER_COLORS = {
    "solar": "#F2C14E",
    "solar rooftop": "#F7D687",
    "onwind": "#3D6FB6",
    "wind": "#3D6FB6",
    "offwind": "#7FA5DB",
    "offwind-ac": "#7FA5DB",
    "offwind-dc": "#5E8BCB",
    "hydro": "#2E9E9E",
    "ror": "#6CC5B5",
    "run-of-river": "#6CC5B5",
    "PHS": "#2E7E9E",
    "battery": "#7FB069",
    "battery charger": "#9CC48B",
    "battery discharger": "#7FB069",
    "H2": "#D6589F",
    "hydrogen": "#D6589F",
    "electrolysis": "#C04A8E",
    "fuel cell": "#E07FB6",
    "gas": "#E1762E",
    "CCGT": "#E1762E",
    "OCGT": "#EE9B4F",
    "coal": "#5C5C5C",
    "lignite": "#7A5C44",
    "oil": "#3F3F3F",
    "nuclear": "#B05BB5",
    "biomass": "#3E7C3A",
    "heat pump": "#46B3A9",
    "resistive heater": "#F09A6A",
    "CHP": "#C9602A",
    "load": INK,
    "load shedding": ALERT_RED,  # red is reserved for failure states
    "transmission": "#6F6F6F",
    "AC": "#6F6F6F",
    "DC": "#8F8F8F",
    "co2": "#8C8C8C",
    "DAC": "#A6A6A6",
}

# substring fallbacks, checked in order, for carrier name variants
_KEYWORD_FALLBACKS = [
    ("shed", ALERT_RED),
    ("solar", CARRIER_COLORS["solar"]),
    ("offwind", CARRIER_COLORS["offwind"]),
    ("wind", CARRIER_COLORS["wind"]),
    ("hydro", CARRIER_COLORS["hydro"]),
    ("water", CARRIER_COLORS["hydro"]),
    ("battery", CARRIER_COLORS["battery"]),
    ("h2", CARRIER_COLORS["H2"]),
    ("electroly", CARRIER_COLORS["electrolysis"]),
    ("fuel cell", CARRIER_COLORS["fuel cell"]),
    ("gas", CARRIER_COLORS["gas"]),
    ("coal", CARRIER_COLORS["coal"]),
    ("lignite", CARRIER_COLORS["lignite"]),
    ("oil", CARRIER_COLORS["oil"]),
    ("nuclear", CARRIER_COLORS["nuclear"]),
    ("bio", CARRIER_COLORS["biomass"]),
    ("heat pump", CARRIER_COLORS["heat pump"]),
    ("heat", CARRIER_COLORS["resistive heater"]),
    ("chp", CARRIER_COLORS["CHP"]),
    ("line", CARRIER_COLORS["transmission"]),
    ("link", CARRIER_COLORS["DC"]),
]

_NEUTRAL_CYCLE = ["#8C9BAB", "#A8B5A2", "#C2A78F", "#9D8FB5", "#B5A28F"]
_overrides: dict[str, str] = {}


def set_overrides(mapping: Mapping[str, str] | None) -> None:
    """Project/user palette wins over the bundled default."""
    _overrides.update(mapping or {})


def color_for(carrier: str) -> str:
    """Resolve a carrier name to a hex color: overrides, exact match,
    lowercase match, keyword fallback, then a stable neutral."""
    c = str(carrier)
    cl = c.lower()
    if c in _overrides:
        return _overrides[c]
    if c in CARRIER_COLORS:
        return CARRIER_COLORS[c]
    if cl in CARRIER_COLORS:
        return CARRIER_COLORS[cl]
    for kw, col in _KEYWORD_FALLBACKS:
        if kw in cl:
            return col
    return _NEUTRAL_CYCLE[hash(cl) % len(_NEUTRAL_CYCLE)]  # stable per carrier


def apply_style() -> None:
    """Modern utilitarian rcParams - see references/design-system.md."""
    import matplotlib as mpl  # late import: keep module importable without it

    mpl.rcParams.update({
        "figure.constrained_layout.use": True,
        "figure.facecolor": "white",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 1.6,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    })


def despine(ax: Axes) -> None:
    """Hide the top and right spines on an axes."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def caption(fig: Figure, text: str) -> None:
    """Gray caption strip carrying run-type caveats - mandatory on economics figs."""
    fig.text(0.01, -0.02, text, fontsize=8.5, color=MUTED_TEXT, ha="left", va="top")


def savefig(fig: Figure, outdir: str | Path, name: str,
            formats: Iterable[str] = ("png",)) -> list[Path]:
    """Save `fig` as `<outdir>/<name>.<fmt>` for each format; returns the paths."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for fmt in formats:
        p = out / f"{name}.{fmt}"
        fig.savefig(p)
        paths.append(p)
    return paths
