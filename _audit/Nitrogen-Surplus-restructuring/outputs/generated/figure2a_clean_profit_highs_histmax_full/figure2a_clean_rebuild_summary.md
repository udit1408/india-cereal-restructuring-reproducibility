# Figure 2(a) clean rebuild

This rebuild uses the single-objective notebook data preparation but replaces the
legacy multi-objective notebook formulation with a clean model that:
- indexes districts jointly by `(state, district)` to avoid duplicate-name collisions,
- applies max-area caps using `(state, district, crop)` keys,
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
Baseline cap repairs: kharif=5, rabi=8
Baseline feasibility after repair:
- kharif worst calorie gap=0, worst income gap=0, cap violations=0
- rabi worst calorie gap=0, worst income gap=0, cap violations=0

Season status counts:
Kharif:
- `Optimal`: 101
Rabi:
- `Optimal`: 101

Combined frontier range:
- nitrogen surplus: 8.007 to 8.109 Tg N
- water demand: 413.726 to 470.563 BCM
- nitrogen surplus: 96.638 to 97.872% of the 2017 baseline
- water demand: 88.481 to 100.637% of the 2017 baseline
- unique Pareto points: 101/101 alpha values
