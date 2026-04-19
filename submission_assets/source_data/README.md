# Source Data package

This folder contains the Nature-style source-data package prepared for revision 2 of
"Quantifying Environmental Co-Benefits of Nitrogen-Based Crop Restructuring and Its
Implications on India's Interstate Trade Network."

Primary artifact:

- `Source Data.xlsx`: workbook containing figure-ready source data tables and the primary revenue-price summary table.

Supporting artifacts:

- `csv/`: CSV mirrors of the workbook sheets.
- `Source_Data_package.zip`: convenience archive of this folder for submission handling.

Workbook coverage:

- Main manuscript Figures 1 to 3.
- Supplementary Figures S2 to S5 and S16 to S21 introduced or revised during the current revision round.
- Supplementary Table S10 summarizing the primary realized-price revenue benchmark.

Sheet manifest:

| Sheet | Display item | Rows | Columns | CSV mirror | Relative source path |
| --- | --- | ---: | ---: | --- | --- |
| `Fig1_abc` | Figure 1a-c district metrics | 734 | 16 | `csv/Fig1_abc.csv` | `_audit/Nitrogen-Surplus-restructuring/outputs/generated/figure1/figure1_panel_abc_joined.csv` |
| `Fig1d_state_area` | Figure 1d state crop areas | 157 | 5 | `csv/Fig1d_state_area.csv` | `_audit/Nitrogen-Surplus-restructuring/outputs/generated/figure1/figure1_panel_d_state_area.csv` |
| `Fig2a_pareto` | Figure 2a Pareto frontier points | 101 | 31 | `csv/Fig2a_pareto.csv` | `data/generated/Figure2_equivalent/Figure2_equivalent_panel_a_combined_by_alpha.csv` |
| `Fig2b_values` | Figure 2b deterministic endpoint values | 20 | 7 | `csv/Fig2b_values.csv` | `data/generated/Figure2_equivalent/Figure2_equivalent_panel_b_values.csv` |
| `Fig2b_whiskers` | Figure 2b whisker summary | 20 | 16 | `csv/Fig2b_whiskers.csv` | `data/generated/Figure2_equivalent/panel_b_bootstrap/Figure2_equivalent_panel_b_bootstrap_summary.csv` |
| `Fig2c_retention` | Figure 2c retention-constraint sweep | 11 | 10 | `csv/Fig2c_retention.csv` | `data/generated/Figure2_equivalent/Figure2_equivalent_panel_c_combined.csv` |
| `Fig2d_flows` | Figure 2d crop-transition flows | 36 | 4 | `csv/Fig2d_flows.csv` | `data/generated/Figure2_equivalent/Figure2_equivalent_panel_d_transition_long.csv` |
| `Fig2d_areas` | Figure 2d optimized area table | 4247 | 6 | `csv/Fig2d_areas.csv` | `data/generated/Figure2_equivalent/Figure2_equivalent_panel_d_optimized_areas.csv` |
| `FigS2_seasonal` | Supplementary Figure S2 seasonal Pareto points | 22 | 4 | `csv/FigS2_seasonal.csv` | `data/generated/si_figure2_block/si_s2_seasonal_pareto_points.csv` |
| `FigS3_tradeoffs` | Supplementary Figure S3 seasonal endpoint trade-offs | 40 | 6 | `csv/FigS3_tradeoffs.csv` | `data/generated/si_figure2_block/si_s3_seasonal_tradeoffs.csv` |
| `FigS4_retention` | Supplementary Figure S4 seasonal retention sweep | 22 | 15 | `csv/FigS4_retention.csv` | `data/generated/si_figure2_block/si_s4_cultural_retention.csv` |
| `FigS5a_alt_edges` | Supplementary Figure S5a observed alternative-cereal trade edges | 95 | 3 | `csv/FigS5a_alt_edges.csv` | `data/generated/si_s5_original_trade_network/si_s5_original_alt_trade_edges.csv` |
| `FigS5a_alt_labels` | Supplementary Figure S5a displayed state labels | 93 | 3 | `csv/FigS5a_alt_labels.csv` | `data/generated/si_s5_original_trade_network/si_s5_original_alt_trade_fromto_displayed.csv` |
| `FigS5b_rw_edges` | Supplementary Figure S5b observed rice-wheat trade edges | 430 | 3 | `csv/FigS5b_rw_edges.csv` | `data/generated/si_s5_original_trade_network/si_s5_original_rice_wheat_trade_edges.csv` |
| `FigS5b_rw_labels` | Supplementary Figure S5b displayed state labels | 283 | 3 | `csv/FigS5b_rw_labels.csv` | `data/generated/si_s5_original_trade_network/si_s5_original_rice_wheat_trade_fromto_displayed.csv` |
| `Fig3a_state_area` | Figure 3a displayed state totals | 81 | 7 | `csv/Fig3a_state_area.csv` | `data/generated/Figure3_equivalent/Figure3_equivalent_panel_a_display_states.csv` |
| `Fig3b_edges` | Figure 3b alternative-cereal trade edges | 988 | 8 | `csv/Fig3b_edges.csv` | `data/generated/Figure3_equivalent/Figure3_equivalent_panel_b_alt_trade_edges.csv` |
| `Fig3b_nodes` | Figure 3b alternative-cereal node flows | 32 | 2 | `csv/Fig3b_nodes.csv` | `data/generated/Figure3_equivalent/Figure3_equivalent_panel_b_alt_node_flows.csv` |
| `Fig3c_edges` | Figure 3c rice-wheat trade edges | 1260 | 5 | `csv/Fig3c_edges.csv` | `data/generated/Figure3_equivalent/Figure3_equivalent_panel_c_rw_trade_edges.csv` |
| `Fig3c_nodes` | Figure 3c rice-wheat node flows | 36 | 2 | `csv/Fig3c_nodes.csv` | `data/generated/Figure3_equivalent/Figure3_equivalent_panel_c_rw_node_flows.csv` |
| `FigS16a_ratio` | Supplementary Figure S16a realized price / MSP ratios | 6 | 6 | `csv/FigS16a_ratio.csv` | `data/generated/all_india_unit_price_to_msp_ratio_2013_14_to_2017_18.csv` |
| `FigS16b_trade` | Supplementary Figure S16b terms of trade summary | 4 | 7 | `csv/FigS16b_trade.csv` | `data/generated/terms_of_trade_summary_2013_14_to_2017_18.csv` |
| `TableS10_prices` | Supplementary Table S10 primary revenue price summary | 6 | 7 | `csv/TableS10_prices.csv` | `data/generated/primary_revenue_price_summary/primary_revenue_price_summary.csv` |
| `FigS17_values` | Supplementary Figure S17 endpoint sensitivity | 120 | 9 | `csv/FigS17_values.csv` | `data/generated/si_revenue_benchmark_endpoint_sensitivity/si_revenue_benchmark_endpoint_sensitivity_values.csv` |
| `FigS18a_pareto_cmp` | Supplementary Figure S18a MSP comparison Pareto points | 101 | 33 | `csv/FigS18a_pareto_cmp.csv` | `data/generated/figure2a_no_historical_cap_core_combined_by_alpha.csv` |
| `FigS18b_values_cmp` | Supplementary Figure S18b MSP comparison endpoint values | 20 | 6 | `csv/FigS18b_values_cmp.csv` | `data/generated/figure2b_no_historical_cap_core_values.csv` |
| `FigS18b_whisk_cmp` | Supplementary Figure S18b MSP comparison whiskers | 20 | 14 | `csv/FigS18b_whisk_cmp.csv` | `data/generated/figure2b_no_historical_cap_core_whiskers/figure2b_no_historical_cap_core_whiskers_summary.csv` |
| `FigS18c_retent_cmp` | Supplementary Figure S18c MSP comparison retention sweep | 11 | 10 | `csv/FigS18c_retent_cmp.csv` | `data/generated/figure2c/combined_no_historical_caps.csv` |
| `FigS18d_flows_cmp` | Supplementary Figure S18d MSP comparison transition flows | 36 | 4 | `csv/FigS18d_flows_cmp.csv` | `data/generated/figure2d_no_historical_cap_core/figure2d_no_historical_cap_core_transition_long.csv` |
| `FigS18d_areas_cmp` | Supplementary Figure S18d MSP comparison optimized areas | 4247 | 6 | `csv/FigS18d_areas_cmp.csv` | `data/generated/figure2d_no_historical_cap_core/figure2d_no_historical_cap_core_optimized_areas.csv` |
| `FigS19a_state_cmp` | Supplementary Figure S19a MSP comparison state areas | 81 | 7 | `csv/FigS19a_state_cmp.csv` | `data/generated/figure3a_state_area_comparison/figure3a_state_area_comparison_display_states.csv` |
| `FigS19b_edges_cmp` | Supplementary Figure S19b MSP comparison alt-cereal edges | 988 | 8 | `csv/FigS19b_edges_cmp.csv` | `data/generated/figure3_trade_networks/figure3b_alt_trade_edges_clean.csv` |
| `FigS19b_nodes_cmp` | Supplementary Figure S19b MSP comparison alt-cereal nodes | 32 | 2 | `csv/FigS19b_nodes_cmp.csv` | `data/generated/figure3_trade_networks/figure3b_alt_node_flows_clean.csv` |
| `FigS19c_edges_cmp` | Supplementary Figure S19c MSP comparison rice-wheat edges | 1260 | 5 | `csv/FigS19c_edges_cmp.csv` | `data/generated/figure3_trade_networks/figure3c_rice_wheat_trade_edges_clean.csv` |
| `FigS19c_nodes_cmp` | Supplementary Figure S19c MSP comparison rice-wheat nodes | 36 | 2 | `csv/FigS19c_nodes_cmp.csv` | `data/generated/figure3_trade_networks/figure3c_rice_wheat_node_flows_clean.csv` |
| `FigS20_frontier` | Supplementary Figure S20 realized-price frontier envelope summary | 101 | 19 | `csv/FigS20_frontier.csv` | `data/generated/Figure2_equivalent_frontier_bootstrap/Figure2_equivalent_frontier_bootstrap_summary.csv` |
| `FigS21_sum` | Supplementary Figure S21 primary realized-price seasonal transition summary | 24 | 5 | `csv/FigS21_sum.csv` | `data/generated/seasonal_substitution_audit_primary_revenue/seasonal_top_non_diagonal_transitions.csv` |
| `FigS21_flags` | Supplementary Figure S21 primary realized-price district-season flags | 127 | 9 | `csv/FigS21_flags.csv` | `data/generated/seasonal_substitution_audit_primary_revenue/district_season_rice_wheat_flags.csv` |

The broader public input datasets and repository-level reproducibility workflow are described separately in the manuscript Data Availability and Code Availability statements.
