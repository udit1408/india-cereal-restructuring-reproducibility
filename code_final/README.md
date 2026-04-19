# Final Reproducibility Code

This folder is the authoritative code entry point for the audited reproducibility package. It deliberately separates the final workflow from exploratory notebooks, legacy rebuild attempts, and diagnostic scripts retained elsewhere for provenance.

## Authoritative Entry Point

Run the final audited workflow from the repository root:

```bash
./code_final/run_final_revision2_batch.sh
```

For the Docker/containerized runtime:

```bash
./code_final/run_final_revision2_container.sh
```

For a lightweight HTML-report refresh from already generated outputs:

```bash
./code_final/run_final_revision2_batch.sh --report-only
```

## What This Final Workflow Uses

The final workflow runs only the audited code path listed in `FINAL_CODE_MANIFEST.md`. It rebuilds the release figure and source-data assets under the primary 2017--18 realized-price revenue benchmark:

- Figure 1 audited reproduction from the repository checkout;
- Figure 2 primary realized-price rebuild, including the no-hard-cap Pareto frontier and panel-b bootstrap intervals;
- Figure 3 rebuild from the Figure 2 nitrogen-focused optimized district-area table;
- supplementary revenue, endpoint, frontier-envelope, and seasonal substitution robustness figures;
- Source Data workbook and zip package;
- exact SHA-256 synchronization of figure targets;
- HTML reproducibility report and manifest.

## What This Final Workflow Does Not Use

The following locations are provenance or diagnostics, not final-code entry points:

- `_audit/`: audited repository checkouts, notebook provenance, and old reconstruction notes;
- `figures/working_variants/`: intermediate figure files produced during the final run;
- `scripts/run_figure2_rebuilds.sh`, `scripts/run_all.sh`, and `scripts/sync_approved_figure2.sh`: older or narrower utilities retained for traceability;
- scripts beginning with `audit_`, `probe_`, or older `generate_figure2*` variants unless they are explicitly listed in `FINAL_CODE_MANIFEST.md`.

## Method Notation Alignment

`METHOD_NOTATION_MAP.md` maps the paper notation to the final code variables and functions. The most important alignment points are:

- the final model conserves total district-season cereal area;
- historical crop presence defines the feasible crop set, but hard district-crop historical maximum area caps are disabled in the main branch;
- the price variable inherited as `msp_per_prod` in older code is overwritten in the final workflow with the primary realized-price benchmark, using matched state-year realized prices where available and crop-wise realized-price/MSP fallback otherwise;
- the paper coefficient `\pi_{j,c}` corresponds to the code expression `msp_per_prod - cost_per_prod`, with unit conversion handled by the code's `0.01` factor because the code uses kg ha-1 yields and Rs quintal-1 prices.

Keep final workflow edits here or in the manifest-listed implementation scripts only. Treat all legacy notebooks and audit branches as read-only provenance unless a new audit is explicitly required.
