# Power-flow feasibility checks

PyPSA 1.0.x. `n.optimize()` = LINEARIZED OPF: MW only, lossless -> optimal dispatch can be AC-infeasible (voltage | reactive | losses ignored). This file = post-solve electrical sanity + the escalation boundary.

## Applicability gate - CHECK in order, before any pf

1. multi-bus AC sub-network exists? Link-only | single-bus model (typical sector-coupled) -> no KVL anywhere -> file inapplicable, stop.
2. real per-line impedances + correct v_nom? Clustered/zonal model (PyPSA-Eur default) -> equivalent impedances -> NR voltage + reactive-loading numbers not credible -> only step-7 transfer-consistency check applies.
3. expansion run? pf uses PRE-expansion x (s_nom_opt does NOT update impedance) -> expanded-branch results unphysical unless impedance iterated.
4. mixed AC+DC network? detect via `n.buses.carrier` (! `n.lines.carrier` stays "AC" even on DC-bus lines) -> whole-network `m.pf()` crashes on 1.0.x (AttributeError: 'SubNetwork' object has no attribute 'Y') -> USE: step 5b per-sub-network path.

Gates 1-3 fail -> model cannot answer voltage questions. STATE: which gate failed + why -> Boundary section. Do NOT produce numbers anyway.

## Recipe - AC feasibility of an optimized dispatch (verified PyPSA 1.0.7)

1. `n.model.solver_model = None`  # ! n.copy() of a solved network raises ValueError otherwise.
2. `m = n.copy()`
3. dispatch -> setpoints: `m.generators_t.p_set = n.generators_t.p` | `m.storage_units_t.p_set = n.storage_units_t.p` | ! `m.links_t.p_set = n.links_t.p0` - pf reads Link p_set ONLY; omit -> HVDC | converters | battery links silently revert to 0 | Stores on AC buses: `m.stores_t.p_set = n.stores_t.p`.
4. reactive support (defaults = all-PQ generators + q=0 loads -> NR diverges, singular matrix):
- SET: `m.generators.control = "PV"` - ALL generators, screening assumption (matches PyPSA's own SciGRID example); pf auto-promotes one generator per sub-network to slack.
- SET: `m.loads_t.q_set = m.get_switchable_as_dense("Load", "p_set") * np.tan(np.arccos(0.95))` (cos phi 0.95 | jurisdiction value). ! plain `m.loads_t.p_set * ...` = silent no-op on static-p_set loads (loads_t.p_set empty).
- STATE: both assumptions in every report.
5. `res = m.pf(distribute_slack=True)` -> gate ALL screens on `res["converged"].all().all()`.
- ! distribute_slack required: single slack absorbs ALL network losses (SciGRID: ~1-1.9 GW onto one bus -> loading 1.77 artifact on adjacent lines).
- ! all-zero generator p_set in a sub-network -> exactly singular Jacobian -> converged=False w/ only a MatrixRankWarning -> retry `slack_weights="p_nom"`.
- ! unconverged -> v_mag_pu = NaN + last-iterate garbage -> any screen output meaningless.

5b. mixed AC+DC (gate 4): `m.determine_network_topology()` (needed - post-optimize sub_networks table can be stale; idempotent) -> per sub-network sn w/ carrier "AC" AND `len(sn.components.buses.static) > 1`: `n_iter, error, converged = sn.pf(distribute_slack=True)` -> gate on `converged.all()` (Series - single .all()). Single-bus AC sub-networks (converter-fed) -> sn.pf() ALSO crashes -> skip; their balance already enforced by optimize. ! DC lines keep their LOPF flows (5b refreshes AC only) -> exactly-1.000 loading on a DC line = copied LOPF binding, not a pf result.

6. screens (converged only):
- voltage: v_mag_pu outside 0.95-1.05 = screening bound, NOT compliance (EN 50160 +-10% LV/MV | ANSI C84.1 +-5% | TSO grid codes differ by voltage level). ! PV buses pinned at v_mag_pu_set -> voltage numbers conditional on step-4 assumptions; meaningless w/o them.
- loading = max-end apparent power `max(sqrt(p0^2+q0^2), sqrt(p1^2+q1^2)) / rating` | rating = s_nom_opt where s_nom_extendable else s_nom (! optimize() leaves s_nom untouched -> s_nom base = dead screen on expansion runs). LOPF capped MW flow at s_max_pu*s_nom (N-1 proxy - owner: ranges-grid.md) -> AC loading in (s_max_pu..1.0]*s_nom = expected (losses + reactive); >1.0 = finding.
- reactive: ! pf has NO PV->PQ switching - generator Q limits ignored + components carry no capability fields -> CHECK: |m.generators_t.q| vs reactive screening bound (owner: ranges-generation.md Red flags): |q| <= tan(acos(PF))*p_nom; PF 0.95 -> 0.33*p_nom | PF 0.85 -> 0.62*p_nom.

7. `m.lpf()` = DC flow, same p_set mechanism (step 3 still required). ! NOT independent physics: same B-theta system + same x as LOPF -> reproduces LOPF flows by construction -> value = TRANSFER-CONSISTENCY check (catches setpoint-transfer bugs, e.g. forgotten links_t.p_set -> nonzero p0 mismatch). Clustered models (gate 2): this is the only check available; no AC statement possible - STATE that limitation.

## Remediate in-suite BEFORE escalating

- loading > 1.0 after lossless OPF -> re-solve w/ `optimize(transmission_losses=3)` (pypsa-solve-and-debug) + check s_max_pu margin (ranges-grid.md) -> re-screen.
- divergence after step 4 -> data problem first: zero-impedance lines | orphan buses (RUN: validator) | missing v_nom.

## Boundary - what PyPSA cannot answer [owner of this fact]

- reactive mitigation | voltage control design | protection | dynamics/stability | distribution feeders | tap + shunt automation = NOT PyPSA -> AC-tool classes: pandapower | PSS/E | ANDES | OpenDSS.
- handoff artifact = violating numbers + assumptions: bus + v_mag_pu | element + loading | control / power-factor / slack assumptions from steps 4-5. ! numbers w/o assumptions overstate fidelity.
