# Nitrogen Crop Restructuring Reproducibility Package

This repository is a cleaned, reviewer-facing reproducibility package for the revised Nature Communications submission:

_Quantifying Environmental Co-Benefits of Nitrogen-Based Crop Restructuring and Its Implications on India's Interstate Trade Network_

It is built from the final audited workflow used for the revision. The package includes:

- the final figure-generation code path;
- Docker and local runners;
- the shareable input tables used in the revised analysis;
- current regenerated outputs for the main figures and supplementary robustness figures;
- the Source Data workbook and CSV exports aligned with the revised manuscript;
- figure-wise notebooks for stepwise inspection and reruns.

## Quick Start

Create a local environment and install the pinned dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run the full audited workflow locally:

```bash
./run_all.sh
```

Run the same workflow in Docker:

```bash
./run_docker.sh
```

Refresh only the HTML reproducibility report from existing outputs:

```bash
./run_all.sh --report-only
```

Run individual figure blocks:

```bash
./run_figure1.sh
./run_figure2.sh
./run_figure3.sh
./run_supplementary.sh
```

## Notebook Walkthrough

The `notebooks/` folder provides a figure-wise walkthrough:

- `00_environment_and_data.ipynb`
- `01_figure1.ipynb`
- `02_figure2.ipynb`
- `03_figure3.ipynb`
- `04_supplementary_and_source_data.ipynb`

These notebooks call the same audited scripts used by the batch runner. They do not reimplement the model logic.

## Repository Layout

- `code_final/`
  - authoritative batch runners, code manifest, and method-notation map.
- `container/`
  - Docker image definition and entrypoint.
- `scripts/`
  - implementation scripts used by the final workflow.
- `_audit/Nitrogen-Surplus-restructuring/`
  - audited code and shareable data tables inherited from the original repository checkout.
- `_audit/external/`
  - external boundary asset used by the audited Figure 1 rebuild.
- `data/input/`
  - revised revenue-benchmark, DES cost-concept, MSP, and public-source snapshot inputs.
- `data/generated/`
  - regenerated figure tables, bootstrap summaries, and supporting outputs.
- `figures/manuscript_final/`
  - manuscript-facing figure exports.
- `figures/working_variants/`
  - current composite and panel-level figure outputs produced by the audited scripts.
- `submission_assets/source_data/`
  - Source Data workbook, CSV exports, and zip package.
- `submission_assets/audited_html_report/`
  - HTML reproducibility report and machine-readable manifest.

## Figure-to-Code Map

| Figure block | Main command | Primary output | Source data |
|---|---|---|---|
| Figure 1 | `./run_figure1.sh` | `_audit/Nitrogen-Surplus-restructuring/outputs/generated/figure1/figure1_reproduced.png` | `submission_assets/source_data/csv/Fig1_abc.csv`, `submission_assets/source_data/csv/Fig1d_state_area.csv` |
| Figure 2 | `./run_figure2.sh` | `figures/working_variants/Figure2_equivalent.png` | `submission_assets/source_data/csv/Fig2a_pareto.csv` through `Fig2d_flows.csv` |
| Figure 3 | `./run_figure3.sh` | `figures/working_variants/Figure3_equivalent.png` | `submission_assets/source_data/csv/Fig3a_state_area.csv` through `Fig3c_nodes.csv` |
| Supplementary robustness block | `./run_supplementary.sh` | `figures/manuscript_final/si_*.png` | `submission_assets/source_data/csv/FigS*.csv`, `submission_assets/source_data/csv/TableS10_prices.csv` |

## Data Notes

This package includes the shareable inputs and derived tables needed to reproduce the revised figures. Official source provenance for the revenue benchmark, DES production denominator, cost concepts, and public production-route snapshot is summarized in [EXTERNAL_DATA_SOURCES.md](EXTERNAL_DATA_SOURCES.md).

The exact manuscript-linked Source Data package is included under `submission_assets/source_data/`.

## Output Verification

After a full run, the main checkpoints are:

- `submission_assets/audited_html_report/index.html`
- `submission_assets/audited_html_report/repro_manifest.json`
- `submission_assets/source_data/Source Data.xlsx`
- `figures/working_variants/Figure2_equivalent.png`
- `figures/working_variants/Figure3_equivalent.png`

## Scope Boundary

This repository is the cleaned reproducibility package only. It does not include the manuscript LaTeX submission package, track-change PDFs, or internal response-to-reviewer drafting files.
