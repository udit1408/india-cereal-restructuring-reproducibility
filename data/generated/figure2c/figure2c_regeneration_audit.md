# Figure 2(c) regeneration audit

This rebuild uses the cultural-significance notebooks
`kharif_n_culture.ipynb` and `rabi_n_cultural_cop.ipynb`, but executes only their
data-preparation preambles and then resolves the optimization cleanly in Python.

The notebook preamble contains broken diagnostic print statements in the rabi notebook;
those lines are stripped before execution because they do not affect any model inputs.

Two configurations are exported:

1. `method_consistent`: nitrogen-minimization with unchanged district cropped area,
   historically observed district crops as the admissible menu, historical maximum crop-area
   caps, state calorie constraints, state profit constraints, and the seasonal rice/wheat
   retention constraint.
2. `no_historical_caps`: the same model, but with the historical crop-area cap removed
   to diagnose the source of the published panel magnitude.

Historically admissible district-crop options missing one or more 2017 coefficient bundles are completed from state-crop means and then crop-level means before solving.
Completed district-crop coefficient bundles: kharif 464, rabi 349.

Combined national nitrogen-surplus reduction ranges:
- method-consistent: 2.589% to 3.056%
- state-retention (no historical caps): 10.650% to 20.040%
- equation-aligned (district retention, no historical caps): 6.584% to 20.040%

Axis interpretation:
- The legacy combined notebook sets `gamma_values = 100 - summed_df['Gamma'] * 100` and labels that axis as substitution rate.
- That quantity is a nominal retention-relaxation parameter, not the realized rice+wheat area replaced after optimization.
- In the method-consistent rebuild, the realized combined rice+wheat replacement is only -0.693% to 1.736%.

Interpretation:
- The published panel magnitude is only approached when the historical crop-area caps are off.
- The state-retention no-cap variant stays closest to the published Figure 2(c) magnitude.
- The district-level no-cap variant stays closer to the subsection equations x_{i,r} and x_{i,w}.
- Once those caps are enforced cleanly, the cultural-significance curve remains monotone but drops to about 3%.
- The legacy x-axis label therefore overstates how much staple area is actually replaced in the clean rebuild.
- The historical crop-area cap is therefore the dominant source of the discrepancy between the legacy panel and the method-consistent rebuild.

Season-level ranges:
- kharif method-consistent: 2.572% to 3.205%
- rabi method-consistent: 2.620% to 2.794%
- kharif without caps: 11.858% to 25.377%
- rabi without caps: 8.521% to 10.626%

For manuscript revision, there are therefore two plausible candidate panels if the goal
is to stay near the legacy magnitude while avoiding a silent mismatch in interpretation:
- use the state-level/no-cap variant and revise the Methods paragraph to state-level retention explicitly;
- or use the district-level/no-cap variant and revise the Methods paragraph to clarify that the cultural sensitivity analysis relaxes historical area caps.

The strict method-consistent panel remains the cleanest reconstruction of the primary optimization framework.
