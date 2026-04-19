# Figure2_equivalent panel b bootstrap audit

This bootstrap adds whiskers to the primary Figure 2(b) rebuild built with the hybrid 2017-18 realized-price benchmark.
The revenue benchmark is held fixed across iterations. Uncertainty is propagated by resampling
district-level historical coefficient fields for water demand, nitrogen application, and phosphorus
application in the same style as the primary Figure 2(b) whisker workflow.

This means the whiskers reflect optimization sensitivity to agronomic coefficient variation under
the realized-price benchmark, rather than a second ad hoc uncertainty model for realized prices.

Bootstrap iterations requested: 5
Elapsed time (s): 0.95

## Deterministic reproduction check

- Nitrogen based | Nitrogen Emission: reproduced 17.800%, center 17.800%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Emission: reproduced 7.391%, center 7.391%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Leach: reproduced 19.798%, center 19.798%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Leach: reproduced 9.972%, center 9.972%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Greenhouse Gas emission: reproduced 24.672%, center 24.672%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Greenhouse Gas emission: reproduced 31.117%, center 31.117%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Profit: reproduced -3.625%, center -3.625%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Profit: reproduced -3.412%, center -3.412%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Calorie: reproduced -5.182%, center -5.182%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Calorie: reproduced -8.442%, center -8.442%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus application: reproduced 8.414%, center 8.414%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus application: reproduced 1.845%, center 1.845%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen application: reproduced 9.684%, center 9.684%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen application: reproduced 1.905%, center 1.905%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Phosphorus Surplus: reproduced 13.023%, center 13.023%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Phosphorus Surplus: reproduced 5.682%, center 5.682%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Nitrogen Surplus: reproduced 17.621%, center 17.621%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Nitrogen Surplus: reproduced 7.486%, center 7.486%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Nitrogen based | Water Demand: reproduced 25.527%, center 25.527%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)
- Water based | Water Demand: reproduced 35.698%, center 35.698%, delta 0.000 pp (kharif:Optimal;rabi:Optimal)

## Bootstrap feasibility

- Nitrogen based | Optimal: 5
- Water based | Optimal: 5

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 17.800%, mean 20.761%, 95% CI [19.701, 21.457]%, optimal 5/5
- Water based | Nitrogen Emission: center 7.391%, mean 5.910%, 95% CI [4.767, 7.134]%, optimal 5/5
- Nitrogen based | Nitrogen Leach: center 19.798%, mean 23.108%, 95% CI [21.582, 24.185]%, optimal 5/5
- Water based | Nitrogen Leach: center 9.972%, mean 9.232%, 95% CI [8.194, 10.217]%, optimal 5/5
- Nitrogen based | Greenhouse Gas emission: center 24.672%, mean 22.288%, 95% CI [21.821, 22.927]%, optimal 5/5
- Water based | Greenhouse Gas emission: center 31.117%, mean 27.568%, 95% CI [27.229, 28.126]%, optimal 5/5
- Nitrogen based | Profit: center -3.625%, mean -3.710%, 95% CI [-4.892, -2.620]%, optimal 5/5
- Water based | Profit: center -3.412%, mean -1.407%, 95% CI [-2.024, -0.685]%, optimal 5/5
- Nitrogen based | Calorie: center -5.182%, mean -4.550%, 95% CI [-4.738, -4.244]%, optimal 5/5
- Water based | Calorie: center -8.442%, mean -5.810%, 95% CI [-6.606, -4.933]%, optimal 5/5
- Nitrogen based | Phosphorus application: center 8.414%, mean 10.124%, 95% CI [9.074, 11.078]%, optimal 5/5
- Water based | Phosphorus application: center 1.845%, mean 2.759%, 95% CI [2.256, 3.250]%, optimal 5/5
- Nitrogen based | Nitrogen application: center 9.684%, mean 11.828%, 95% CI [11.103, 12.354]%, optimal 5/5
- Water based | Nitrogen application: center 1.905%, mean 1.832%, 95% CI [1.011, 2.679]%, optimal 5/5
- Nitrogen based | Phosphorus Surplus: center 13.023%, mean 14.874%, 95% CI [13.566, 15.978]%, optimal 5/5
- Water based | Phosphorus Surplus: center 5.682%, mean 6.002%, 95% CI [5.220, 6.820]%, optimal 5/5
- Nitrogen based | Nitrogen Surplus: center 17.621%, mean 20.450%, 95% CI [19.374, 21.179]%, optimal 5/5
- Water based | Nitrogen Surplus: center 7.486%, mean 6.035%, 95% CI [4.851, 7.269]%, optimal 5/5
- Nitrogen based | Water Demand: center 25.527%, mean 20.876%, 95% CI [15.002, 24.186]%, optimal 5/5
- Water based | Water Demand: center 35.698%, mean 40.848%, 95% CI [39.943, 41.718]%, optimal 5/5
