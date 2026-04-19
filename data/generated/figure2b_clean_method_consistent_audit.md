# Figure 2(b) clean deterministic rebuild audit

This rebuild uses the same strict seasonal contexts as the clean Figure 2(a) frontier:
- unchanged district cropped area,
- crop substitution limited to historically grown crops,
- district-crop historical maximum area caps,
- state calorie constraints,
- state profit constraints.

The panel is regenerated deterministically for the two endpoint strategies only:
- `Water based`: minimize water demand in each season under the shared constraint set.
- `Nitrogen based`: minimize nitrogen surplus in each season under the shared constraint set.

This file is intended as the clean method-consistent alternative to the legacy-centered Figure 2(b).
It does not include whiskers, because the currently reproducible bootstrap pipeline is not yet aligned
with the strict capped model used for the clean endpoints.

Season-level solve status:
- Water based | kharif: Optimal
- Water based | rabi: Optimal
- Nitrogen based | kharif: Optimal
- Nitrogen based | rabi: Optimal

Cap-floor repairs inherited from seasonal contexts:
- kharif: 5
- rabi: 8

Combined annual percentage reductions:
## Water based
- Nitrogen Emission: 2.246%
- Nitrogen Leach: 1.761%
- Greenhouse Gas emission: 5.284%
- Profit: -4.967%
- Calorie: -0.840%
- Phosphorus application: 1.549%
- Nitrogen application: 1.061%
- Phosphorus Surplus: 2.384%
- Nitrogen Surplus: 2.128%
- Water Demand: 11.519%

## Nitrogen based
- Nitrogen Emission: 3.546%
- Nitrogen Leach: 2.901%
- Greenhouse Gas emission: 2.988%
- Profit: -3.199%
- Calorie: -0.697%
- Phosphorus application: 2.107%
- Nitrogen application: 1.948%
- Phosphorus Surplus: 2.978%
- Nitrogen Surplus: 3.362%
- Water Demand: -0.637%
