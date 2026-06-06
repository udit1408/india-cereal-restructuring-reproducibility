# SI figure-2 supporting block regeneration audit

This audit documents the rebuilt revision-2 assets for Supplementary Figures S2, S3, and S4.
All three figures are now generated from the primary 2017-18 official price-and-cost benchmark
used in the revised main text, rather than from the older district-MSP figure branch.
Archived district-MSP versions of these seasonal figures have been preserved separately in
`figures/manuscript_final/si_msp_s2_seasonal_pareto.*`,
`figures/manuscript_final/si_msp_s3_seasonal_tradeoffs.*`, and
`figures/manuscript_final/si_msp_s4_cultural_retention.*`, while the main MSP comparison block
remains documented later in Supplementary Figures S18-S19.

## Figure S2
- Source files: `data/generated/Figure2_equivalent/Figure2_equivalent_panel_a_rabi_by_alpha.csv` and
  `data/generated/Figure2_equivalent/Figure2_equivalent_panel_a_kharif_by_alpha.csv`.
- Plot content: decile alpha points from the primary kharif and rabi Pareto frontiers, with water-focused
  and nitrogen-focused endpoints highlighted explicitly.
- rabi: nitrogen surplus 2.711 to 3.062 Mt; water demand 92.130 to 104.417 BCM.
- kharif: nitrogen surplus 4.466 to 4.889 Mt; water demand 241.922 to 276.375 BCM.

## Figure S3
- Source logic: season-specific endpoint solves from `generate_figure2b_clean.py` with
  fixed district cropped area, substitution among historically observed cereals, no district-crop
  historical area caps, and the primary 2017-18 official price-and-cost benchmark
  applied to the revenue and production-cost terms before solving.
- Values below are changes relative to the baseline cereal allocation.
- kharif water:
  - Calorie: +4.804%
  - Nitrogen Surplus: -7.533%
  - Water Demand: -32.878%
- kharif nitrogen:
  - Calorie: +1.375%
  - Nitrogen Surplus: -15.540%
  - Water Demand: -23.319%
- rabi water:
  - Calorie: +4.544%
  - Nitrogen Surplus: +2.155%
  - Water Demand: -14.028%
- rabi nitrogen:
  - Calorie: +1.589%
  - Nitrogen Surplus: -9.551%
  - Water Demand: -2.562%

## Figure S4
- Source files: `data/generated/Figure2_equivalent/Figure2_equivalent_panel_c_kharif.csv` and
  `data/generated/Figure2_equivalent/Figure2_equivalent_panel_c_rabi.csv`.
- Plot content: nitrogen-surplus reduction as the state-level retained rice or wheat floor is relaxed.
- kharif: 11.407% reduction at full retention (0% substitution allowed) and 15.540% at full relaxation (100% substitution allowed).
- rabi: 6.568% reduction at full retention (0% substitution allowed) and 9.551% at full relaxation (100% substitution allowed).
