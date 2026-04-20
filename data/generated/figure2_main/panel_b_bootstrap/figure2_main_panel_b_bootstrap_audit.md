# figure2_main panel b bootstrap audit

This bootstrap adds whiskers to the primary Figure 2(b) rebuild under the 2017-18 realized-price benchmark.
The revenue benchmark is held fixed across iterations. Uncertainty is propagated by resampling
district-level historical coefficient fields for water demand, nitrogen application, and phosphorus
application in the same style as the primary Figure 2(b) whisker workflow.

This means the whiskers reflect optimization sensitivity to agronomic coefficient variation under
the realized-price benchmark, rather than a second ad hoc uncertainty model for realized prices.

Bootstrap iterations requested: 500
Elapsed time (s): 79.06

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

- Nitrogen based | Optimal: 500
- Water based | Optimal: 500

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 17.800%, mean 19.759%, 95% CI [18.653, 20.926]%, optimal 500/500
- Water based | Nitrogen Emission: center 7.391%, mean 6.771%, 95% CI [4.909, 8.594]%, optimal 500/500
- Nitrogen based | Nitrogen Leach: center 19.798%, mean 21.478%, 95% CI [20.242, 22.790]%, optimal 500/500
- Water based | Nitrogen Leach: center 9.972%, mean 9.410%, 95% CI [7.639, 11.229]%, optimal 500/500
- Nitrogen based | Greenhouse Gas emission: center 24.672%, mean 23.048%, 95% CI [21.217, 24.706]%, optimal 500/500
- Water based | Greenhouse Gas emission: center 31.117%, mean 29.954%, 95% CI [29.121, 30.679]%, optimal 500/500
- Nitrogen based | Profit: center -3.625%, mean -2.797%, 95% CI [-4.326, -1.486]%, optimal 500/500
- Water based | Profit: center -3.412%, mean -2.244%, 95% CI [-3.449, -0.692]%, optimal 500/500
- Nitrogen based | Calorie: center -5.182%, mean -4.668%, 95% CI [-5.487, -3.933]%, optimal 500/500
- Water based | Calorie: center -8.442%, mean -7.229%, 95% CI [-8.028, -6.248]%, optimal 500/500
- Nitrogen based | Phosphorus application: center 8.414%, mean 9.318%, 95% CI [7.439, 11.019]%, optimal 500/500
- Water based | Phosphorus application: center 1.845%, mean 2.610%, 95% CI [0.534, 4.639]%, optimal 500/500
- Nitrogen based | Nitrogen application: center 9.684%, mean 11.147%, 95% CI [10.479, 11.888]%, optimal 500/500
- Water based | Nitrogen application: center 1.905%, mean 1.875%, 95% CI [0.686, 3.163]%, optimal 500/500
- Nitrogen based | Phosphorus Surplus: center 13.023%, mean 13.935%, 95% CI [11.629, 16.083]%, optimal 500/500
- Water based | Phosphorus Surplus: center 5.682%, mean 6.287%, 95% CI [3.640, 8.848]%, optimal 500/500
- Nitrogen based | Nitrogen Surplus: center 17.621%, mean 19.520%, 95% CI [18.459, 20.661]%, optimal 500/500
- Water based | Nitrogen Surplus: center 7.486%, mean 6.881%, 95% CI [5.080, 8.649]%, optimal 500/500
- Nitrogen based | Water Demand: center 25.527%, mean 24.074%, 95% CI [20.137, 27.345]%, optimal 500/500
- Water based | Water Demand: center 35.698%, mean 37.542%, 95% CI [36.395, 38.672]%, optimal 500/500
