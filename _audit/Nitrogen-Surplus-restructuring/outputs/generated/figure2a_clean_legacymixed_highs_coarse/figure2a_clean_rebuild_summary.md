# Figure 2(a) clean rebuild

This rebuild uses the single-objective notebook data preparation but replaces the
legacy multi-objective notebook formulation with a clean model that:
- indexes districts jointly by `(state, district)` to avoid duplicate-name collisions,
- applies max-area caps using `(state, district, crop)` keys,
- normalizes the weighted objective by baseline nitrogen surplus and baseline water demand,
- records solver status explicitly and excludes non-optimal alpha points,
- combines seasons by summing national totals, consistent with the manuscript Methods.

Solver: `highs`
Income constraint: `legacy_mixed`
Alpha count: 5
Valid combined alphas: 5/5
Baseline cap repairs: kharif=5, rabi=8

Season status counts:
Kharif:
- `Optimal`: 5
Rabi:
- `Optimal`: 5

Combined frontier range:
- nitrogen surplus: 8.010 to 8.112 Tg N
- water demand: 413.804 to 470.831 BCM
