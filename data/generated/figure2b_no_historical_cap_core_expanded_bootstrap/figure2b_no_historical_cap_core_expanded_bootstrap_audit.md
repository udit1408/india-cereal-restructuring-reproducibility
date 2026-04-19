# Figure 2(b) approved expanded bootstrap audit

This rebuild extends the district-input bootstrap on the approved
Figure 2(b) branch by perturbing both the optimization
coefficients and the downstream environmental translation coefficients
available in the prepared seasonal panels.

Perturbed raw-panel coefficients and mapped model fields:
- `CWR m3/ha` -> `water_rate` (delta)
- `net_N_applied(kg/ha)` -> `nitrogen_rate` (delta)
- `net_P_applied(kg/ha)` -> `p_rate` (delta)
- `n_removed_rate` -> `n_removed_rate` (ratio)
- `p_removed_rate` -> `p_removed_rate` (ratio)
- `fn2o` -> `n_emission_rate` (ratio)
- `fno3` -> `n_leach_rate` (ratio)

All perturbations are centered on the prepared 2017 coefficient fields.
For `delta` specifications, the sampled deviation from the empirical pool mean is added to the
prepared 2017 value. For `ratio` specifications, the prepared 2017 value is multiplied by the
sample-to-mean ratio from the empirical pool.

Bootstrap iterations requested: 300
Elapsed time (s): 44.75

## Deterministic reproduction check

- Nitrogen based | Nitrogen Emission: reproduced 22.336%, center 22.336%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Emission: reproduced 13.642%, center 13.642%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Leach: reproduced 19.598%, center 19.598%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Leach: reproduced 11.638%, center 11.638%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Greenhouse Gas emission: reproduced 29.408%, center 29.408%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Greenhouse Gas emission: reproduced 41.794%, center 41.794%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Profit: reproduced -17.253%, center -17.253%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Profit: reproduced -23.133%, center -23.133%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Calorie: reproduced -1.102%, center -1.102%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Calorie: reproduced -4.156%, center -4.156%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus application: reproduced 14.876%, center 14.876%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus application: reproduced 9.376%, center 9.376%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen application: reproduced 13.696%, center 13.696%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen application: reproduced 7.539%, center 7.539%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus Surplus: reproduced 19.966%, center 19.966%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus Surplus: reproduced 14.024%, center 14.024%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Surplus: reproduced 21.408%, center 21.408%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Surplus: reproduced 12.957%, center 12.957%, delta -0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Water Demand: reproduced 36.257%, center 36.257%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Water Demand: reproduced 44.493%, center 44.493%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)

## Bootstrap feasibility

- Nitrogen based | Optimal: 300
- Water based | Optimal: 300

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 22.336%, mean 21.288%, 95% CI [20.208, 22.411]%, optimal 300/300
- Water based | Nitrogen Emission: center 13.642%, mean 6.729%, 95% CI [4.813, 8.759]%, optimal 300/300
- Nitrogen based | Nitrogen Leach: center 19.598%, mean 18.328%, 95% CI [16.886, 19.859]%, optimal 300/300
- Water based | Nitrogen Leach: center 11.638%, mean 5.391%, 95% CI [3.586, 7.369]%, optimal 300/300
- Nitrogen based | Greenhouse Gas emission: center 29.408%, mean 28.846%, 95% CI [26.777, 30.507]%, optimal 300/300
- Water based | Greenhouse Gas emission: center 41.794%, mean 39.439%, 95% CI [37.776, 40.805]%, optimal 300/300
- Nitrogen based | Profit: center -17.253%, mean -18.425%, 95% CI [-21.387, -14.468]%, optimal 300/300
- Water based | Profit: center -23.133%, mean -18.096%, 95% CI [-21.904, -14.226]%, optimal 300/300
- Nitrogen based | Calorie: center -1.102%, mean -2.394%, 95% CI [-3.167, -1.546]%, optimal 300/300
- Water based | Calorie: center -4.156%, mean -4.095%, 95% CI [-5.083, -3.022]%, optimal 300/300
- Nitrogen based | Phosphorus application: center 14.876%, mean 12.537%, 95% CI [10.936, 14.060]%, optimal 300/300
- Water based | Phosphorus application: center 9.376%, mean 5.057%, 95% CI [3.093, 6.961]%, optimal 300/300
- Nitrogen based | Nitrogen application: center 13.696%, mean 12.412%, 95% CI [11.646, 13.244]%, optimal 300/300
- Water based | Nitrogen application: center 7.539%, mean 2.809%, 95% CI [1.476, 4.219]%, optimal 300/300
- Nitrogen based | Phosphorus Surplus: center 19.966%, mean 17.522%, 95% CI [15.483, 19.536]%, optimal 300/300
- Water based | Phosphorus Surplus: center 14.024%, mean 8.703%, 95% CI [6.199, 11.030]%, optimal 300/300
- Nitrogen based | Nitrogen Surplus: center 21.408%, mean 20.424%, 95% CI [19.315, 21.587]%, optimal 300/300
- Water based | Nitrogen Surplus: center 12.957%, mean 6.287%, 95% CI [4.428, 8.288]%, optimal 300/300
- Nitrogen based | Water Demand: center 36.257%, mean 27.451%, 95% CI [17.055, 33.174]%, optimal 300/300
- Water based | Water Demand: center 44.493%, mean 46.172%, 95% CI [44.798, 47.523]%, optimal 300/300
