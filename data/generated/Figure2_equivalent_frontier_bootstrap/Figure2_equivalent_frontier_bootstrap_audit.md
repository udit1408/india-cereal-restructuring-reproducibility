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

- kharif: direct realized-price coverage = 90.97% of decision keys and 99.97% of baseline cereal area
- rabi: direct realized-price coverage = 97.15% of decision keys and 99.99% of baseline cereal area

## Run metadata

Bootstrap iterations requested: 500
Random seed: 42
Elapsed time (s): 29.89

## Solve status counts

- Evaluated: 50500

The alpha-wise shaded bands in panels b-c are plotted as envelopes spanning the deterministic
frontier and the fixed-allocation bootstrap ensemble.

## Endpoint envelopes

- Water-based endpoint: nitrogen 7.665 Tg N (envelope 7.447 to 7.924), water 300.667 BCM (envelope 289.394 to 388.396), optimal 500/500
- Nitrogen-based endpoint: nitrogen 6.825 Tg N (envelope 6.657 to 6.988), water 348.227 BCM (envelope 329.266 to 443.503), optimal 500/500

## Mid-frontier check

- Alpha=0.50: nitrogen 6.999 Tg N (envelope 6.792 to 7.211), water 311.004 BCM (envelope 300.401 to 403.663), optimal 500.0/500.0
