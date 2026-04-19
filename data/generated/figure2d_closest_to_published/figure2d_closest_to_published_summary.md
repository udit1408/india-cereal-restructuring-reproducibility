# Figure 2(d) closest-to-published rebuild

This branch is designed to stay as close as possible to the published Figure 2(d) behavior while remaining
fully reproducible from the current cleaned workflow. It keeps the manuscript's seasonal income logic
(profit floor in kharif, relaxed income floor in rabi), preserves district total cropped area, and restricts
reallocation to crops already observed in each district. It does not apply the stricter district-crop historical
maximum-area cap, because that cap was not active in the legacy notebooks that underlie the original panel.

The published text for panel (d) is better matched by gross district-level reallocation away from a crop
(sum of all positive district losses divided by that crop's national baseline area) than by net national crop-area
change. Under that accounting, the rebuilt panel gives the following national shifts:

- rice gross reallocation: 39.0% of baseline rice area
- wheat gross reallocation: 19.1% of baseline wheat area
- rice net national area change: -30.7%
- wheat net national area change: -15.9%

The optimized national cereal-area shares closely match the published narrative:

- millet (bajra + ragi): 14.4% of optimized cropland area
- jowar: 9.0% of optimized cropland area
- maize: 19.7% of optimized cropland area

District-area conservation check: maximum district-season residual = 1.818989e-12 ha.

This branch reproduces the published rice-conversion magnitude and the alternative-cereal area shares closely.
It does not fully recover the legacy wheat value of 22.6%, suggesting that number should be treated as a
manuscript-level legacy value rather than as a reproducible output of the current archived code and data.

