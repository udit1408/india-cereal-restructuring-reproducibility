# Figure 1 reproduction audit

- Boundary source: `/Users/udit/Documents/Shekhar_Nature/revision_2/github_release/_audit/external/indian-district-boundaries/shapefile/india-districts-2019-734.shp`
- District-key coverage for panels a-c: 714/715
- Panels a-c use 2017 baseline metrics from the generated optimization exports, filtered to observed baseline area.
- Panel d uses the all-years sum of raw crop areas from `kharif_df.csv` and `rabi_df.csv`, scaled by `1e6`, so the plotted values are in million hectares.
- Panel d reassigns districts affected by historical state bifurcations to their current states before aggregation (Andhra Pradesh/Telangana, Madhya Pradesh/Chhattisgarh, Bihar/Jharkhand, Uttar Pradesh/Uttarakhand).

## Unresolved district names

- west bengal / barddhaman
