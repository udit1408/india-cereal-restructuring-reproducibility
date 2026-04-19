# Figure 2(b) approved core whisker audit

This rebuild adds whiskers to the approved Figure 2(b) branch used in the current release.
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

Bootstrap iterations requested: 500
Elapsed time (s): 75.22

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
- Nitrogen based | Phosphorus application: reproduced 11.125%, center 11.125%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus application: reproduced 5.114%, center 5.114%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen application: reproduced 10.807%, center 10.807%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen application: reproduced 3.063%, center 3.063%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus Surplus: reproduced 17.247%, center 17.247%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus Surplus: reproduced 10.481%, center 10.481%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Surplus: reproduced 20.040%, center 20.040%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Surplus: reproduced 9.249%, center 9.249%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Water Demand: reproduced 31.907%, center 31.907%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Water Demand: reproduced 42.890%, center 42.890%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)

## Bootstrap feasibility

- Nitrogen based | Optimal: 500
- Water based | Optimal: 500

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 20.190%, mean 22.353%, 95% CI [21.339, 23.518]%, optimal 500/500
- Water based | Nitrogen Emission: center 9.187%, mean 8.052%, 95% CI [6.027, 10.072]%, optimal 500/500
- Nitrogen based | Nitrogen Leach: center 22.526%, mean 24.432%, 95% CI [23.130, 25.795]%, optimal 500/500
- Water based | Nitrogen Leach: center 10.976%, mean 10.006%, 95% CI [8.152, 11.982]%, optimal 500/500
- Nitrogen based | Greenhouse Gas emission: center 39.711%, mean 38.574%, 95% CI [36.457, 40.610]%, optimal 500/500
- Water based | Greenhouse Gas emission: center 54.017%, mean 51.876%, 95% CI [50.681, 53.070]%, optimal 500/500
- Nitrogen based | Profit: center -17.910%, mean -17.447%, 95% CI [-21.111, -13.957]%, optimal 500/500
- Water based | Profit: center -16.226%, mean -15.554%, 95% CI [-19.346, -11.568]%, optimal 500/500
- Nitrogen based | Calorie: center -6.055%, mean -5.238%, 95% CI [-6.064, -4.333]%, optimal 500/500
- Water based | Calorie: center -8.103%, mean -7.359%, 95% CI [-8.126, -6.375]%, optimal 500/500
- Nitrogen based | Phosphorus application: center 11.125%, mean 11.822%, 95% CI [10.019, 13.521]%, optimal 500/500
- Water based | Phosphorus application: center 5.114%, mean 5.737%, 95% CI [3.423, 7.721]%, optimal 500/500
- Nitrogen based | Nitrogen application: center 10.807%, mean 12.413%, 95% CI [11.747, 13.169]%, optimal 500/500
- Water based | Nitrogen application: center 3.063%, mean 2.618%, 95% CI [1.244, 3.957]%, optimal 500/500
- Nitrogen based | Phosphorus Surplus: center 17.247%, mean 17.882%, 95% CI [15.588, 19.993]%, optimal 500/500
- Water based | Phosphorus Surplus: center 10.481%, mean 11.004%, 95% CI [8.096, 13.510]%, optimal 500/500
- Nitrogen based | Nitrogen Surplus: center 20.040%, mean 22.130%, 95% CI [21.129, 23.289]%, optimal 500/500
- Water based | Nitrogen Surplus: center 9.249%, mean 8.155%, 95% CI [6.151, 10.146]%, optimal 500/500
- Nitrogen based | Water Demand: center 31.907%, mean 30.291%, 95% CI [26.788, 33.456]%, optimal 500/500
- Water based | Water Demand: center 42.890%, mean 44.683%, 95% CI [43.745, 45.521]%, optimal 500/500
