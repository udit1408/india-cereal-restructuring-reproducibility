# Figure 2(a) frontier bootstrap audit

This SI-only robustness figure propagates the same local coefficient-bootstrap logic used
for the Figure 2(b) endpoint whiskers across the full approved Figure 2(a) alpha frontier under
fixed district cropped area and substitution among historically observed cereals.

For each bootstrap iteration, district crop-specific water demand and net nitrogen application rates
are perturbed around the prepared 2017 coefficient fields using the historical prepared-panel bootstrap pools.
State calorie and MSP-benchmarked profit constraints are held fixed at their approved 2017 values.

Bootstrap iterations requested: 50
Random seed: 42
Elapsed time (s): 437.71

## Solve status counts

- Optimal: 5050

The alpha-wise shaded bands in panels b-c are plotted as envelopes spanning the deterministic
frontier and the bootstrap frontier ensemble, not as percentile intervals centered on the deterministic line.

## Endpoint envelopes

- Water-based endpoint: nitrogen 7.519 Tg N (envelope 7.517 to 7.979), water 267.037 BCM (envelope 236.378 to 267.037), optimal 50/50
- Nitrogen-based endpoint: nitrogen 6.625 Tg N (envelope 6.245 to 6.625), water 318.394 BCM (envelope 299.349 to 392.095), optimal 50/50

## Mid-frontier check

- Alpha=0.50: nitrogen 6.847 Tg N (envelope 6.542 to 6.849), water 279.534 BCM (envelope 253.668 to 279.534), optimal 50.0/50.0
