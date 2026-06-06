# SI primary-revenue uncertainty audit

Scenario year: 2017-18
Bootstrap iterations per season: 500
Bootstrap seed: 42

This workflow regenerates Supplementary Figures S8-S11 from the same official
2017-18 realized-price and state-crop C2 cost benchmark used in the main Figure 2 branch.
The seasonal uncertainty bars (S8-S9) use the nitrogen-focused endpoint only and propagate
district-level coefficient uncertainty through water-demand, net-nitrogen, and net-phosphorus
coefficients. The component-sensitivity panels (S10-S11) apply one-at-a-time +/-10% changes
to the four nitrogen-input components that sum into net nitrogen application.

Outputs:
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/kharif_bootstrap_iterations.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/kharif_bootstrap_summary.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/figures/manuscript_final/si_s8_kharif_bootstrap_uncertainty.png
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/kharif_component_sensitivity.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/figures/manuscript_final/si_s10_kharif_n_component_sensitivity.png
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/rabi_bootstrap_iterations.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/rabi_bootstrap_summary.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/figures/manuscript_final/si_s9_rabi_bootstrap_uncertainty.png
- /Users/udit/Documents/Shekhar_Nature/revision_2/data/generated/si_uncertainty_primary_revenue/rabi_component_sensitivity.csv
- /Users/udit/Documents/Shekhar_Nature/revision_2/figures/manuscript_final/si_s11_rabi_n_component_sensitivity.png
