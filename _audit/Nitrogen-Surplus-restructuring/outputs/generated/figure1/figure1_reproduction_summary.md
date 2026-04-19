# Figure 1 reproduction audit

- Boundary source: `/Users/udit/Documents/Shekhar_Nature/revision_2/github_release/_audit/external/indian-district-boundaries/topojson/india-districts-2019-734.json`
- District-key coverage for panels a-c: 714/715
- Panels a-c use 2017 baseline metrics from the generated optimization exports, filtered to observed baseline area.
- Panel d uses the all-years sum of raw crop areas from `kharif_df.csv` and `rabi_df.csv`, scaled by `1e6`, so the plotted values are in million hectares.
- The remaining interpretation issue in panel d is temporal aggregation: the figure behaves like a cumulative study-period area panel rather than a single-year baseline area panel.

## Unresolved district names

- west bengal / barddhaman
