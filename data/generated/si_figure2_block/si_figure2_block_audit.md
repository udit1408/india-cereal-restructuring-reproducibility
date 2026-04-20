# SI figure-2 supporting block regeneration audit

This audit documents the rebuilt assets for Supplementary Figures S2, S3, and S4.
All three figures are now generated from the primary 2017-18 realized-price benchmark
used in the revised main text, rather than from the older district-MSP figure branch.
Archived district-MSP versions of these seasonal figures have been preserved separately in
`figures/manuscript_final/si_msp_s2_seasonal_pareto.*`,
`figures/manuscript_final/si_msp_s3_seasonal_tradeoffs.*`, and
`figures/manuscript_final/si_msp_s4_cultural_retention.*`, while the main MSP comparison block
remains documented later in Supplementary Figures S18-S19.

## Figure S2
- Source files: `data/generated/figure2_main/figure2_main_panel_a_rabi_by_alpha.csv` and
  `data/generated/figure2_main/figure2_main_panel_a_kharif_by_alpha.csv`.
- Plot content: decile alpha points from the primary kharif and rabi Pareto frontiers, with water-focused
  and nitrogen-focused endpoints highlighted explicitly.
- rabi: nitrogen surplus 2.715 to 3.053 Mt; water demand 90.638 to 102.584 BCM.
- kharif: nitrogen surplus 4.110 to 4.612 Mt; water demand 210.029 to 245.643 BCM.

## Figure S3
- Source logic: season-specific endpoint solves from `generate_figure2b_clean.py` with
  fixed district cropped area, substitution among historically observed cereals, no district-crop
  historical area caps, and the primary 2017-18 realized-price benchmark
  applied to the state price term before solving.
- Values below are changes relative to the baseline cereal allocation.
- kharif water:
  - Profit: +1.783%
  - Calorie: +10.230%
  - Nitrogen Surplus: -12.776%
  - Water Demand: -41.727%
- kharif nitrogen:
  - Profit: +4.781%
  - Calorie: +8.114%
  - Nitrogen Surplus: -22.263%
  - Water Demand: -31.846%
- rabi water:
  - Profit: +6.464%
  - Calorie: +6.595%
  - Nitrogen Surplus: +1.846%
  - Water Demand: -15.420%
- rabi nitrogen:
  - Profit: +1.459%
  - Calorie: +2.152%
  - Nitrogen Surplus: -9.435%
  - Water Demand: -4.273%

## Figure S4
- Source files: `data/generated/figure2_main/figure2_main_panel_c_kharif.csv` and
  `data/generated/figure2_main/figure2_main_panel_c_rabi.csv`.
- Plot content: nitrogen-surplus reduction as the state-level retained rice or wheat floor is relaxed.
- kharif: 11.989% reduction at full retention (0% substitution allowed) and 22.263% at full relaxation (100% substitution allowed).
- rabi: 7.312% reduction at full retention (0% substitution allowed) and 9.435% at full relaxation (100% substitution allowed).
