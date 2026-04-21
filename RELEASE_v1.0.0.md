# v1.0.0

Initial public reproducibility release.

## What is included

- audited scripted workflow for the main figure blocks and cited supplementary outputs;
- shareable public input tables and benchmark datasets under `data/input/`;
- regenerated figure-ready outputs under `data/generated/` and `figures/manuscript_final/`;
- source-data workbook and CSV mirrors under `submission_assets/source_data/`;
- audited HTML reproducibility report under `submission_assets/audited_html_report/`;
- Dockerized rerun path for containerized reproduction.

## Main entry points

- `./run_all.sh`
- `./run_figure1.sh`
- `./run_figure2.sh`
- `./run_figure3.sh`
- `./run_supplementary.sh`
- `./run_docker.sh`

## Key outputs

- `figures/manuscript_final/figure1_main_revision2.pdf`
- `figures/manuscript_final/figure2_main_revision2.pdf`
- `figures/manuscript_final/figure3_main_revision2.pdf`
- `submission_assets/source_data/Source Data.xlsx`
- `submission_assets/audited_html_report/index.html`

## Notes

- This release is organized as a reproducibility workflow rather than as a general-purpose software library.
- Public provenance for bundled inputs is summarized in `EXTERNAL_DATA_SOURCES.md`.
- Citation metadata is provided in `CITATION.cff`.
- Zenodo release metadata is provided in `.zenodo.json`.
