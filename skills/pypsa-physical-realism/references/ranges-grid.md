# Screening ranges - grid

- AC line reactance: never 0. 380 kV OHL x ~0.25-0.35 Ohm/km | r/x ~ 0.05-0.15.
- s_max_pu 0.6-0.8 = N-1 proxy in zonal/nodal planning. 1.0 = security margins ignored -> OK for screening, state it.
- transformers between unequal v_nom buses: mandatory in nodal models.
- HVDC link efficiency 0.95-0.985 (converter pair + cable). ! Lossless 2000 km link -> flag.
- bidirectional lossy links via p_min_pu=-1 -> loss applied WRONG direction for reverse flow. USE: anti-parallel link pairs when it matters.
- distribution-level study in transmission tool -> losses 2-6% as link efficiency | load uplift. Document which.
- line capital cost (HVAC overhead) ~ annualized 40-110 EUR/MW/km/a (overnight ~750 EUR/MW/km, DEA via technology-data) | underground cables 5-10x.
- underground HVDC vs OHL cost ratio drives expansion results -> cite assumption.
