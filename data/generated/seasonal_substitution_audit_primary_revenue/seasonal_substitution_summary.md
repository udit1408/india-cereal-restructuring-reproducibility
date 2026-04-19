# Seasonal Substitution Audit

This audit uses the primary nitrogen-focused optimized area table generated under the
hybrid 2017-18 realized-price revenue benchmark. The optimization itself is seasonal:
kharif and rabi are solved
independently, and the annual Figure 2(d) is an aggregation of those two seasonal outputs.

- districts with baseline kharif wheat area: 0
- districts with baseline rabi rice area: 294

Key interpretation:

- There is no baseline kharif wheat in the primary area table, so any apparent annual
  rice-to-wheat crossover in the combined panel is an annual aggregation artifact rather than
  a kharif same-season substitution.
- Same-season rice-loss / wheat-gain co-adjustment is confined to the rabi solution and only
  occurs in districts where rabi rice is already present in the baseline system.
- The wheat-to-coarse-cereal reallocations visible in the rabi solution occur within a seasonal
  crop set that already contains rabi bajra, jowar, maize, and ragi in the observed baseline.

Top direct seasonal findings from the primary realized-price rebuild:

## Kharif crop-area totals
- bajra: original=7286546.00 ha, optimized=8414830.38 ha, delta=1128284.38 ha (15.5%)
- jowar: original=2041066.00 ha, optimized=7994134.39 ha, delta=5953068.39 ha (291.7%)
- maize: original=7470863.00 ha, optimized=11182688.32 ha, delta=3711825.32 ha (49.7%)
- ragi: original=1103945.00 ha, optimized=2593937.94 ha, delta=1489992.94 ha (135.0%)
- rice: original=40085352.75 ha, optimized=27802181.72 ha, delta=-12283171.03 ha (-30.6%)

## Rabi crop-area totals
- bajra: original=279267.00 ha, optimized=509607.24 ha, delta=230340.24 ha (82.5%)
- jowar: original=4197163.00 ha, optimized=5300316.60 ha, delta=1103153.60 ha (26.3%)
- maize: original=1968674.82 ha, optimized=2998186.24 ha, delta=1029511.42 ha (52.3%)
- ragi: original=91039.00 ha, optimized=221339.81 ha, delta=130300.81 ha (143.1%)
- rice: original=4459552.00 ha, optimized=4296359.28 ha, delta=-163192.72 ha (-3.7%)
- wheat: original=30731432.50 ha, optimized=28401319.15 ha, delta=-2330113.35 ha (-7.6%)

## Kharif largest non-diagonal transition-rule flows
- rice -> maize: 7680164.8 ha
- rice -> jowar: 3273673.9 ha
- rice -> bajra: 2107213.4 ha
- maize -> jowar: 1999473.5 ha
- rice -> ragi: 1925120.5 ha
- bajra -> jowar: 1627046.8 ha
- maize -> rice: 1588123.6 ha
- maize -> bajra: 1392295.2 ha
- bajra -> rice: 776580.0 ha
- jowar -> bajra: 609424.2 ha
- ragi -> maize: 465175.1 ha
- jowar -> maize: 432003.0 ha

## Rabi largest non-diagonal transition-rule flows
- wheat -> maize: 1450775.0 ha
- wheat -> jowar: 1051789.5 ha
- wheat -> rice: 867096.2 ha
- rice -> wheat: 561281.1 ha
- rice -> maize: 468565.7 ha
- maize -> rice: 404673.2 ha
- maize -> jowar: 372701.0 ha
- rice -> jowar: 369563.6 ha
- maize -> wheat: 362062.1 ha
- jowar -> maize: 306738.0 ha
- jowar -> wheat: 288889.6 ha
- wheat -> bajra: 235593.2 ha

## Rice/wheat same-season audit
- rabi | wheat_loss_rice_gain: 69 districts, 867096.2 ha co-occurring area
- rabi | rice_loss_wheat_gain: 60 districts, 561281.1 ha co-occurring area

Top states for rabi rice-loss / wheat-gain co-adjustment:
- west bengal: 489571.1 ha across 7 districts
- uttar pradesh: 19927.0 ha across 20 districts
- assam: 19342.0 ha across 2 districts
- uttarakhand: 13949.0 ha across 2 districts
- gujarat: 7878.0 ha across 6 districts
- madhya pradesh: 6200.0 ha across 15 districts
- bihar: 4133.0 ha across 5 districts
- meghalaya: 281.0 ha across 2 districts
- dadra and nagar haveli: 0.0 ha across 1 districts
