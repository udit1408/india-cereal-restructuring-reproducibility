# Figure 2(d) clean rebuild

This rebuild uses the same clean nitrogen-focused optimization formulation adopted for the updated
Figure 2(a) reconstruction: unchanged district cropped area, state-level calorie and profit constraints,
district-crop historical maximum area caps, and crop availability restricted to crops observed in the
historical record for each district.

The transition panel is not read directly from an optimization variable because the model optimizes
pre- and post-optimization crop areas rather than crop-to-crop movement. The alluvial panel therefore
uses a deterministic allocation rule within each district-season:
1. retain `min(original, optimized)` area on the diagonal for each crop;
2. compute residual crop losses and gains;
3. distribute each losing crop's residual area across gaining crops in proportion to those gains.

Constraint audit:
- max district-season area residual: 5.684342e-14 ha
- worst state calorie gap vs. relaxed model target: -2.343750e-02 kcal (solver tolerance only)
- worst state profit gap vs. relaxed model target: -3.432592e+03 Rs (solver tolerance only)

National area changes:
- rice: 44.545 Mha -> 43.190 Mha (-3.043%)
- wheat: 30.731 Mha -> 30.588 Mha (-0.466%)
- total area reallocated off the diagonal: 6.355 Mha (6.373% of baseline cereal area)

Largest off-diagonal flows under the proportional within-district allocation rule:
- rice -> maize: 1.322 Mha
- maize -> rice: 0.566 Mha
- rice -> bajra: 0.459 Mha
- rice -> jowar: 0.436 Mha
- maize -> jowar: 0.316 Mha
- bajra -> jowar: 0.263 Mha
- maize -> bajra: 0.259 Mha
- wheat -> jowar: 0.259 Mha
- jowar -> bajra: 0.256 Mha
- maize -> wheat: 0.232 Mha

