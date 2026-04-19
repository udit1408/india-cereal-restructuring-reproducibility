# India Cereal Restructuring Reproducibility

This repository is a reproducibility release for a district-level cereal crop restructuring analysis in India. It packages the audited workflow, shareable inputs, regenerated figure outputs, source-data tables, and a Dockerized rerun path needed to reproduce the public-facing computational results.

It is a reproducibility workflow, not a general-purpose Python library. The repository is organized around executable scripts, pinned dependencies, audited intermediate tables, and figure-level outputs.

## What Is Included

- scripted reruns for the main figure blocks and supplementary robustness outputs;
- shareable public-source inputs and benchmark tables in `data/input/`;
- regenerated outputs in `data/generated/` and `figures/manuscript_final/`;
- source-data exports in `submission_assets/source_data/`;
- an HTML reproducibility report in `submission_assets/audited_html_report/`;
- notebook walkthroughs that call the same scripted workflow;
- a Docker build path for containerized reruns.

## What Is Not Included

- article text and editorial documents;
- non-shareable private datasets.

## System Requirements

The workflow is intended for macOS and Linux and is pinned to Python 3.11 in the containerized path. A standard workstation is sufficient for the scripted reruns.

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

## Expected Outputs

After a full rerun, the main checkpoints are:

- `figures/manuscript_final/`
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
  - public-facing figure exports used by the reproducibility package.
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
