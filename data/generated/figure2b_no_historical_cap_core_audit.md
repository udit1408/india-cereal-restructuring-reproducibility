# Figure 2(b) clean deterministic rebuild audit

This rebuild uses the same seasonal contexts as the clean Figure 2(a) frontier:
- unchanged district cropped area,
- crop substitution limited to historically grown crops,
- substitution among historically observed cereals without crop-specific historical area ceilings,
- state calorie constraints,
- state profit constraints.

The panel is regenerated deterministically for the two endpoint strategies only:
- `Water based`: minimize water demand in each season under the shared constraint set.
- `Nitrogen based`: minimize nitrogen surplus in each season under the shared constraint set.

This file is intended as the approved Figure 2(b) rebuild used in the revised manuscript.
It does not include whiskers, because the currently reproducible bootstrap pipeline is not yet aligned
with the cleaned endpoint formulation used for this approved branch.

Season-level solve status:
- Water based | kharif: Optimal
- Water based | rabi: Optimal
- Nitrogen based | kharif: Optimal
- Nitrogen based | rabi: Optimal

Cap-floor repairs inherited from seasonal contexts:
- kharif: 0
- rabi: 0

Combined annual percentage reductions:
## Water based
- Nitrogen Emission: 9.187%
- Nitrogen Leach: 10.976%
- Greenhouse Gas emission: 54.017%
- Profit: -16.226%
- Calorie: -8.103%
- Phosphorus application: 5.114%
- Nitrogen application: 3.063%
- Phosphorus Surplus: 10.481%
- Nitrogen Surplus: 9.249%
- Water Demand: 42.890%

## Nitrogen based
- Nitrogen Emission: 20.190%
- Nitrogen Leach: 22.526%
- Greenhouse Gas emission: 39.711%
- Profit: -17.910%
- Calorie: -6.055%
- Phosphorus application: 11.125%
- Nitrogen application: 10.807%
- Phosphorus Surplus: 17.247%
- Nitrogen Surplus: 20.040%
- Water Demand: 31.907%
