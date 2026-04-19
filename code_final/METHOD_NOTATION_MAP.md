# Method Notation Map

This file aligns the paper notation with the final audited code path. It is intended to prevent accidental drift between the paper methods summary and the reproducible code.

## Core Sets and Indices

| Paper notation | Meaning | Final code representation |
|---|---|---|
| `i` | District | `district` string in tuple keys `(state, district, crop)` |
| `j` | State | `state` string in tuple keys and `states` lists |
| `c` | Crop | `crop` string; final crop set is rice, wheat, maize, bajra, jowar, ragi |
| `s` | Season | `season` key, with values `kharif` and `rabi` |
| `D_j` | Districts in state `j` | `districts_by_state[state]` |
| `C` | Six focal cereals | `crops_by_pair[(state, district)]` contains the feasible crop subset for each district |
| `S` | Rabi and kharif seasons | `SEASON_NOTEBOOKS` / seasonal context dictionaries |

## Decision Variable and Feasible Area

| Paper notation | Meaning | Final code representation |
|---|---|---|
| `x_{i,j,c,s}` | Optimized cultivated area for district-state-crop-season | PuLP variables named `area__{state}__{district}__{crop}` in `figure2a_clean_rebuild._build_problem`, `generate_figure2b_clean.solve_endpoint`, `generate_figure2c.solve_season`, and `generate_figure2d_clean.solve_nitrogen_focused_areas` |
| `A_{i,j,c,s}^{cu}` | 2017 baseline cultivated area | `current_cereal_area[(state, district, crop)]` |
| `sum_c x = sum_c A^{cu}` | District-season total cereal area conservation | `prob += lpSum(x[(state, district, crop)] ...) == current_area/current_cereal_area` |
| `A_{i,j,c,s}^{hs}` | Historical crop presence | The final feasible crop list is `crops_by_pair[(state, district)]`; crops outside this list have no decision variable and therefore behave as `x=0` |
| no hard historical maximum cap | Historical area is not a future upper bound in the main branch | Final calls set `use_historical_caps=False`; hard-cap branches are legacy/audit only |

## Objectives

| Paper notation | Meaning | Final code representation |
|---|---|---|
| `NS_{i,j,c,s}` | Per-hectare nitrogen-surplus coefficient | `net_n_surplus`, or `nitrogen_rate - yield_data * nitrogen_removal_rate` where bootstrap coefficients are perturbed |
| `F_N(x)` | Total nitrogen surplus objective | `objective_n = lpSum(x * net_n_surplus)` or the equivalent net-N expression in bootstrap code |
| `CWD_{i,j,c,s}` | Per-hectare consumptive water-demand coefficient | `water_rate[(state, district, crop)]` |
| `F_W(x)` | Total water-demand objective | `objective_w = lpSum(x * water_rate)` |
| `F_N^{2017}`, `F_W^{2017}` | Baseline 2017 totals for normalization | `baseline_n_surplus`, `baseline_water` |
| `alpha` | Weighted-objective parameter | `DEFAULT_ALPHAS`; final Figure 2(a) solves `0.00` to `1.00` in 0.01 increments |
| `alpha F_N/F_N^{2017} + (1-alpha)F_W/F_W^{2017}` | Normalized weighted objective | `_build_problem(... objective_mode="normalized", use_historical_caps=False)` in `generate_Figure2_equivalent.py` |

## Calorie and Income Constraints

| Paper notation | Meaning | Final code representation |
|---|---|---|
| `Y_{i,j,c,s}` | Crop yield | `yield_data[(state, district, crop)]`; code uses kg ha-1 basis from the notebook-derived tables |
| `kc_c` | Crop calorie density | `calories_per_prod[(state, district, crop)]`; code uses kcal kg-1 with production in kg, equivalent to the manuscript kcal tonne-1 expression after unit conversion |
| State-season calorie floor | Post-optimization calories must meet baseline state-season calories | `initial_state_calories[state]`; enforced by `lpSum(x * yield_data * calories_per_prod) >= initial_state_calories[state]` |
| `SP_{j,c}^{bench}` | Primary benchmark selling price | In final code this is stored in the inherited variable name `msp_per_prod`; `generate_Figure2_equivalent.py` overwrites it using matched state-year realized prices where available and crop-wise realized-price/MSP fallback otherwise |
| `Cp_{j,c}^{prod}` | DES C2 cost-of-production benchmark | `cost_per_prod[(state, district, crop)]` |
| `pi_{j,c}=10(SP_{j,c}^{bench}-Cp_{j,c}^{prod})` | Net-return coefficient in Rs tonne-1 | Code computes the equivalent as `0.01 * yield_data * (msp_per_prod - cost_per_prod)`, because code yields are kg ha-1 and price/cost terms are Rs quintal-1 |
| State-season income floor | Post-optimization benchmarked net farmer income must meet baseline | `initial_state_profit[state]`; enforced in `income_mode="profit"` |

## Revenue Benchmark Wiring

| Paper concept | Final code implementation |
|---|---|
| Matched official state-year realized prices | `load_state_price_lookup()` in `generate_si_hybrid_revenue_profit_sensitivity.py`, reused by `generate_Figure2_equivalent.py` |
| Crop-wise realized-price/MSP fallback | `load_ratio_scenarios()` returns the crop-specific realized-price/MSP multipliers |
| Primary 2017--18 benchmark | `generate_Figure2_equivalent.py --scenario-year 2017-18`; this is the final main-figure branch |
| Coverage audit | `Figure2_equivalent_price_coverage.csv` records direct versus fallback realized-price coverage by panel and season |

## Cultural Retention and Trade

| Paper notation | Meaning | Final code representation |
|---|---|---|
| `tau` | State-level rice/wheat retained-area parameter | `generate_figure2c.solve_season(... retention_level="state")` called through `generate_Figure2_equivalent.py` |
| rice kharif, wheat rabi retention | Retained staple-area floors by primary season | `CULTURAL_NOTEBOOKS` and `retain_crop` in `generate_figure2c.py` |
| `D_{ij}^{staple}` | Staple calorie deficit on a trade link | `diff_trade_kcal` and related link-level fields in `generate_Figure3_equivalent.py` |
| `W_{ij,alt,opt}^{kcal}` | Optimized alternative-cereal trade in kcal | `optimized_trade_kcal` for alternative-cereal edges |
| `P_{i,alt,opt}^{kcal}` | Optimized alternative-cereal production capacity | `optimized_alt_prod_kcal` in the Figure 3 alternative-trade summary |

## Final-Code Guardrails

1. Any code used for final main figures must be reachable from `code_final/run_final_revision2_batch.sh`.
2. If a script has a legacy default such as `use_historical_caps=True`, the final runner must call it only through a wrapper that explicitly sets `use_historical_caps=False`.
3. The public paper description should describe the primary revenue benchmark, not "MSP-only" income, except when discussing supplementary MSP comparisons.
4. The public paper description should describe calorie preservation as calorie adequacy or energy availability, not as full food-security or nutritional-security optimization.
5. Figure 3 must use the Figure 2 nitrogen-focused optimized area table generated under the same primary revenue benchmark.
