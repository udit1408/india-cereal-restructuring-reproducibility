# Final Code Manifest

This manifest defines the final audited code path. Files listed here are the only implementation files used by the final batch. Other scripts and notebooks in the repository are retained for provenance, diagnostics, or earlier reconstruction attempts.

## Entry Points

| Purpose | File |
|---|---|
| Final local batch runner | `code_final/run_final_revision2_batch.sh` |
| Final Docker runner | `code_final/run_final_revision2_container.sh` |
| Docker image definition | `container/Dockerfile` |
| Docker entrypoint | `container/entrypoint.sh` |
| Docker Python dependencies | `container/requirements.txt` |

## Final Analysis Modules

| Step | Implementation file | Main outputs |
|---|---|---|
| Trade-stage normalization | `_audit/Nitrogen-Surplus-restructuring/repro/trade_stage.py` via `python -m repro trade-stage` | `_audit/Nitrogen-Surplus-restructuring/outputs/generated/trade_stage/` |
| Figure 1 reproduction | `_audit/Nitrogen-Surplus-restructuring/repro/figure1.py` via `python -m repro figure1` | `_audit/Nitrogen-Surplus-restructuring/outputs/generated/figure1/` |
| Figure 2 primary realized-price rebuild | `scripts/generate_Figure2_equivalent.py` | `figures/working_variants/Figure2_equivalent.*`; `data/generated/Figure2_equivalent/` |
| Supplementary Figure 2 supporting block | `scripts/generate_si_figure2_supporting_block.py` | `figures/manuscript_final/si_figure2_supporting_block.*` |
| Figure 3 primary realized-price rebuild | `scripts/generate_Figure3_equivalent.py` | `figures/working_variants/Figure3_equivalent.*`; `data/generated/Figure3_equivalent/` |
| Seasonal substitution audit | `scripts/generate_seasonal_substitution_audit.py` | `data/generated/seasonal_substitution_audit_primary_revenue/`; `figures/manuscript_final/si_s21_seasonal_substitution_audit.*` |
| Revenue robustness SI figure | `scripts/generate_si_revenue_robustness_figure.py` | `figures/manuscript_final/si_revenue_benchmark_robustness.*` |
| Revenue endpoint sensitivity SI figure | `scripts/generate_si_revenue_benchmark_endpoint_sensitivity.py` | `figures/manuscript_final/si_revenue_benchmark_endpoint_sensitivity.*` |
| Hybrid revenue-profit SI figure | `scripts/generate_si_hybrid_revenue_profit_sensitivity.py` | `figures/manuscript_final/si_hybrid_revenue_profit_sensitivity.*` |
| Figure 2(a) frontier-envelope SI figure | `scripts/generate_si_figure2a_frontier_bootstrap.py` | `figures/manuscript_final/si_figure2a_frontier_bootstrap.*` |
| Source Data package | `scripts/build_source_data_package.py` | `submission_assets/source_data/` |
| HTML reproducibility report | `scripts/generate_audited_html_report.py` | `submission_assets/audited_html_report/` |

## Final Outputs

| Output class | Canonical location |
|---|---|
| Release figure PDFs/PNGs | `figures/manuscript_final/` |
| Generated analysis/source tables | `data/generated/` |
| Source Data package | `submission_assets/source_data/` |
| HTML reproducibility report | `submission_assets/audited_html_report/index.html` |
| Machine-readable reproducibility manifest | `submission_assets/audited_html_report/repro_manifest.json` |

## Legacy Boundary

Do not use these as final workflow entry points:

| Legacy or diagnostic path | Reason |
|---|---|
| `_audit/Nitrogen-Surplus-restructuring/*.ipynb` | Original notebook provenance; paths and intermediate exports are not the cleaned final workflow. |
| `figures/legacy_reference/` | Previous-submission figure references only. |
| `scripts/run_figure2_rebuilds.sh` | Figure 2 audit runner with cap variants and legacy-faithful diagnostics. |
| `scripts/run_all.sh` | Earlier reviewer-data robustness note runner, not the final full batch. |
| `scripts/generate_figure2b_clean.py`, `generate_figure2d_clean.py`, `generate_figure2c.py` when run directly | Implementation utilities with legacy defaults; the final workflow calls them through `generate_Figure2_equivalent.py` with `use_historical_caps=False` and the primary revenue benchmark wired in. |
| `scripts/audit_*`, `probe_*`, and `bootstrap_*` files not called by the final runner | Diagnostic scripts retained for traceability. |

If a future change needs to become part of the final code path, update this manifest, `METHOD_NOTATION_MAP.md`, and the final batch runner in the same commit.
