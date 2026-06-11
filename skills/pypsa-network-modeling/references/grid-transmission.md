# Grid and transmission representation

## Line (AC, impedance-based)

- SET `x` (+ ideally `r`) in Ohm | `x_pu`. ! Zero reactance breaks load-flow formulation.
- `s_nom` = MVA. `s_max_pu` (e.g. 0.7) ~ N-1 security margin.
- Buses of different v_nom -> Transformer, not direct Line.
- LOPF: AC lines obey Kirchhoff voltage law (cycle constraints) -> flows NOT freely controllable. Controllable flow -> Link.
- `s_nom_extendable=True` -> nonconvex in theory (impedance varies with capacity); PyPSA linearizes. Serious TEP -> discrete candidate lines | iterate impedance updates.

## Link (DC | controllable | cross-carrier)

- HVDC: Link, efficiency ~0.97, `p_min_pu=-1` for bidirectional.
- ! `p_min_pu=-1` -> SAME efficiency both directions -> physically wrong for lossy converters. Loss direction matters -> USE two anti-parallel links.

## Transformers

- USE standard-types library type | explicit s_nom + impedance.
- Step-up transformers: keep for nodal studies | aggregate away for zonal -> record decision (pypsa-market-design).

## Aggregation

- Clustering buses (k-means|HAC, `pypsa.clustering.spatial`) changes line impedances -> can flip congestion results.
- Aggregation acceptability = market-design question -> READ pypsa-market-design SKILL.md before merging buses.
