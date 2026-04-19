# Figure 2(a) clean rebuild

This rebuild uses the single-objective notebook data preparation but replaces the
legacy multi-objective notebook formulation with a clean model that:
- indexes districts jointly by `(state, district)` to avoid duplicate-name collisions,
- restricts reallocation to crops already observed in each district, without imposing crop-specific historical area ceilings,
- normalizes the weighted objective by baseline nitrogen surplus and baseline water demand.
- records solver status explicitly and excludes non-optimal alpha points,
- combines seasons by summing national totals, consistent with the manuscript Methods.

Solver: `highs`
Income constraint: `profit`
Objective mode: `normalized`
Alpha count: 101
Valid combined alphas: 101/101
Combined 2017 baseline nitrogen surplus: 8.285336 Tg N
Combined 2017 baseline water demand: 467.586094 BCM
Baseline cap repairs: not used in this approved branch
Baseline feasibility after repair:
- kharif worst calorie gap=0, worst income gap=0, cap violations=0
- rabi worst calorie gap=0, worst income gap=0, cap violations=0

Season status counts:
Kharif:
- `Optimal`: 101
Rabi:
- `Optimal`: 101

Combined frontier range:
- nitrogen surplus: 6.625 to 7.519 Tg N
- water demand: 267.037 to 318.394 BCM
- nitrogen surplus: 79.960 to 90.751% of the 2017 baseline
- water demand: 57.110 to 68.093% of the 2017 baseline
- unique Pareto points: 101/101 alpha values
