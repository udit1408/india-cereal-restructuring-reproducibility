# Figure 2(b) deterministic regeneration audit

This table is rebuilt directly from the four endpoint optimization outputs in
`revision_2/_audit/Nitrogen-Surplus-restructuring/generated/`.

For each scenario, kharif and rabi outputs are concatenated, annual totals are summed
across all district-crop rows, and the plotted percentage change is computed as
`100 * (Original - Optimized) / Original`.

The rendered panel uses `display_pct_change = -pct_reduction`, so reductions plot to the
left of zero and gains in calorie or profit plot to the right.

This script intentionally does not add uncertainty whiskers because the current workspace
does not contain a single reproducible bootstrap pipeline covering both the water-based and
nitrogen-based scenarios end to end. Deterministic bar centers are therefore regenerated
cleanly first; uncertainty should only be added back after a traceable bootstrap rebuild.

Key combined annual percentage reductions:

## Water based
- Nitrogen Emission: 12.300%
- Nitrogen Leach: 9.370%
- Greenhouse Gas emission: 40.106%
- Profit: -23.783%
- Calorie: -6.533%
- Phosphorus application: 7.955%
- Nitrogen application: 5.992%
- Phosphorus Surplus: 12.772%
- Nitrogen Surplus: 11.455%
- Water Demand: 43.377%

## Nitrogen based
- Nitrogen Emission: 22.366%
- Nitrogen Leach: 18.621%
- Greenhouse Gas emission: 27.932%
- Profit: -7.813%
- Calorie: -2.410%
- Phosphorus application: 14.951%
- Nitrogen application: 13.444%
- Phosphorus Surplus: 20.295%
- Nitrogen Surplus: 21.243%
- Water Demand: 35.340%
