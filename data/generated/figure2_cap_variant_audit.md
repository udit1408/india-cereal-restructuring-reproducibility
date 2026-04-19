# Figure 2 cap-variant audit

This note compares two coherent Figure 2 branches:

1. `clean_capped`: the strict method-consistent rebuild with unchanged district cropped area, locally grown crops only, state calorie and profit constraints, and district-crop historical maximum area caps.
2. `clean_no_caps`: the same optimization but with the district-crop historical maximum area caps removed.

The GitHub audit root currently resolves to:

- local HEAD: `596682e561ae3f5fad1393b83e1a68e20611cfdb`
- `origin/main`: `760ab516aed4d38d437fee17f5b3b0e706bff745`

Remote diff relative to the local audit checkout:

- `M	code_data.zip`

The comparisons below show that the historical maximum area caps are the dominant driver of the magnitude gap between the strict rebuild and the legacy Figure 2 outputs.

## Figure 2(a) endpoint comparison

`legacy_plotted` refers to the archived combined frontier CSV used for the old panel. `clean_no_caps` uses annual sums from the no-cap endpoint solves rather than the old plotting-stage averaging.

| scenario       | variant        | nitrogen_tg | water_bcm |
| -------------- | -------------- | ----------- | --------- |
| Water based    | legacy_plotted | 3.508       | 123.984   |
| Water based    | clean_capped   | 8.109       | 413.726   |
| Water based    | clean_no_caps  | 7.212       | 259.544   |
| Nitrogen based | legacy_plotted | 3.167       | 142.099   |
| Nitrogen based | clean_capped   | 8.007       | 470.563   |
| Nitrogen based | clean_no_caps  | 6.512       | 298.054   |

## Figure 2(b) percentage changes

Values are annual percentage reductions relative to the 2017 baseline. Negative values for `Profit` or `Calorie` indicate increases rather than declines.

| scenario       | variant                 | metric           | pct_reduction |
| -------------- | ----------------------- | ---------------- | ------------- |
| Nitrogen based | clean_capped            | Profit           | -3.199        |
| Water based    | clean_capped            | Profit           | -4.967        |
| Nitrogen based | clean_capped            | Calorie          | -0.697        |
| Water based    | clean_capped            | Calorie          | -0.840        |
| Nitrogen based | clean_capped            | Nitrogen Surplus | 3.362         |
| Water based    | clean_capped            | Nitrogen Surplus | 2.128         |
| Nitrogen based | clean_capped            | Water Demand     | -0.637        |
| Water based    | clean_capped            | Water Demand     | 11.519        |
| Nitrogen based | no_historical_caps      | Profit           | -17.253       |
| Water based    | no_historical_caps      | Profit           | -23.133       |
| Nitrogen based | no_historical_caps      | Calorie          | -1.102        |
| Water based    | no_historical_caps      | Calorie          | -4.156        |
| Nitrogen based | no_historical_caps      | Nitrogen Surplus | 21.408        |
| Water based    | no_historical_caps      | Nitrogen Surplus | 12.957        |
| Nitrogen based | no_historical_caps      | Water Demand     | 36.257        |
| Water based    | no_historical_caps      | Water Demand     | 44.493        |
| Nitrogen based | legacy_endpoint_exports | Profit           | -7.813        |
| Water based    | legacy_endpoint_exports | Profit           | -23.783       |
| Nitrogen based | legacy_endpoint_exports | Calorie          | -2.410        |
| Water based    | legacy_endpoint_exports | Calorie          | -6.533        |
| Nitrogen based | legacy_endpoint_exports | Nitrogen Surplus | 21.243        |
| Water based    | legacy_endpoint_exports | Nitrogen Surplus | 11.455        |
| Nitrogen based | legacy_endpoint_exports | Water Demand     | 35.340        |
| Water based    | legacy_endpoint_exports | Water Demand     | 43.377        |

Removing the historical caps pulls the clean endpoint bars close to the legacy export-centered bars:

- water-based water-demand reduction: `11.519%` with caps versus `44.493%` without caps, compared with the legacy `43.377%`;
- nitrogen-based nitrogen-surplus reduction: `3.362%` with caps versus `21.408%` without caps, compared with the legacy `21.243%`;
- nitrogen-based water-demand co-benefit: `-0.637%` with caps versus `36.257%` without caps, compared with the legacy `35.340%`.

## Figure 2(c) combined endpoint comparison

The endpoint reported here is the `gamma = 0` case, which corresponds to the strongest relaxation of the staple-retention parameter.

| variant                          | n_surplus_reduction_pct | realized_staple_replacement_pct |
| -------------------------------- | ----------------------- | ------------------------------- |
| clean_capped                     | 3.362                   | 1.572                           |
| clean_no_caps_state_retention    | 21.408                  | 21.755                          |
| clean_no_caps_district_retention | 21.408                  | 21.755                          |

For Figure 2(c), the no-cap branch nearly restores the legacy nitrogen-surplus reduction magnitude. The difference between the state-retention and district-retention variants is much smaller than the difference caused by switching the historical caps on or off.

## Figure 2(d) rice and wheat area shifts

`legacy_reported_text` is the crop-area change described in the old main-text narrative, included here only as a reference point.

| variant              | crop  | original_mha | optimized_mha | pct_change |
| -------------------- | ----- | ------------ | ------------- | ---------- |
| clean_capped         | rice  | 44.545       | 43.190        | -3.043     |
| clean_capped         | wheat | 30.731       | 30.588        | -0.466     |
| clean_no_caps        | rice  | 44.545       | 30.487        | -31.559    |
| clean_no_caps        | wheat | 30.731       | 28.039        | -8.760     |
| legacy_reported_text | rice  |              |               | -38.000    |
| legacy_reported_text | wheat |              |               | -22.600    |

For Figure 2(d), the no-cap branch moves the transition magnitudes materially toward the legacy narrative, especially for rice, but it does not fully recover the previously reported wheat shift. This means the historical caps explain most of the gap, but the old alluvial panel also depended on additional legacy transition-accounting choices.

## Working conclusion

There are now two internally coherent options:

1. Keep the paper methods summary as currently written, retain the historical caps, and use the strict `clean_capped` Figure 2 panels with smaller but fully aligned effect sizes.
2. Revise the Methods explicitly so that the main Figure 2 optimization does not impose district-crop historical maximum area caps, then use annual summed endpoints for Figure 2(a) and the corresponding no-cap versions of Figure 2(b), Figure 2(c), and Figure 2(d).

The important point is that the legacy magnitudes are not being reproduced by a hidden bug hunt anymore; they are being reproduced when the cap assumption is relaxed in a controlled and transparent way.
