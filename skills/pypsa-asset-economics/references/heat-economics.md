# Heat economics

## Heat pump vs gas boiler dispatch
- break-even power price P_el* = COP * (P_gas + EF * CO2price) / eta_boiler — EF in t/MWh_thermal (suite convention), so the CO2 term sits INSIDE the /eta. ! leaving CO2 outside understates break-even ~5-6 EUR/MWh_el at EF 0.2, 80 EUR/t, eta 0.9, COP 3.
- time-varying COP -> break-even moves hourly.
- realistic industrial setup = dual-fuel bus (HP + boiler + TES) -> let model switch, REPORT: run-hours.

## Tariff reality
- retail/industrial power price = wholesale + grid fees + levies.
- ! bare wholesale flatters heat pumps. APPLY: uplift constant | tariff series. DOCUMENT: it.

## TES value in heat systems
- TES monetizes price spreads via heat side (charge resistive/HP at cheap hours).
- value anchors to spread statistics like BESS; thermal standing losses + lower cost per MWh -> longer durations economic.
- CHECK: standing_loss realistic (physical-realism ranges-storage.md) before quoting seasonal TES business cases.

## District heating
- heat sale price often regulated/contracted -> MODEL: heat revenue as exogenous price on delivered heat, not dual.
- ! DH marginal duals from cost-min run are NOT tariffs.
