# Figure 2(d) no-historical-cap core rebuild

This panel is aligned to the same core optimization branch used for Figure 2(a),
Figure 2(b), and the displayed no-cap variant of Figure 2(c): unchanged district
cropped area, state calorie constraints, state profit constraints, locally observed
crops only, and no hard district-crop historical maximum-area cap.

To keep the panel text consistent with the visual transition diagram, the rice and wheat
reallocation magnitudes reported below use gross district-level losses relative to each crop's
national baseline area, alongside the corresponding net national area changes.

- rice gross reallocation: 37.1% of baseline rice area
- wheat gross reallocation: 10.4% of baseline wheat area
- rice net national area change: -31.5%
- wheat net national area change: -5.9%

The optimized national cereal-area shares under this same branch are:

- millet (bajra + ragi): 11.2% of optimized cropland area
- jowar: 12.5% of optimized cropland area
- maize: 16.7% of optimized cropland area

District-area conservation check: maximum district-season residual = 1.818989e-12 ha.

This corrected variant keeps the same no-historical-cap nitrogen-focused optimization
structure as the core rebuild, but filters each district-season crop choice set to entries
with a valid coefficient bundle before solving.

- kept crop-choice entries: 3434
- removed crop-choice entries with incomplete or zero core coefficients: 813

This is intended to prevent allocation into district-crop combinations with zero yield/calorie
or otherwise missing core coefficients.

