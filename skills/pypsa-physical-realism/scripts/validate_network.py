#!/usr/bin/env python3
"""validate_network.py - deterministic physical-realism checks for a PyPSA network.

Usage:
    python validate_network.py network.nc            # netCDF or CSV-folder path
    python validate_network.py network.nc --strict   # exit nonzero on WARN too

Checks structural invariants (free energy, free machines, topology, time accounting,
carbon accounting) and screens parameters against plausible ranges. Mirrors the rules
in ../references/ranges-*.md - keep both in sync when extending.

Exit code: 0 clean / warnings only, 1 if any ERROR (or any WARN with --strict).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Carrier keyword tables (lowercase substring matching on component.carrier)
# ---------------------------------------------------------------------------

# Conversion technologies that consume real inputs -> marginal_cost == 0 is a flag.
# The CO2-chain entries (methanol, synfuel, e-fuel, kerosene, ccs, ccu) intentionally
# widen this zero-VOM check too: capture/synthesis VOM is real.
CONVERSION_KEYWORDS = [
    "electroly", "fuel cell", "methanation", "fischer", "sabatier", "dac",
    "direct air", "haber", "ammonia", "steam reform", "smr", "chp",
    "methanol", "synfuel", "e-fuel", "kerosene", "ccs", "ccu",
]

# CO2-chain technologies that need explicit carbon accounting (co2 bus or, for
# Generator/Store/StorageUnit only, a carrier co2_emissions entry)
CO2_CHAIN_KEYWORDS = [
    "ccs", "ccu", "dac", "direct air", "methanol", "synfuel", "e-fuel",
    "kerosene", "fischer", "sabatier", "methanation",
]

# Carriers for which Link efficiency > 1 is legitimate (ambient-heat harvesters)
AMBIENT_HEAT_KEYWORDS = ["heat pump", "ground heat", "air heat", "gshp", "ashp"]

# Fossil carriers expected to carry co2_emissions > 0 (t/MWh_th)
FOSSIL_KEYWORDS = ["coal", "lignite", "gas", "ccgt", "ocgt", "oil", "diesel"]

# Generator efficiency screening ranges by carrier keyword (min, max)
GEN_EFF_RANGES = {
    "nuclear": (0.30, 0.40),
    "lignite": (0.30, 0.46),
    "coal": (0.34, 0.50),
    "ccgt": (0.50, 0.65),
    "ocgt": (0.30, 0.45),
    "biomass": (0.20, 0.50),
}

# Link efficiency screening ranges by carrier keyword
LINK_EFF_RANGES = {
    "electroly": (0.55, 0.90),       # incl. SOEC upper end
    "fuel cell": (0.40, 0.62),
    "heat pump": (1.5, 6.0),         # COP
    "resistive": (0.90, 1.0),
    "boiler": (0.80, 1.06),          # condensing on LHV basis can exceed 1 slightly
    "methanation": (0.70, 0.85),
    "battery": (0.88, 0.99),         # per-direction inverter+cell
}

STORE_STANDING_LOSS_MAX = 0.05       # 5%/h is beyond even small water tanks
ANNUALIZED_CAPEX_SUSPECT = 3.0e6     # EUR/MW/a above this looks like overnight CAPEX
ROUND_TRIP_MAX = 0.97                # electrochemical round-trip above this: flag


@dataclass
class Finding:
    severity: str   # "ERROR" | "WARN"
    component: str
    name: str
    message: str

    def line(self) -> str:
        return f"[{self.severity}] {self.component:12s} {self.name:35s} {self.message}"


def _match(carrier: str, keywords) -> bool:
    c = str(carrier).lower()
    return any(k in c for k in keywords)


def _range_for(carrier: str, table):
    c = str(carrier).lower()
    for key, rng in table.items():
        if key in c:
            return key, rng
    return None, None


def _series_cost_positive(n, comp_t: str, name: str) -> bool:
    """True if the component has a time-varying marginal_cost with max > 0.

    Value check, not column presence: an all-zero series (NaN->0 merge bug)
    must still flag.
    """
    pnl = getattr(n, comp_t, None)
    mc_t = getattr(pnl, "marginal_cost", None) if pnl is not None else None
    if mc_t is None or name not in getattr(mc_t, "columns", []):
        return False
    return float(mc_t[name].max()) > 0


def validate(n) -> list[Finding]:
    f: list[Finding] = []
    add = f.append

    # ---------------- topology ----------------
    used_buses = set()
    for comp, cols in [
        ("generators", ["bus"]), ("loads", ["bus"]), ("stores", ["bus"]),
        ("storage_units", ["bus"]), ("shunt_impedances", ["bus"]),
        ("lines", ["bus0", "bus1"]), ("transformers", ["bus0", "bus1"]),
        ("links", None),
    ]:
        df = getattr(n, comp, None)
        if df is None or df.empty:
            continue
        if comp == "links":
            cols = [c for c in df.columns if c.startswith("bus")]
        for c in cols:
            used_buses.update(df[c].dropna().astype(str))
    used_buses.discard("")
    for b in n.buses.index:
        if b not in used_buses:
            add(Finding("WARN", "Bus", b, "orphan bus - nothing attached"))
    missing = used_buses - set(n.buses.index)
    for b in sorted(missing):
        add(Finding("ERROR", "Bus", b, "referenced by a component but does not exist"))

    # ---------------- generators ----------------
    for name, g in n.generators.iterrows():
        eff = float(g.get("efficiency", 1.0))
        if not (0 < eff <= 1.0):
            add(Finding("ERROR", "Generator", name,
                        f"efficiency {eff} outside (0,1] - free energy"))
        key, rng = _range_for(g.carrier, GEN_EFF_RANGES)
        if rng and not (rng[0] <= eff <= rng[1]):
            add(Finding("WARN", "Generator", name,
                        f"efficiency {eff} outside screening range {rng} for '{key}'"))
        if (_match(g.carrier, FOSSIL_KEYWORDS) and float(g.get("marginal_cost", 0)) <= 0
                and not _series_cost_positive(n, "generators_t", name)):
            add(Finding("WARN", "Generator", name,
                        "fossil unit with marginal_cost <= 0 - fuel cost missing?"))
        if bool(g.get("p_nom_extendable", False)):
            cc = float(g.get("capital_cost", 0))
            if cc <= 0:
                add(Finding("ERROR", "Generator", name,
                            "extendable with capital_cost <= 0 - free capacity"))
            elif cc > ANNUALIZED_CAPEX_SUSPECT:
                add(Finding("WARN", "Generator", name,
                            f"capital_cost {cc:.3g} EUR/MW looks like overnight CAPEX,"
                            " not annualized"))
            if bool(g.get("committable", False)):
                # invalid through PyPSA 1.0.x; >=1.1.0 allows via big-M
                try:
                    import pypsa
                    major, minor = (int(x) for x in
                                    str(pypsa.__version__).split(".")[:2])
                    new_enough = (major, minor) >= (1, 1)
                except Exception:  # noqa: BLE001
                    new_enough = False
                add(Finding("WARN" if new_enough else "ERROR", "Generator", name,
                            "committable AND extendable - invalid through PyPSA"
                            " 1.0.x; >=1.1.0 uses big-M (committable_big_m) -"
                            " intended?"))
        pmin, pmax = float(g.get("p_nom_min", 0)), float(g.get("p_nom_max", float("inf")))
        if pmin > pmax:
            add(Finding("ERROR", "Generator", name, f"p_nom_min {pmin} > p_nom_max {pmax}"))

    # ---------------- links ----------------
    for name, l in n.links.iterrows():
        eff = float(l.get("efficiency", 1.0))
        if eff > 1.0 and not _match(l.carrier, AMBIENT_HEAT_KEYWORDS):
            add(Finding("ERROR", "Link", name,
                        f"efficiency {eff} > 1 on carrier '{l.carrier}' - free energy "
                        "(only ambient-heat devices like heat pumps may exceed 1)"))
        if eff <= 0:
            add(Finding("ERROR", "Link", name, f"efficiency {eff} <= 0"))
        key, rng = _range_for(l.carrier, LINK_EFF_RANGES)
        if rng and not (rng[0] <= eff <= rng[1]):
            add(Finding("WARN", "Link", name,
                        f"efficiency {eff} outside screening range {rng} for '{key}'"))
        if (_match(l.carrier, CONVERSION_KEYWORDS) and float(l.get("marginal_cost", 0)) == 0
                and not _series_cost_positive(n, "links_t", name)):
            add(Finding("WARN", "Link", name,
                        "conversion technology with marginal_cost == 0 - water/"
                        "catalyst/stack wear are real costs (canonical bug)"))
        if float(l.get("p_min_pu", 0)) < 0 and eff < 0.999:
            add(Finding("WARN", "Link", name,
                        "bidirectional (p_min_pu<0) lossy link - losses applied in the"
                        " wrong direction on reverse flow; use anti-parallel links"))
        if bool(l.get("p_nom_extendable", False)):
            lcc = float(l.get("capital_cost", 0))
            if lcc <= 0:
                add(Finding("WARN", "Link", name,
                            "extendable link with capital_cost <= 0 - intended?"
                            " (only the paired charger OR discharger of a"
                            " storage may be free)"))
            elif lcc > ANNUALIZED_CAPEX_SUSPECT:
                add(Finding("WARN", "Link", name,
                            f"capital_cost {lcc:.3g} EUR/MW looks like overnight"
                            " CAPEX, not annualized"))

    # ---------------- stores / storage units ----------------
    full_year = len(n.snapshots) > 0 and float(
        n.snapshot_weightings.objective.sum()) >= 8000
    for name, s in n.stores.iterrows():
        sl = float(s.get("standing_loss", 0))
        if sl < 0 or sl > STORE_STANDING_LOSS_MAX:
            add(Finding("ERROR" if sl < 0 else "WARN", "Store", name,
                        f"standing_loss {sl}/h outside [0, {STORE_STANDING_LOSS_MAX}]"))
        if full_year and not bool(s.get("e_cyclic", False)):
            add(Finding("WARN", "Store", name,
                        "full-year run without e_cyclic - optimizer can drain storage"
                        " for free by the final snapshot"))
        if bool(s.get("e_nom_extendable", False)) and float(s.get("capital_cost", 0)) <= 0:
            add(Finding("ERROR", "Store", name,
                        "extendable with capital_cost <= 0 - free energy capacity"))
    for name, su in n.storage_units.iterrows():
        es = float(su.get("efficiency_store", 1.0))
        ed = float(su.get("efficiency_dispatch", 1.0))
        rt = es * ed
        if not (0 < es <= 1) or not (0 < ed <= 1):
            add(Finding("ERROR", "StorageUnit", name,
                        f"per-direction efficiencies ({es},{ed}) outside (0,1]"))
        elif rt > ROUND_TRIP_MAX:
            add(Finding("WARN", "StorageUnit", name,
                        f"round-trip {rt:.3f} > {ROUND_TRIP_MAX} - optimistic"))
        mh = float(su.get("max_hours", 1))
        if not (0.25 <= mh <= 1000):
            add(Finding("WARN", "StorageUnit", name,
                        f"max_hours {mh} outside [0.25, 1000] - MWh/MW mix-up?"))
        if full_year and not bool(su.get("cyclic_state_of_charge", False)):
            add(Finding("WARN", "StorageUnit", name,
                        "full-year run without cyclic_state_of_charge"))

    # ---------------- lines ----------------
    for name, ln in n.lines.iterrows():
        if float(ln.get("x", 0)) == 0:
            add(Finding("ERROR", "Line", name, "zero reactance breaks load flow"))
        if float(ln.get("s_nom", 0)) == 0 and not bool(ln.get("s_nom_extendable", False)):
            add(Finding("WARN", "Line", name, "s_nom == 0 and not extendable"))

    # ---------------- carriers / CO2 ----------------
    if "co2_emissions" in n.carriers.columns:
        for name, c in n.carriers.iterrows():
            if _match(name, FOSSIL_KEYWORDS) and float(c.get("co2_emissions", 0)) <= 0:
                add(Finding("WARN", "Carrier", name,
                            "fossil carrier with co2_emissions <= 0"))
    else:
        add(Finding("WARN", "Carrier", "-",
                    "no co2_emissions column on carriers - emissions unaccounted"))

    # ---------------- CO2-chain accounting ----------------
    # GlobalConstraints count carrier co2_emissions for Generators (and
    # Store/StorageUnit state) but NOT for Link conversion flows - the reason
    # PyPSA-Eur uses explicit co2 buses for CCS/DAC/synfuels.
    co2_bus_exists = any(_match(c, ["co2"]) for c in n.buses.carrier.astype(str))
    if not co2_bus_exists:
        emis = (n.carriers["co2_emissions"]
                if "co2_emissions" in n.carriers.columns else None)

        def _carrier_emissions(carrier) -> float:
            if emis is None or carrier not in emis.index:
                return 0.0
            return float(emis[carrier])

        for comp, df, escape_ok in [("Generator", n.generators, True),
                                    ("Store", n.stores, True),
                                    ("StorageUnit", n.storage_units, True),
                                    ("Link", n.links, False)]:
            for name, row in df.iterrows():
                if not _match(row.carrier, CO2_CHAIN_KEYWORDS):
                    continue
                if escape_ok and _carrier_emissions(row.carrier) != 0.0:
                    continue  # counted by GlobalConstraints for this component type
                if escape_ok:
                    msg = ("CO2-chain tech without explicit co2 bus or carrier "
                           "co2_emissions - carbon-neutral import assumption? state it")
                else:
                    msg = ("CO2-chain Link without explicit co2 bus - carrier "
                           "co2_emissions on a Link is NOT counted by "
                           "GlobalConstraints; use an explicit co2 bus")
                add(Finding("WARN", comp, name, msg))

    # ---------------- heat bus carrier mixing ----------------
    if not n.loads.empty and "carrier" in n.loads.columns:
        heat_loads = n.loads[
            n.loads.carrier.astype(str).str.lower().str.contains("heat")]
        for bus, grp in heat_loads.groupby("bus"):
            carriers = set(grp.carrier.astype(str)) - {""}
            if len(carriers) > 1:
                add(Finding("WARN", "Bus", bus,
                            f"{len(carriers)} distinct heat load carriers on one bus"
                            " - same temperature level? mixing process heat with"
                            " space heat flattens COP/efficiency"))

    # ---------------- time accounting ----------------
    w = n.snapshot_weightings
    if len(n.snapshots) and not (w.objective.equals(w.generators)
                                 and w.objective.equals(w.stores)):
        add(Finding("WARN", "Snapshots", "-",
                    "weighting columns differ (objective|generators|stores) -"
                    " intended? generators drives CO2 accounting, stores drives"
                    " storage physics"))

    # ---------------- loads ----------------
    # load carrier vs bus carrier mismatch (heat demand on AC bus etc.);
    # only fires when BOTH carriers are non-empty and share no substring
    if "carrier" in n.loads.columns:
        for name, ld in n.loads.iterrows():
            lc = str(ld.get("carrier", "")).strip().lower()
            bc = str(n.buses.carrier.get(ld.bus, "")).strip().lower()
            if lc and bc and lc not in bc and bc not in lc:
                add(Finding("WARN", "Load", name,
                            f"carrier '{lc}' on bus carrier '{bc}' -"
                            " demand on the wrong bus?"))
    for name in n.loads.index:
        series = n.loads_t.p_set.get(name) if name in getattr(
            n.loads_t, "p_set", {}) else None
        static = float(n.loads.at[name, "p_set"]) if "p_set" in n.loads.columns else 0.0
        if (series is None and static == 0.0) or (
                series is not None and float(series.abs().sum()) == 0.0):
            add(Finding("WARN", "Load", name, "load is identically zero"))

    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("network", help="path to .nc file or CSV folder")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    args = ap.parse_args()

    import pypsa  # late import so --help works anywhere

    n = pypsa.Network(args.network)
    findings = validate(n)

    errors = [x for x in findings if x.severity == "ERROR"]
    warns = [x for x in findings if x.severity == "WARN"]
    for x in errors + warns:
        print(x.line())
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s) "
          f"across {len(n.buses)} buses / {len(n.snapshots)} snapshots.")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
