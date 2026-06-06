# Figure 2(a) frontier bootstrap audit

This SI-only robustness figure propagates local coefficient uncertainty through
the deterministic optimized allocations that define the primary Figure 2(a) alpha frontier
under the primary 2017-18 revenue benchmark, fixed district cropped area,
and substitution among historically observed cereals.

For each bootstrap iteration, district crop-specific water demand and net nitrogen application rates
are perturbed around the prepared 2017 coefficient fields using sign-symmetric residual draws
from the historical prepared-panel bootstrap pools.
The deterministic area allocation at each alpha is then held fixed and re-evaluated under the perturbed
coefficients. This reports coefficient-propagation uncertainty around the reported frontier rather than
a separate set of re-optimized frontiers.

## Revenue benchmark coverage

- kharif: direct realized-price coverage = 97.93% of decision keys and 99.95% of baseline cereal area
- rabi: direct realized-price coverage = 98.60% of decision keys and 99.95% of baseline cereal area

## Run metadata

Bootstrap iterations requested: 500
Random seed: 42
Elapsed time (s): 30.55

## Solve status counts

- Evaluated: 50500

The alpha-wise shaded bands in panels b-c are plotted as envelopes spanning the deterministic
frontier and the fixed-allocation bootstrap ensemble.

## Endpoint envelopes

- Water-based endpoint: nitrogen 7.952 Tg N (envelope 7.821 to 8.124), water 334.053 BCM (envelope 323.087 to 355.641), optimal 500/500
- Nitrogen-based endpoint: nitrogen 7.177 Tg N (envelope 7.014 to 7.312), water 380.792 BCM (envelope 368.034 to 403.808), optimal 500/500

Panel d reports the fixed-allocation bootstrap distributions at the two frontier endpoints,
with deterministic values shown explicitly against the bootstrap median and central spread.

## Mid-frontier check

- Alpha=0.50: nitrogen 7.372 Tg N (envelope 7.235 to 7.504), water 344.138 BCM (envelope 334.256 to 363.420), optimal 500.0/500.0
