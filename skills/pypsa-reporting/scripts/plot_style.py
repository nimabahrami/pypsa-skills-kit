#!/usr/bin/env python3
"""plot_style.py - shared palette and matplotlib styling for PyPSA reports.

Import from sibling scripts (`from plot_style import apply_style, color_for, savefig`)
or copy into the user's codebase. Project/user palettes OVERRIDE this default:
pass overrides to color_for via set_overrides() or merge into CARRIER_COLORS.
"""
from __future__ import annotations

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
    "load": "#1A1A1A",
    "load shedding": "#DD1C1A",  # red is reserved for failure states
    "transmission": "#6F6F6F",
    "AC": "#6F6F6F",
    "DC": "#8F8F8F",
    "co2": "#8C8C8C",
    "DAC": "#A6A6A6",
}

# substring fallbacks, checked in order, for carrier name variants
_KEYWORD_FALLBACKS = [
    ("shed", "#DD1C1A"), ("solar", "#F2C14E"), ("offwind", "#7FA5DB"),
    ("wind", "#3D6FB6"), ("hydro", "#2E9E9E"), ("water", "#2E9E9E"),
    ("battery", "#7FB069"), ("h2", "#D6589F"), ("electroly", "#C04A8E"),
    ("fuel cell", "#E07FB6"), ("gas", "#E1762E"), ("coal", "#5C5C5C"),
    ("lignite", "#7A5C44"), ("oil", "#3F3F3F"), ("nuclear", "#B05BB5"),
    ("bio", "#3E7C3A"), ("heat pump", "#46B3A9"), ("heat", "#F09A6A"),
    ("chp", "#C9602A"), ("line", "#6F6F6F"), ("link", "#8F8F8F"),
]

_NEUTRAL_CYCLE = ["#8C9BAB", "#A8B5A2", "#C2A78F", "#9D8FB5", "#B5A28F"]
_overrides: dict = {}


def set_overrides(mapping: dict) -> None:
    """Project/user palette wins over the bundled default."""
    _overrides.update(mapping or {})


def color_for(carrier: str) -> str:
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
    import matplotlib as mpl

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


def despine(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def caption(fig, text: str) -> None:
    """Gray caption strip carrying run-type caveats - mandatory on economics figs."""
    fig.text(0.01, -0.02, text, fontsize=8.5, color="#666666", ha="left", va="top")


def savefig(fig, outdir, name: str, formats=("png",)) -> list:
    from pathlib import Path

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for fmt in formats:
        p = out / f"{name}.{fmt}"
        fig.savefig(p)
        paths.append(p)
    return paths
