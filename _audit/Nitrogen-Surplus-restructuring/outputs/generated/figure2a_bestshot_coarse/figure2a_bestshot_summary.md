# Figure 2(a) best-shot reconstruction

This reconstruction follows the manuscript definition of Fig. 2(a):
the weighted multi-objective sweep is executed separately for kharif and rabi,
solver status is recorded for each alpha, and the all-season frontier is formed by
summing national nitrogen surplus and water demand across the two seasons.

Solver: `highs`
Alpha count: 5
Alpha range: 0.00 to 1.00

Season status counts:
Kharif:
- `Infeasible`: 5
Rabi:
- `Infeasible`: 5

Consistency checks:
- kharif valid alphas: 0/5
- rabi valid alphas: 0/5
- combined valid alphas: 0/5

No scientifically admissible combined frontier was obtained from the current code/data
under this status-gated reconstruction. Any paper-facing redraw would therefore require
either recovery of the original season Pareto outputs or a method-level reformulation.

Method note:
The earlier notebook-based draft reproduction averaged kharif and rabi objective values by alpha.
This best-shot export instead uses kharif+rabi sums because the manuscript Methods describe
Fig. 2(a) in terms of total national water demand and nitrogen surplus for combined seasons.
