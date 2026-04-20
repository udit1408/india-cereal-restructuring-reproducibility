# Official Realized-Price And Production Inputs

This folder contains the authoritative input tables for the public realized-price benchmark used by the reproducibility workflow.

The key point is narrow but important: the main workflow does not take direct crop revenue from older MSP-only fields or from notebook-side revenue values. Direct realized prices come from official state-year value-output and production tables bundled here.

## Authoritative Input Files

- `state_realized_price_state_year_inputs_2011_12_to_2017_18.csv`
  - state-year-crop realized-price table assembled from official value-of-output and production sources.
  - this is the direct price source for the primary benchmark.
  - the filename retains its historical compatibility label.
  - official source routes:
    - MoSPI publications portal: `https://www.mospi.gov.in/publications-reports/innerpage/431`
    - UPAg public portal: `https://upag.gov.in/`

- `all_india_realized_price_year_inputs_2011_12_to_2017_18.csv`
  - all-India crop-year realized-price table derived from the same official value and production sources.
  - this is used to compute crop-year national mean prices and crop-year realized-price/MSP ratios.
  - official source routes:
    - MoSPI publications portal: `https://www.mospi.gov.in/publications-reports/innerpage/431`
    - UPAg public portal: `https://upag.gov.in/`

- `state_realized_price_join_audit_2011_12_to_2017_18.csv`
  - join audit showing which state-year-crop rows were matched directly and which required fallback handling.

- `des_apy_selected_crops_state_year_season_production_2011_12_to_2017_18.csv`
  - official DES/APY production denominator used when constructing the revised realized-price tables.
  - public production portal checked during the benchmark audit: `https://upag.gov.in/`

- `des_msp_selected_crops_2013_14_to_2017_18.csv`
  - MSP reference table.
  - in the revised main benchmark this is not used as a direct realized-price source.
  - it is used only in the explicit realized-price/MSP fallback for unmatched state-crop pairs and in MSP comparison analyses retained for Supplementary Information.

- `des_cost_concepts.csv`
  - DES cost-concept reference used only for Methods/SI clarification of production-cost terminology.

## Benchmark Rule

The primary public-price benchmark is implemented through:

- `scripts/generate_si_revenue_profit_sensitivity.py`
  - `load_state_price_bundle()`
- `scripts/generate_figure2_main.py`
  - `_apply_hybrid_price_to_dict_context()`
  - `_apply_hybrid_price_to_season_context()`
- `scripts/generate_primary_revenue_price_summary_table.py`

The rule is:

1. Read `state_realized_price_state_year_inputs_2011_12_to_2017_18.csv`.
2. Keep only matched state-crop-year rows with finite and strictly positive realized prices.
3. If a matched official row exists but its realized price is zero or unusable, replace it with the crop-year national realized-price mean computed from aggregated official value and production.
4. If no matched official state-crop row exists, use the explicit crop-year realized-price/MSP fallback.
5. Therefore, legacy MSP values are never treated as direct realized-price observations in the primary benchmark.

The official public routes referenced for this benchmark are:

- MoSPI value-output route: `https://www.mospi.gov.in/publications-reports/innerpage/431`
- UPAg public production portal: `https://upag.gov.in/`

For the official 2017-18 benchmark currently used in the workflow, the repaired bad direct-price keys are screened out before they can enter the model. In the present decision-key coverage this repair does not materially move the headline results, but it prevents zero-price direct matches from silently contaminating future reruns.

## Sandbox Rule

The sandbox test based on the collaborator CSV is implemented in:

- `scripts/generate_figure2_stateprice_csv_sandbox.py`
  - `build_stateprice_inputs()`
  - `build_ratio_scenarios_from_stateprice()`

In that sandbox path the prices are recomputed from aggregated raw totals:

- state price = `(sum Output_lakh * 100) / sum Production_tonne`
- national crop-year price = `(sum Output_lakh across states * 100) / sum Production_tonne across states`

The sandbox hierarchy is:

1. Use the aggregated state price if it is finite and positive.
2. Otherwise use the national crop-year mean price.
3. Only if neither is available, use the ratio-scaled fallback.

This avoids carrying forward unusable precomputed `rupee_per_kg` rows when the underlying value or production totals imply that the direct state price should not be trusted.

## What Was Replaced And What Was Not

Replaced for the primary revenue benchmark:

- direct crop revenue/prices used in the income constraint and endpoint reporting.

Not replaced:

- the district agronomic crop tables used for area, yield, calorie, water, nitrogen, and phosphorus coefficients.

That separation is deliberate. The new official production tables are used to construct the revised revenue benchmark. They do not replace the district-level agronomic inputs that define the optimization problem itself.

## Guardrails Against Reverting To Older Revenue Inputs

If a run is meant to reproduce the primary benchmark, it should pass through `load_state_price_bundle()` and the price-application helpers listed above.

A run is not the primary benchmark if it:

- reads district MSP columns directly as the primary realized-price term;
- bypasses the official state-year realized-price table;
- bypasses the national-mean repair for unusable matched rows.

The generated audit outputs to inspect are:

- `../generated/figure2_main/figure2_main_price_coverage.csv`
- `../generated/primary_revenue_price_summary/primary_revenue_price_summary.csv`

## Explicitly Repaired Bad Direct-Price Cases

The current code handles these examples explicitly:

- official table:
  - `2017-18 | Kerala | Maize`
  - `2014-15 | Goa | Ragi`

- collaborator CSV sandbox:
  - `2017-18 | Tripura | Jowar`
  - `2017-18 | Kerala | Maize`
  - `2017-18 | Dadra and Nagar Haveli | Maize`

These rows no longer enter the benchmark as zero-price direct observations.
