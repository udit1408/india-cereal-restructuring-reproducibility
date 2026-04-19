# Figure 2(b) approved core whisker audit

This rebuild adds whiskers to the approved Figure 2(b) branch used in the revised manuscript.
The deterministic bar centers come directly from `figure2b_no_historical_cap_core_values.csv` and therefore
remain aligned with the current state calorie and state profit floors in both seasons.

Each bootstrap iteration draws one shared seasonal perturbation field from the historical prepared panels
and applies it to both endpoint strategies before resolving the optimization. The perturbed coefficients are:

- `CWR m3/ha`
- `net_N_applied(kg/ha)`
- `net_P_applied(kg/ha)`

The bootstrap is centered on the prepared 2017 coefficient fields, so each draw is a local perturbation of
the approved manuscript branch rather than a replacement of the optimization inputs with long-run means.
Calorie and profit constraint coefficients are held fixed at their prepared 2017 values.

Bootstrap iterations requested: 200
Elapsed time (s): 30.74

## Deterministic reproduction check

- Nitrogen based | Nitrogen Emission: reproduced 20.190%, center 20.190%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Emission: reproduced 9.187%, center 9.187%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Leach: reproduced 22.526%, center 22.526%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Leach: reproduced 10.976%, center 10.976%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Greenhouse Gas emission: reproduced 39.711%, center 39.711%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Greenhouse Gas emission: reproduced 54.017%, center 54.017%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Profit: reproduced -17.910%, center -17.910%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Profit: reproduced -16.226%, center -16.226%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Calorie: reproduced -6.055%, center -6.055%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Calorie: reproduced -8.103%, center -8.103%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus application: reproduced 11.125%, center 11.125%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus application: reproduced 5.114%, center 5.114%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen application: reproduced 10.807%, center 10.807%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen application: reproduced 3.063%, center 3.063%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus Surplus: reproduced 17.247%, center 17.247%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus Surplus: reproduced 10.481%, center 10.481%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Surplus: reproduced 20.040%, center 20.040%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Surplus: reproduced 9.249%, center 9.249%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Water Demand: reproduced 31.907%, center 31.907%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Water Demand: reproduced 42.890%, center 42.890%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)

## Bootstrap feasibility

- Nitrogen based | Optimal: 200
- Water based | Optimal: 200

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 20.190%, mean 23.343%, 95% CI [22.162, 24.594]%, optimal 200/200
- Water based | Nitrogen Emission: center 9.187%, mean 6.650%, 95% CI [4.606, 8.638]%, optimal 200/200
- Nitrogen based | Nitrogen Leach: center 22.526%, mean 25.996%, 95% CI [24.728, 27.453]%, optimal 200/200
- Water based | Nitrogen Leach: center 10.976%, mean 9.094%, 95% CI [7.134, 11.059]%, optimal 200/200
- Nitrogen based | Greenhouse Gas emission: center 39.711%, mean 38.254%, 95% CI [36.115, 40.434]%, optimal 200/200
- Water based | Greenhouse Gas emission: center 54.017%, mean 48.796%, 95% CI [47.090, 50.559]%, optimal 200/200
- Nitrogen based | Profit: center -17.910%, mean -17.833%, 95% CI [-21.713, -13.946]%, optimal 200/200
- Water based | Profit: center -16.226%, mean -13.743%, 95% CI [-17.084, -10.214]%, optimal 200/200
- Nitrogen based | Calorie: center -6.055%, mean -5.352%, 95% CI [-6.099, -4.425]%, optimal 200/200
- Water based | Calorie: center -8.103%, mean -6.156%, 95% CI [-7.175, -5.133]%, optimal 200/200
- Nitrogen based | Phosphorus application: center 11.125%, mean 12.428%, 95% CI [10.959, 13.945]%, optimal 200/200
- Water based | Phosphorus application: center 5.114%, mean 5.095%, 95% CI [3.336, 7.037]%, optimal 200/200
- Nitrogen based | Nitrogen application: center 10.807%, mean 13.001%, 95% CI [12.323, 13.798]%, optimal 200/200
- Water based | Nitrogen application: center 3.063%, mean 2.137%, 95% CI [0.721, 3.575]%, optimal 200/200
- Nitrogen based | Phosphorus Surplus: center 17.247%, mean 18.642%, 95% CI [16.797, 20.522]%, optimal 200/200
- Water based | Phosphorus Surplus: center 10.481%, mean 9.765%, 95% CI [7.490, 12.181]%, optimal 200/200
- Nitrogen based | Nitrogen Surplus: center 20.040%, mean 23.014%, 95% CI [21.953, 24.301]%, optimal 200/200
- Water based | Nitrogen Surplus: center 9.249%, mean 6.780%, 95% CI [4.764, 8.626]%, optimal 200/200
- Nitrogen based | Water Demand: center 31.907%, mean 28.012%, 95% CI [17.411, 33.726]%, optimal 200/200
- Water based | Water Demand: center 42.890%, mean 48.180%, 95% CI [46.822, 49.323]%, optimal 200/200
