# India Cereal Restructuring Reproducibility

This repository is a reproducibility release for a district-level cereal crop restructuring analysis in India. It packages the audited workflow, shareable inputs, regenerated figure outputs, source-data tables, and a Dockerized rerun path needed to reproduce the public-facing computational results.

It is a reproducibility workflow, not a general-purpose Python library. The repository is organized around executable scripts, pinned dependencies, audited intermediate tables, and figure-level outputs.

## What Is Included

- scripted reruns for the main figure blocks and supplementary robustness outputs;
- shareable public-source inputs and benchmark tables in `data/input/`;
- regenerated outputs in `data/generated/`, `figures/manuscript_final/`, and `figures/supporting_analysis/`;
- source-data exports in `submission_assets/source_data/`;
- an HTML reproducibility report in `submission_assets/audited_html_report/`;
- notebook walkthroughs that call the same scripted workflow;
- a Docker build path for containerized reruns.

## System Requirements

The workflow is tested on macOS and Linux and is pinned to Python 3.11 in the containerized path. Windows users should run the workflow through Docker Desktop or WSL2. A standard workstation is sufficient for the scripted reruns.

Core Python dependencies are listed in [requirements.txt](requirements.txt) and include `numpy`, `pandas`, `matplotlib`, `PuLP`, `highspy`, `geopandas`, `pyogrio`, `pyproj`, `shapely`, `openpyxl`, and `pycirclize`.

## Quick Start

Create a local environment and install the pinned dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the full audited workflow:

```bash
./run_all.sh
```

Refresh only the reproducibility report from existing outputs:

```bash
./run_all.sh --report-only
```

## Docker Reproduction

Use Docker if you want the cleanest rerun path with a pinned Python base image:

```bash
./run_docker.sh --report-only
./run_docker.sh
```

The container path builds from [Dockerfile](Dockerfile), installs the pinned requirements, mounts the repository into `/workspace`, and writes outputs back into the host working tree.

## Figure-Level Entry Points

Run the main blocks independently:

```bash
./run_figure1.sh
./run_figure2.sh
./run_figure3.sh
./run_supplementary.sh
```

The root entry points delegate to the audited batch runners in [code_final](code_final/) and the implementation scripts in [scripts](scripts/).

## Canonical Manuscript Outputs

The manuscript-aligned figure files live in `figures/manuscript_final/`. The canonical article and cited supplementary assets are:

- `figures/manuscript_final/figure1_main_revision2.pdf`
- `figures/manuscript_final/figure2_main_revision2.pdf`
- `figures/manuscript_final/figure3_main_revision2.pdf`
- `figures/manuscript_final/si_s1_methodological_framework.png`
- `figures/manuscript_final/si_s2_seasonal_pareto.pdf`
- `figures/manuscript_final/si_s3_seasonal_tradeoffs.pdf`
- `figures/manuscript_final/si_s4_cultural_retention.pdf`
- `figures/manuscript_final/si_s5_original_trade_network_clean.pdf`
- `figures/manuscript_final/si_s6_state_boundaries.pdf`
- `figures/manuscript_final/si_s7_parametric_uncertainty.pdf`
- `figures/manuscript_final/si_s8_kharif_bootstrap_uncertainty.png`
- `figures/manuscript_final/si_s9_rabi_bootstrap_uncertainty.png`
- `figures/manuscript_final/si_s10_kharif_n_component_sensitivity.png`
- `figures/manuscript_final/si_s11_rabi_n_component_sensitivity.png`
- `figures/manuscript_final/si_s12_n_strategy_ghg_components.jpg`
- `figures/manuscript_final/si_s13_water_strategy_ghg_components.jpg`
- `figures/manuscript_final/si_s14_spatial_n_application.png`
- `figures/manuscript_final/si_s15_image_gnm_partition.png`
- `figures/manuscript_final/si_revenue_benchmark_robustness.pdf`
- `figures/manuscript_final/si_msp_benchmark_figure2.pdf`
- `figures/manuscript_final/si_msp_benchmark_figure3.pdf`
- `figures/manuscript_final/si_figure2a_frontier_bootstrap.pdf`
- `figures/manuscript_final/si_s21_seasonal_substitution_audit.pdf`

Auxiliary or non-manuscript figure exports are kept separately in `figures/supporting_analysis/`, `figures/archive_nonmanuscript/`, or `figures/working_variants/`.

## Expected Outputs

After a full rerun, the main checkpoints are:

- `figures/manuscript_final/`
- `figures/supporting_analysis/`
- `data/generated/`
- `submission_assets/source_data/Source Data.xlsx`
- `submission_assets/source_data/csv/`
- `submission_assets/audited_html_report/index.html`
- `submission_assets/audited_html_report/repro_manifest.json`

## Repository Layout

- `scripts/`
  - figure-generation, robustness-analysis, source-data, and report-generation scripts.
- `code_final/`
  - audited batch runners, manifest files, and notation maps.
- `container/`
  - container entrypoint and dependency lock-in for Docker reruns.
- `data/input/`
  - shareable benchmark inputs and public-source snapshots.
- `data/generated/`
  - regenerated tables, bootstrap summaries, audits, and figure-ready intermediates.
- `figures/manuscript_final/`
  - canonical manuscript and cited supplementary figure exports.
- `figures/supporting_analysis/`
  - generated support analyses that are useful for auditing the price benchmark but are not manuscript display items.
- `figures/archive_nonmanuscript/`
  - archived non-canonical comparison exports retained for provenance.
- `submission_assets/source_data/`
  - workbook and CSV exports aligned with the generated figures.
- `submission_assets/audited_html_report/`
  - human-readable and machine-readable reproducibility checks.
- `_audit/`
  - audited inherited checkout and static support assets needed by the final workflow.
- `notebooks/`
  - notebook walkthroughs that mirror the scripted run path.

## Figure 1 Note

Figure 1 is rebuilt through the audited reconstruction path bundled in `_audit/Nitrogen-Surplus-restructuring/`. The original historical checkout did not preserve a standalone public plotting script for that panel set, so this repository ships the audited reconstruction workflow together with its generated audit tables.

## Data Provenance

Public-source provenance for the bundled benchmark inputs is summarized in [EXTERNAL_DATA_SOURCES.md](EXTERNAL_DATA_SOURCES.md). The realized-price and production benchmark inputs shipped in `data/input/` are further documented in [data/input/README.md](data/input/README.md).

## License

This repository is released under the Apache 2.0 License. See [LICENSE](LICENSE).

## Citation

Software citation metadata is provided in [CITATION.cff](CITATION.cff).
