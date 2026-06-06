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
- bajra: original=7286546.00 ha, optimized=9211500.79 ha, delta=1924954.79 ha (26.4%)
- jowar: original=2041066.00 ha, optimized=8514033.19 ha, delta=6472967.19 ha (317.1%)
- maize: original=7470863.00 ha, optimized=5439370.92 ha, delta=-2031492.08 ha (-27.2%)
- ragi: original=1103945.00 ha, optimized=893945.11 ha, delta=-209999.89 ha (-19.0%)
- rice: original=40085352.75 ha, optimized=33928922.74 ha, delta=-6156430.01 ha (-15.4%)

## Rabi crop-area totals
- bajra: original=279267.00 ha, optimized=1225676.93 ha, delta=946409.93 ha (338.9%)
- jowar: original=4197163.00 ha, optimized=5806551.58 ha, delta=1609388.58 ha (38.3%)
- maize: original=1968674.82 ha, optimized=3079850.95 ha, delta=1111176.13 ha (56.4%)
- ragi: original=91039.00 ha, optimized=41419.56 ha, delta=-49619.44 ha (-54.5%)
- rice: original=4459552.00 ha, optimized=4211855.03 ha, delta=-247696.97 ha (-5.6%)
- wheat: original=30731432.50 ha, optimized=27361774.27 ha, delta=-3369658.23 ha (-11.0%)

## Kharif largest non-diagonal transition-rule flows
- rice -> jowar: 3473656.0 ha
- rice -> bajra: 2908067.7 ha
- rice -> maize: 2609886.6 ha
- maize -> jowar: 2391290.1 ha
- maize -> rice: 2009400.6 ha
- bajra -> jowar: 1571344.1 ha
- maize -> bajra: 1123658.8 ha
- bajra -> rice: 786266.9 ha
- jowar -> bajra: 727141.0 ha
- ragi -> jowar: 421642.0 ha
- ragi -> maize: 393146.0 ha
- rice -> ragi: 326719.6 ha

## Rabi largest non-diagonal transition-rule flows
- wheat -> maize: 1342890.5 ha
- wheat -> rice: 1028657.5 ha
- wheat -> jowar: 1027953.2 ha
- wheat -> bajra: 781890.4 ha
- rice -> jowar: 713220.0 ha
- rice -> maize: 598778.3 ha
- maize -> jowar: 528975.0 ha
- jowar -> maize: 393313.4 ha
- jowar -> wheat: 323432.0 ha
- maize -> rice: 314772.2 ha
- maize -> wheat: 314413.0 ha
- rice -> wheat: 172428.1 ha

## Rice/wheat same-season audit
- rabi | wheat_loss_rice_gain: 73 districts, 1028657.5 ha co-occurring area
- rabi | rice_loss_wheat_gain: 54 districts, 172428.1 ha co-occurring area

Top states for rabi rice-loss / wheat-gain co-adjustment:
- west bengal: 97922.3 ha across 3 districts
- uttar pradesh: 19927.0 ha across 20 districts
- bihar: 15754.0 ha across 4 districts
- uttarakhand: 13949.0 ha across 2 districts
- madhya pradesh: 12070.0 ha across 17 districts
- assam: 9323.8 ha across 2 districts
- gujarat: 1856.0 ha across 1 districts
- odisha: 1340.0 ha across 1 districts
- meghalaya: 281.0 ha across 2 districts
- karnataka: 5.0 ha across 1 districts
