# Figure 2(b) clean method-consistent whisker rebuild audit

This rebuild uses clean, method-consistent deterministic centers rather than anchoring to the
legacy endpoint CSVs. The optimization is solved directly from notebook-prepared inputs while
enforcing unchanged district cropped area, state calorie constraints, state profit constraints
where applicable, restriction to historically grown crops, and district-crop historical max-area caps.

The whiskers are rebuilt from a joint historical bootstrap over the seasonal prepared panels,
sampling three environmental intensity coefficients within crop histories:

- `CWR m3/ha`
- `net_N_applied(kg/ha)`
- `net_P_applied(kg/ha)`

The bootstrap is centered on the prepared 2017 coefficients, so each draw perturbs the method-consistent
endpoint locally rather than replacing it with the long-run historical mean. The calorie and
farmer-income constraint coefficients remain fixed at the prepared 2017 values, which preserves
the manuscript's optimization structure and avoids turning the panel into a different yield- or
price-uncertainty experiment.

Bootstrap iterations requested: 100
Elapsed time (s): 16.71

## Clean-vs-legacy deterministic comparison

- Nitrogen based | Nitrogen Emission: clean 100.000%, legacy 22.366%, delta 77.634 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Nitrogen Emission: clean 100.000%, legacy 12.300%, delta 87.700 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Nitrogen Leach: clean 100.000%, legacy 18.621%, delta 81.379 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Nitrogen Leach: clean 100.000%, legacy 9.370%, delta 90.630 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Greenhouse Gas emission: clean 100.000%, legacy 27.932%, delta 72.068 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Greenhouse Gas emission: clean 100.000%, legacy 40.106%, delta 59.894 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Profit: clean 100.000%, legacy -7.813%, delta 107.813 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Profit: clean 100.000%, legacy -23.783%, delta 123.783 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Calorie: clean 100.000%, legacy -2.410%, delta 102.410 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Calorie: clean 100.000%, legacy -6.533%, delta 106.533 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Phosphorus application: clean 100.000%, legacy 14.951%, delta 85.049 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Phosphorus application: clean 100.000%, legacy 7.955%, delta 92.045 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Nitrogen application: clean 100.000%, legacy 13.444%, delta 86.556 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Nitrogen application: clean 100.000%, legacy 5.992%, delta 94.008 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Phosphorus Surplus: clean 100.000%, legacy 20.295%, delta 79.705 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Phosphorus Surplus: clean 100.000%, legacy 12.772%, delta 87.228 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Nitrogen Surplus: clean 100.000%, legacy 21.243%, delta 78.757 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Nitrogen Surplus: clean 100.000%, legacy 11.455%, delta 88.545 pp (kharif:Infeasible;rabi:Infeasible)
- Nitrogen based | Water Demand: clean 100.000%, legacy 35.340%, delta 64.660 pp (kharif:Infeasible;rabi:Infeasible)
- Water based | Water Demand: clean 100.000%, legacy 43.377%, delta 56.623 pp (kharif:Infeasible;rabi:Infeasible)

## Bootstrap feasibility

- Nitrogen based | Infeasible: 100
- Water based | Infeasible: 100

## Summary by metric

- Nitrogen based | Nitrogen Emission: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Nitrogen Emission: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Nitrogen Leach: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Nitrogen Leach: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Greenhouse Gas emission: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Greenhouse Gas emission: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Profit: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Profit: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Calorie: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Calorie: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Phosphorus application: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Phosphorus application: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Nitrogen application: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Nitrogen application: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Phosphorus Surplus: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Phosphorus Surplus: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Nitrogen Surplus: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Nitrogen Surplus: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Nitrogen based | Water Demand: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
- Water based | Water Demand: center 100.000%, mean nan%, 95% CI [nan, nan]%, optimal 0/100
