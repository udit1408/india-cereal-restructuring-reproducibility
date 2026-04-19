# Clean Reproduction Layer

This package is the start of a script-based reproduction workflow outside the original notebooks.

Current scope:

- standardized repository and archive-aware CSV loading
- fallback handling for rice and wheat trade inputs
- a first trade-stage export pipeline that materializes normalized inputs and key derived tables

The current script layer does not yet replace the optimization notebooks. It is intended to let us migrate the workflow in stages while keeping the intermediate outputs auditable.

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 -m repro trade-stage
```

By default this writes CSV outputs into `outputs/generated/trade_stage/`.

## Current dependency boundary

The trade-stage pipeline can read source data from the repository, from `code_data.zip`, or from generated outputs already produced by the optimization stage.

At present, these two optimization outputs are still upstream dependencies for the fully joined optimized-production tables:

- `nutrient_based_opt_cop_kharif.csv`
- `nitrogen_surplus_rbased_opt_cop_rabi.csv`

If they are missing, the exporter still writes the trade-stage outputs that are available and adds a `generated_dependency_status.csv` file describing the missing optimization-stage inputs.
