# Figure 2 Legacy-Faithful Audit

The earlier strict rebuild drifted away from the manuscript because it made the district-crop historical maximum area cap genuinely binding. In the legacy notebooks, that cap is assembled with `(State, District, Crop)` tuple keys but tested inside the model as `if c in max_area_constraints`, so it is effectively inactive. Once that notebook behavior is preserved, the manuscript-scale magnitudes are much closer to the original outputs.

For panel 2(a), I rebuilt sample alpha points directly from `kharif_perito_cop.ipynb` and `rabi_perito_cop.ipynb` using the raw weighted objective, the same row-weighted seasonal aggregation used in `rabi_kharif_plot_perito_combined.ipynb`, fixed district cropped area, and the same locally grown crop restriction. The kharif Pareto notebook enforces a state profit floor, whereas the rabi Pareto notebook enforces a state MSP floor. Under that legacy-faithful setup, the rebuilt combined frontier matches the archived plotted frontier exactly at sampled alpha values. The remaining concern is status handling: CBC still returns `Infeasible` for the kharif and rabi endpoint solves even though the reported objective values match the archived CSVs.

| alpha | kharif_status | rabi_status | rebuilt_nitrogen_tg | archived_nitrogen_tg | rebuilt_water_bcm | archived_water_bcm | delta_nitrogen_tg | delta_water_bcm |
| ----- | ------------- | ----------- | ------------------- | -------------------- | ----------------- | ------------------ | ----------------- | --------------- |
| 0.000 | Infeasible    | Infeasible  | 3.508               | 3.508                | 123.984           | 123.984            | 0.000             | 0.000           |
| 0.250 | Infeasible    | Infeasible  | 3.517               | 3.517                | 123.984           | 123.984            | 0.000             | 0.000           |
| 0.500 | Infeasible    | Infeasible  | 3.499               | 3.499                | 123.996           | 123.996            | 0.000             | 0.000           |
| 0.750 | Infeasible    | Infeasible  | 3.485               | 3.485                | 124.065           | 124.065            | 0.000             | 0.000           |
| 1.000 | Infeasible    | Infeasible  | 3.167               | 3.167                | 142.099           | 142.099            | 0.000             | 0.000           |

Panel 2(b) is internally consistent on the legacy branch. The generated endpoint exports in `generated/` recover the published combined bar heights exactly when their seasonal totals are summed. Those published values sit very close to the no-historical-cap branch and far from the strict capped rebuild, which is consistent with the ineffective crop-specific cap in the original endpoint notebooks as well.

Water-based and nitrogen-based combined reductions for the two headline metrics are summarized below.

Water-based endpoint:

| variant                 | Nitrogen Surplus | Water Demand |
| ----------------------- | ---------------- | ------------ |
| clean_capped            | 2.128            | 11.519       |
| legacy_endpoint_exports | 11.455           | 43.377       |
| no_historical_caps      | 12.957           | 44.493       |

Nitrogen-based endpoint:

| variant                 | Nitrogen Surplus | Water Demand |
| ----------------------- | ---------------- | ------------ |
| clean_capped            | 3.362            | -0.637       |
| legacy_endpoint_exports | 21.243           | 35.340       |
| no_historical_caps      | 21.408           | 36.257       |

Panel 2(c) shows the same structural split. With historical crop-area caps enforced, the combined nitrogen-surplus reduction only spans about 3.029% to 3.362%. Without those caps, the combined curve spans about 13.767% to 21.408%, which is much closer to the manuscript text describing roughly 12% to 22% reductions. The x-axis also needs care: the notebook grid is in 10% steps of the nominal retention parameter, not the 25/50/75 checkpoints described in the current prose, and even the most relaxed no-cap case only realizes about 21.755% actual rice+wheat replacement.

| variant            | metric                                                     | value  |
| ------------------ | ---------------------------------------------------------- | ------ |
| method_consistent  | n_surplus_reduction_at_0pct_nominal_substitution           | 3.029  |
| method_consistent  | n_surplus_reduction_at_50pct_nominal_substitution          | 3.362  |
| method_consistent  | n_surplus_reduction_at_100pct_nominal_substitution         | 3.362  |
| method_consistent  | realized_staple_replacement_at_100pct_nominal_substitution | 1.572  |
| no_historical_caps | n_surplus_reduction_at_0pct_nominal_substitution           | 13.767 |
| no_historical_caps | n_surplus_reduction_at_50pct_nominal_substitution          | 20.362 |
| no_historical_caps | n_surplus_reduction_at_100pct_nominal_substitution         | 21.408 |
| no_historical_caps | realized_staple_replacement_at_100pct_nominal_substitution | 21.755 |
| district_no_caps   | n_surplus_reduction_at_0pct_nominal_substitution           | 8.109  |
| district_no_caps   | n_surplus_reduction_at_50pct_nominal_substitution          | 15.338 |
| district_no_caps   | n_surplus_reduction_at_100pct_nominal_substitution         | 21.408 |
| district_no_caps   | realized_staple_replacement_at_100pct_nominal_substitution | 21.755 |

Panel 2(d) remains the one place where the legacy-like no-cap branch gets much closer but does not fully recover the manuscript text. The no-cap rebuild moves rice area by about -31.559% and wheat area by about -8.760%, compared with manuscript text of -38.000% and -22.600%. That makes the rice change broadly compatible with the legacy branch, but the wheat change still needs targeted checking before it is treated as fully recovered.

| variant              | scenario | value   |
| -------------------- | -------- | ------- |
| clean_capped         | rice     | -3.043  |
| clean_capped         | wheat    | -0.466  |
| clean_no_caps        | rice     | -31.559 |
| clean_no_caps        | wheat    | -8.760  |
| legacy_reported_text | rice     | -38.000 |
| legacy_reported_text | wheat    | -22.600 |

Working conclusion: the repository and manuscript are not randomly wrong. Their central message and most of the published Figure 2 magnitudes sit on a legacy-faithful effective model defined by fixed district cropped area, locally grown crop substitution, panel-specific state income constraints, and an in-practice inactive crop-specific historical maximum cap. The main unresolved technical issue is not the direction of the science but whether the revision should stay on that legacy-effective branch or move to the stricter capped branch, and how to handle the Figure 2(a) solver-status problem if we stay close to the published outputs.
