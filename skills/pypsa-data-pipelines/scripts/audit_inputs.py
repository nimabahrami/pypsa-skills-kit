#!/usr/bin/env python3
"""audit_inputs.py - time-series forensics for PyPSA input data.

Boundary: validate_network.py (pypsa-physical-realism) screens STATIC
parameters and structure; this script audits the TIME SERIES feeding the
model - timezone bugs, leap-year/DST artifacts, placeholder profiles,
seasonality physics. Keep in sync with the pitfalls in references/*.md.

Usage:
    python audit_inputs.py audit network.nc              # netCDF or CSV folder
    python audit_inputs.py audit network.nc --strict     # exit nonzero on WARN
    python audit_inputs.py convert annuity --overnight 4e5 --rate 0.07 --life 25 [--fom 0.02]
    python audit_inputs.py convert ttf --eur-mwh-hhv 35 [--eff 0.55]
    python audit_inputs.py convert api2 --usd-tonne 110 [--eurusd 1.08]

Exit code (audit): 0 clean / warnings only, 1 if any ERROR (or WARN w/ --strict).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    import pypsa

SOLAR_KEYWORDS = ("solar", "pv")
WIND_KEYWORDS = ("wind",)
ROR_KEYWORDS = ("ror", "run-of-river")
HYDRO_RES_KEYWORDS = ("hydro", "reservoir")
PUMPED_KEYWORDS = ("phs", "pumped")
HEAT_PUMP_KEYWORDS = ("heat pump", "gshp", "ashp")
HEAT_KEYWORDS = ("heat",)

NIGHT_HOURS_LOCAL = (0, 1, 2, 3)     # LOCAL solar night; shifted by bus longitude
NIGHT_CF_MAX = 0.05                  # mean night availability above this = tz bug
FLAT_STD_MIN = 1e-6                  # series std below this = placeholder
PU_UPPER_TOL = 1.001                 # p_max_pu above this = unit/bias overshoot
MIN_SEASON_DAYS = 200                # need both seasons to judge seasonality
TROPICS_LAT = 15.0                   # |lat| below this: skip seasonality physics
SOLAR_CF_RANGE = (0.05, 0.30)        # generous outer screening bounds; canonical
WIND_CF_RANGE = (0.08, 0.65)         # per-region ranges: ranges-generation.md
COP_RANGE = (1.0, 7.0)               # heat pump COP plausibility (series-wide)
MIN_DUP_SNAPSHOTS = 100              # identical-profile check needs a real series

# conversion constants (owners: references/cost-data.md)
HHV_TO_LHV_GAS = 0.901               # TTF quotes HHV; divide to get LHV basis
API2_MWH_PER_TONNE = 6.978           # 6000 kcal/kg NAR


@dataclass
class Finding:
    severity: str   # "ERROR" | "WARN"
    component: str
    name: str
    message: str

    def line(self) -> str:
        return f"[{self.severity}] {self.component:12s} {self.name:35s} {self.message}"


AddFinding = Callable[[Finding], None]


def _carriers_matching(df: pd.DataFrame, keywords: tuple[str, ...]) -> list[str]:
    mask = df.carrier.astype(str).str.lower().str.contains("|".join(keywords))
    return list(df.index[mask])


def _bus_coords(n: pypsa.Network, bus: str) -> tuple[float, float]:
    """(longitude, latitude) of a bus; (0, 0) when unset (PyPSA default)."""
    try:
        return float(n.buses.x.get(bus, 0.0)), float(n.buses.y.get(bus, 0.0))
    except (TypeError, ValueError):
        return 0.0, 0.0


def _night_hours_utc(lon: float) -> set[int]:
    """LOCAL night hours expressed in UTC, shifted by solar longitude.

    lon=0 (or unset) -> 0-3 UTC; Texas lon~-97 -> 6-9 UTC. Avoids the
    Europe-centric false positive on correct non-European models.
    """
    offset = round(lon / 15.0)
    return {(h - offset) % 24 for h in NIGHT_HOURS_LOCAL}


def _hemisphere(lat: float, lon: float) -> str:
    """'north' | 'south' | 'tropics' | 'unknown' (coords unset -> assume north)."""
    if lat == 0.0 and lon == 0.0:
        return "north"            # PyPSA default coords = unset; most models N
    if abs(lat) <= TROPICS_LAT:
        return "tropics"
    return "south" if lat < 0 else "north"


def _check_index(n: pypsa.Network, add: AddFinding) -> None:
    """Calendar integrity: duplicates, gaps, leap-year truncation."""
    import pandas as pd

    idx = n.snapshots
    if len(idx) < 2:
        return
    if idx.duplicated().any():
        add(Finding("ERROR", "Snapshots", "-",
                    "duplicated timestamps - DST fall-back artifact? convert to"
                    " UTC once (references pitfall)"))
    if not idx.is_monotonic_increasing:
        add(Finding("ERROR", "Snapshots", "-", "non-monotonic snapshot index"))
    diffs = pd.Series(idx).diff().dropna()
    step = diffs.median()
    gaps = int((diffs > step).sum())
    if gaps:
        add(Finding("WARN", "Snapshots", "-",
                    f"{gaps} gap(s) larger than the {step} base step - DST"
                    " spring-forward holes | missing data?"))
    try:
        years = sorted(set(idx.year))
    except AttributeError:       # non-datetime index
        return
    import calendar

    for y in years:
        in_feb = idx[(idx.year == y) & (idx.month == 2)]
        if calendar.isleap(y) and len(in_feb) and 28 in set(in_feb.day) \
                and 29 not in set(in_feb.day):
            add(Finding("WARN", "Snapshots", str(y),
                        "leap year without Feb 29 - silent 8760 truncation"
                        " drops stress days (suite leap-year rule)"))
    print(f"weather year(s) covered: {years} - VERIFY same year across"
          " VRE + heat + inflow + load (cold-dark-doldrums discipline)")


def _check_vre_profiles(n: pypsa.Network, add: AddFinding) -> None:
    """Solar-at-night (longitude-aware), placeholders, bounds, CF levels."""
    pmax = n.generators_t.p_max_pu
    solar = _carriers_matching(n.generators, SOLAR_KEYWORDS)
    wind = _carriers_matching(n.generators, WIND_KEYWORDS)
    profiled = solar + wind + _carriers_matching(n.generators, ROR_KEYWORDS)

    for name in profiled:
        if name not in pmax.columns:
            add(Finding("WARN", "Generator", name,
                        "profile-driven generator without p_max_pu series -"
                        " placeholder availability = 1.0 everywhere?"))
            continue
        s = pmax[name]
        if s.isna().any():
            add(Finding("ERROR", "Generator", name, "NaN in p_max_pu series"))
            s = s.dropna()
        if float(s.min()) < 0:
            add(Finding("ERROR", "Generator", name,
                        f"p_max_pu min {s.min():.3f} < 0"))
        if float(s.max()) > PU_UPPER_TOL:
            add(Finding("WARN", "Generator", name,
                        f"p_max_pu max {s.max():.3f} > 1 - MW instead of"
                        " per-unit | bias-correction overshoot?"))
        if float(s.std()) < FLAT_STD_MIN:
            add(Finding("WARN", "Generator", name,
                        "flat p_max_pu series - placeholder data?"))

    for name, rng, label in (
            [(g, SOLAR_CF_RANGE, "solar") for g in solar]
            + [(g, WIND_CF_RANGE, "wind") for g in wind]):
        if name not in pmax.columns:
            continue
        cf = float(pmax[name].dropna().mean())
        if not rng[0] <= cf <= rng[1]:
            add(Finding("WARN", "Generator", name,
                        f"mean {label} CF {cf:.2f} outside screening"
                        f" {rng} - wrong cutout year | unit confusion?"
                        " (per-region ranges: ranges-generation.md)"))

    for name in solar:
        if name not in pmax.columns:
            continue
        s = pmax[name].dropna()
        lon, _ = _bus_coords(n, n.generators.bus[name])
        hours = _night_hours_utc(lon)
        night = s[s.index.hour.isin(hours)]
        if len(night) >= 24 and float(night.mean()) > NIGHT_CF_MAX:
            add(Finding("ERROR", "Generator", name,
                        f"solar mean availability {night.mean():.2f} during"
                        f" local night ({sorted(hours)} h UTC @ lon {lon:.0f})"
                        " - timezone shift bug (UTC vs local)?"))

    by_values: dict[int, list[str]] = {}
    for name in profiled:
        if name in pmax.columns and len(pmax[name]) >= MIN_DUP_SNAPSHOTS:
            by_values.setdefault(hash(pmax[name].round(6).to_numpy().tobytes()),
                                 []).append(name)
    for group in by_values.values():
        buses = {n.generators.bus[g] for g in group}
        if len(group) > 1 and len(buses) > 1:
            add(Finding("WARN", "Generator", group[0],
                        f"identical p_max_pu series on {len(group)} generators"
                        f" across {len(buses)} buses ({', '.join(group[:4])})"
                        " - copy-pasted placeholder profile?"))


def _seasonal_means(s: pd.Series) -> tuple[float, float] | None:
    """(winter DJF mean, summer JJA mean) when both seasons are covered."""
    if len(s) < MIN_SEASON_DAYS * 24 // 3:
        return None
    djf = s[s.index.month.isin((12, 1, 2))]
    jja = s[s.index.month.isin((6, 7, 8))]
    if len(djf) < 28 * 24 // 3 or len(jja) < 28 * 24 // 3:
        return None
    return float(djf.mean()), float(jja.mean())


def _check_seasonality(n: pypsa.Network, add: AddFinding) -> None:
    """Hemisphere-aware physics: solar peaks in local summer, heat in winter."""
    pmax = n.generators_t.p_max_pu
    for name in _carriers_matching(n.generators, SOLAR_KEYWORDS):
        if name not in pmax.columns:
            continue
        lon, lat = _bus_coords(n, n.generators.bus[name])
        hemi = _hemisphere(lat, lon)
        if hemi == "tropics":
            continue
        seasons = _seasonal_means(pmax[name].dropna())
        if not seasons:
            continue
        djf, jja = seasons
        inverted = (djf > jja) if hemi != "south" else (jja > djf)
        if inverted:
            add(Finding("WARN", "Generator", name,
                        f"solar DJF CF {djf:.2f} vs JJA {jja:.2f} inverted for"
                        f" {hemi}-hemisphere bus (lat {lat:.0f}) - wrong-"
                        "hemisphere data | month-shift bug? intended?"))
    if n.loads.empty or "carrier" not in n.loads.columns:
        return
    pset = n.loads_t.p_set
    for name in _carriers_matching(n.loads, HEAT_KEYWORDS):
        if name not in pset.columns:
            continue
        seasons = _seasonal_means(pset[name].dropna())
        if seasons and seasons[1] > seasons[0]:
            add(Finding("WARN", "Load", name,
                        f"heat demand summer {seasons[1]:.0f} > winter"
                        f" {seasons[0]:.0f} - inverted seasonality?"))


def _check_loads(n: pypsa.Network, add: AddFinding) -> None:
    """Negative and placeholder-flat load series."""
    pset = n.loads_t.p_set
    for name in n.loads.index:
        if name not in pset.columns:
            continue
        s = pset[name].dropna()
        if not len(s):
            continue
        if float(s.min()) < 0:
            add(Finding("WARN", "Load", name,
                        f"negative load {s.min():.1f} MW - prosumer netting?"
                        " intended?"))
        if len(s) > 168 and float(s.std()) < FLAT_STD_MIN:
            add(Finding("WARN", "Load", name,
                        "flat load series over a long horizon - placeholder?"))


def _check_hydro(n: pypsa.Network, add: AddFinding) -> None:
    """Hydro reservoirs (non-pumped) should carry an inflow series."""
    inflow = n.storage_units_t.inflow
    for name in _carriers_matching(n.storage_units, HYDRO_RES_KEYWORDS):
        carrier = str(n.storage_units.carrier[name]).lower()
        if any(k in carrier for k in PUMPED_KEYWORDS):
            continue
        if name not in inflow.columns or float(inflow[name].abs().sum()) == 0:
            add(Finding("WARN", "StorageUnit", name,
                        "hydro reservoir without inflow series - pure-storage"
                        " representation intended? (pipeline: atlite runoff ->"
                        " normalize to national annual generation)"))


def _check_cop_series(n: pypsa.Network, add: AddFinding) -> None:
    """Heat pump COP must be a plausible, time-varying efficiency series."""
    eff_t = getattr(n.links_t, "efficiency", None)
    for name in _carriers_matching(n.links, HEAT_PUMP_KEYWORDS):
        if eff_t is None or name not in eff_t.columns:
            add(Finding("WARN", "Link", name,
                        "heat pump with STATIC efficiency - constant COP"
                        " overstates winter output exactly when it matters"
                        " (references/atlite-heat.md)"))
            continue
        s = eff_t[name].dropna()
        if not len(s):
            continue
        if float(s.min()) < COP_RANGE[0] or float(s.max()) > COP_RANGE[1]:
            add(Finding("WARN", "Link", name,
                        f"COP series [{s.min():.1f}, {s.max():.1f}] outside"
                        f" plausibility {COP_RANGE} (ranges-conversion.md)"))
        if float(s.std()) < FLAT_STD_MIN:
            add(Finding("WARN", "Link", name,
                        "flat COP series - placeholder? source-temperature"
                        " dependence missing"))


CHECKS = (_check_index, _check_vre_profiles, _check_seasonality, _check_loads,
          _check_hydro, _check_cop_series)


def audit(n: pypsa.Network) -> list[Finding]:
    """Run every input-forensics check; returns findings in check order."""
    findings: list[Finding] = []
    for check in CHECKS:
        check(n, findings.append)
    return findings


def _convert(args: argparse.Namespace) -> int:
    if args.kind == "annuity":
        r, life = args.rate, args.life
        ann = r / (1 - (1 + r) ** -life)
        cc = args.overnight * (ann + args.fom)
        print(f"annuity factor = {ann:.5f}  ->  capital_cost ="
              f" {cc:,.0f} EUR/MW/a (overnight {args.overnight:,.0f},"
              f" r={r}, n={life}, FOM={args.fom})")
    elif args.kind == "ttf":
        lhv = args.eur_mwh_hhv / HHV_TO_LHV_GAS
        print(f"TTF {args.eur_mwh_hhv} EUR/MWh_HHV = {lhv:.2f} EUR/MWh_LHV"
              " (suite efficiencies are LHV)")
        if args.eff:
            print(f"fuel component of marginal_cost @ eff {args.eff}:"
                  f" {lhv / args.eff:.2f} EUR/MWh_el (add CO2 + VOM)")
    elif args.kind == "api2":
        usd_mwh = args.usd_tonne / API2_MWH_PER_TONNE
        print(f"API2 {args.usd_tonne} USD/t = {usd_mwh:.2f} USD/MWh_th"
              f" = {usd_mwh / args.eurusd:.2f} EUR/MWh_th @ EURUSD"
              f" {args.eurusd}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="time-series forensics on a network")
    a.add_argument("network")
    a.add_argument("--strict", action="store_true", help="warnings also fail")
    c = sub.add_parser("convert", help="executable unit conversions")
    c.add_argument("kind", choices=["annuity", "ttf", "api2"])
    c.add_argument("--overnight", type=float, help="EUR/MW overnight CAPEX")
    c.add_argument("--rate", type=float, default=0.07)
    c.add_argument("--life", type=int, default=25)
    c.add_argument("--fom", type=float, default=0.0, help="FOM fraction of overnight")
    c.add_argument("--eur-mwh-hhv", type=float, dest="eur_mwh_hhv")
    c.add_argument("--eff", type=float, default=None)
    c.add_argument("--usd-tonne", type=float, dest="usd_tonne")
    c.add_argument("--eurusd", type=float, default=1.08)
    args = ap.parse_args()

    if args.cmd == "convert":
        return _convert(args)

    import pypsa  # late import so --help works without pypsa

    n = pypsa.Network(args.network)
    findings = audit(n)
    errors = [f for f in findings if f.severity == "ERROR"]
    warns = [f for f in findings if f.severity == "WARN"]
    for f in errors + warns:
        print(f.line())
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s) across"
          f" {len(n.snapshots)} snapshots.")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
