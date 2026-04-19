# Figure 2(a) clean rebuild

This rebuild uses the single-objective notebook data preparation but replaces the
legacy multi-objective notebook formulation with a clean model that:
- indexes districts jointly by `(state, district)` to avoid duplicate-name collisions,
- applies max-area caps using `(state, district, crop)` keys,
- normalizes the weighted objective by baseline nitrogen surplus and baseline water demand,
- records solver status explicitly and excludes non-optimal alpha points,
- combines seasons by summing national totals, consistent with the paper methods summary.

Solver: `glpk`
Income constraint: `profit`
Alpha count: 5
Valid combined alphas: 5/5
Baseline cap repairs: kharif=53, rabi=57

Season status counts:
Kharif:
- `Optimal`: 5
Rabi:
- `Optimal`: 5

Combined frontier range:
- nitrogen surplus: 8.231 to 8.240 Tg N
- water demand: 426.267 to 428.514 BCM
