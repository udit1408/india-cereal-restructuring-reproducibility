# External Data Sources

This file records the external data provenance used in the reproducibility package.

## Included Shareable Inputs

The following shareable inputs are already bundled in `data/input/`:

- `des_apy_selected_crops_state_year_season_production_2011_12_to_2017_18.csv`
  - historical DES APY state-year-season production denominator used in the state-level realized-price benchmark.
- `des_cost_concepts.csv`
  - DES cost concept definitions used for the Methods and Supplementary clarification.
- `des_msp_selected_crops_2013_14_to_2017_18.csv`
  - MSP reference table used for benchmark fallback and comparison analyses.
- `state_realized_price_state_year_inputs_2011_12_to_2017_18.csv`
  - state-year realized unit-price inputs assembled from official value-of-output and production sources.
  - the filename retains its historical compatibility label, but this is the primary state-level realized-price input table bundled with the package.
- `all_india_realized_price_year_inputs_2011_12_to_2017_18.csv`
  - all-India realized price series used for crop-wise fallback scaling.
- `state_realized_price_join_audit_2011_12_to_2017_18.csv`
  - join audit showing matched and fallback benchmark coverage.
- `upag_public_snapshot_2026_04_19/*.json`
  - public UPAg endpoint snapshots captured during revision to verify current public-route availability and its lack of historical benchmark depth.

## Audited Repository Inputs

The audited repository copy under `_audit/Nitrogen-Surplus-restructuring/code_data/` contains the shareable tables inherited from the original analysis workflow, including:

- district-season crop tables;
- crop-wise water-demand and nitrogen-surplus coefficient tables;
- cost-of-production table used in the original workflow;
- trade-network and cultural-retention support tables.

These tables are included here because they are required by the final audited scripts and are already present in the original code/data repository used for the paper.

## External Public Sources Used By The Benchmark Workflow

The state-level realized-price benchmark and supporting clarifications draw on the following official public-source routes:

1. Ministry of Statistics and Programme Implementation (MoSPI), value of output in agriculture
   - used to assemble state-year realized value-of-output inputs for the revised revenue benchmark.
   - public route: `https://www.mospi.gov.in/publications-reports/innerpage/431`

2. Directorate of Economics and Statistics (DES), Agricultural Statistics at a Glance / APY public report route
   - used for the historical state-year production denominator and DES cost-of-production interpretation.

3. Unified Portal for Agricultural Statistics (UPAg) public homepage endpoints
   - checked to test whether the public route exposed the historical benchmark series needed for 2017--18;
   - current public endpoints exposed snapshot-style recent production views, not the required historical series.
   - public portal: `https://upag.gov.in/`

## Source Data

The exact figure-linked source data shipped with this repository is in:

- `submission_assets/source_data/Source Data.xlsx`
- `submission_assets/source_data/csv/`

These files are derived from the bundled inputs and audited generated outputs in this repository.
