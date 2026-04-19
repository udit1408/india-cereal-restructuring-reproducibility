# Figure 2(b) whisker rebuild audit

This rebuild keeps the deterministic bar centers anchored to the existing endpoint CSVs in
`revision_2/_audit/Nitrogen-Surplus-restructuring/generated/`.

The whiskers are rebuilt from a joint historical bootstrap over the seasonal prepared panels,
sampling three environmental intensity coefficients within crop histories:

- `CWR m3/ha`
- `net_N_applied(kg/ha)`
- `net_P_applied(kg/ha)`

The bootstrap is centered on the prepared 2017 coefficients, so each draw perturbs the published
endpoint locally rather than replacing it with the long-run historical mean. The calorie and
farmer-income constraint coefficients remain fixed at the prepared 2017 values, which preserves
the manuscript's optimization structure and avoids turning the panel into a different yield- or
price-uncertainty experiment.

Bootstrap iterations requested: 100
Elapsed time (s): 23.13

## Deterministic reproduction check

- Nitrogen based | Nitrogen Emission: reproduced 23.717%, existing 22.366%, delta 1.351 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Emission: reproduced 14.496%, existing 12.300%, delta 2.196 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Leach: reproduced 21.239%, existing 18.621%, delta 2.618 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Leach: reproduced 12.789%, existing 9.370%, delta 3.419 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Greenhouse Gas emission: reproduced 30.083%, existing 27.932%, delta 2.151 pp (kharif:Optimal;rabi:Optimal)
- Water based | Greenhouse Gas emission: reproduced 42.771%, existing 40.106%, delta 2.666 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Profit: reproduced -4.600%, existing -7.813%, delta 3.212 pp (kharif:Optimal;rabi:Optimal)
- Water based | Profit: reproduced -19.370%, existing -23.783%, delta 4.413 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Calorie: reproduced -0.645%, existing -2.410%, delta 1.765 pp (kharif:Optimal;rabi:Optimal)
- Water based | Calorie: reproduced -3.607%, existing -6.533%, delta 2.927 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus application: reproduced 16.529%, existing 14.951%, delta 1.578 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus application: reproduced 10.412%, existing 7.955%, delta 2.458 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen application: reproduced 15.057%, existing 13.444%, delta 1.613 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen application: reproduced 8.443%, existing 5.992%, delta 2.450 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus Surplus: reproduced 21.835%, existing 20.295%, delta 1.540 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus Surplus: reproduced 15.137%, existing 12.772%, delta 2.364 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Surplus: reproduced 22.813%, existing 21.243%, delta 1.570 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Surplus: reproduced 13.837%, existing 11.455%, delta 2.382 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Water Demand: reproduced 36.758%, existing 35.340%, delta 1.417 pp (kharif:Optimal;rabi:Optimal)
- Water based | Water Demand: reproduced 45.284%, existing 43.377%, delta 1.907 pp (kharif:Optimal;rabi:Optimal)

## Bootstrap feasibility

- Nitrogen based | Optimal: 100
- Water based | Optimal: 100

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 22.366%, mean 23.834%, 95% CI [22.650, 24.960]%, optimal 100/100
- Water based | Nitrogen Emission: center 12.300%, mean 9.739%, 95% CI [7.653, 12.145]%, optimal 100/100
- Nitrogen based | Nitrogen Leach: center 18.621%, mean 21.686%, 95% CI [20.501, 23.132]%, optimal 100/100
- Water based | Nitrogen Leach: center 9.370%, mean 8.693%, 95% CI [6.607, 10.799]%, optimal 100/100
- Nitrogen based | Greenhouse Gas emission: center 27.932%, mean 28.905%, 95% CI [27.234, 30.481]%, optimal 100/100
- Water based | Greenhouse Gas emission: center 40.106%, mean 39.801%, 95% CI [38.458, 41.314]%, optimal 100/100
- Nitrogen based | Profit: center -7.813%, mean -6.321%, 95% CI [-9.739, -2.494]%, optimal 100/100
- Water based | Profit: center -23.783%, mean -14.251%, 95% CI [-18.621, -9.570]%, optimal 100/100
- Nitrogen based | Calorie: center -2.410%, mean -2.354%, 95% CI [-3.133, -1.509]%, optimal 100/100
- Water based | Calorie: center -6.533%, mean -3.976%, 95% CI [-4.875, -2.979]%, optimal 100/100
- Nitrogen based | Phosphorus application: center 14.951%, mean 14.583%, 95% CI [13.200, 16.069]%, optimal 100/100
- Water based | Phosphorus application: center 7.955%, mean 5.469%, 95% CI [3.628, 7.398]%, optimal 100/100
- Nitrogen based | Nitrogen application: center 13.444%, mean 14.086%, 95% CI [13.352, 14.790]%, optimal 100/100
- Water based | Nitrogen application: center 5.992%, mean 3.232%, 95% CI [1.831, 4.730]%, optimal 100/100
- Nitrogen based | Phosphorus Surplus: center 20.295%, mean 19.975%, 95% CI [18.331, 21.854]%, optimal 100/100
- Water based | Phosphorus Surplus: center 12.772%, mean 9.106%, 95% CI [6.761, 11.693]%, optimal 100/100
- Nitrogen based | Nitrogen Surplus: center 21.243%, mean 22.469%, 95% CI [21.296, 23.632]%, optimal 100/100
- Water based | Nitrogen Surplus: center 11.455%, mean 6.530%, 95% CI [4.251, 8.953]%, optimal 100/100
- Nitrogen based | Water Demand: center 35.340%, mean 28.403%, 95% CI [17.729, 33.828]%, optimal 100/100
- Water based | Water Demand: center 43.377%, mean 47.109%, 95% CI [45.654, 48.342]%, optimal 100/100
