# Figure 2(a) reproduction summary

The combined frontier follows the legacy notebook logic in `rabi_kharif_plot_perito_combined.ipynb`,
which concatenates the kharif and rabi season Pareto tables and averages `Objective Nitrogen` and
`Objective Water` by alpha before converting them to Mt and BCM, respectively.

Season-level provenance:
- `kharif_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv`: loaded existing generated CSV
- `rabi_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv`: loaded existing generated CSV

Generated frontier endpoints:
- alpha=0.00: nitrogen=3.508270e+09, water=1.239837e+11
- alpha=1.00: nitrogen=3.166531e+09, water=1.420987e+11

Cached notebook output endpoints:
- alpha=0.00: nitrogen=2.853118e+09, water=1.159904e+11
- alpha=1.00: nitrogen=2.530120e+09, water=1.350547e+11
