# Reviewer 6 Seasonal Substitution Audit

This audit uses the approved nitrogen-focused optimized area table from the current
revision-2 rebuild. The optimization itself is seasonal: kharif and rabi are solved
independently, and the annual Figure 2(d) is an aggregation of those two seasonal outputs.

- districts with baseline kharif wheat area: 0
- districts with baseline rabi rice area: 294

Key interpretation:

- There is no baseline kharif wheat in the approved area table, so any apparent annual
  rice-to-wheat crossover in the combined panel is an annual aggregation artifact rather than
  a kharif same-season substitution.
- Same-season rice-loss / wheat-gain co-adjustment is confined to the rabi solution and only
  occurs in districts where rabi rice is already present in the baseline system.
- The wheat-to-coarse-cereal reallocations visible in the rabi solution occur within a seasonal
  crop set that already contains rabi bajra, jowar, maize, and ragi in the observed baseline.

Top direct seasonal findings from the approved rebuild:

## Kharif crop-area totals
- bajra: original=7286546.00 ha, optimized=9614987.57 ha, delta=2328441.57 ha (32.0%)
- jowar: original=2041066.00 ha, optimized=9220434.87 ha, delta=7179368.87 ha (351.7%)
- maize: original=7470863.00 ha, optimized=15892925.19 ha, delta=8422062.19 ha (112.7%)
- ragi: original=1103945.00 ha, optimized=1773893.82 ha, delta=669948.82 ha (60.7%)
- rice: original=40085352.75 ha, optimized=21485531.30 ha, delta=-18599821.45 ha (-46.4%)

## Rabi crop-area totals
- bajra: original=279267.00 ha, optimized=913963.50 ha, delta=634696.50 ha (227.3%)
- jowar: original=4197163.00 ha, optimized=5123268.35 ha, delta=926105.35 ha (22.1%)
- maize: original=1968674.82 ha, optimized=4258241.26 ha, delta=2289566.44 ha (116.3%)
- ragi: original=91039.00 ha, optimized=180549.28 ha, delta=89510.28 ha (98.3%)
- rice: original=4459552.00 ha, optimized=2619791.99 ha, delta=-1839760.01 ha (-41.3%)
- wheat: original=30731432.50 ha, optimized=28631313.93 ha, delta=-2100118.57 ha (-6.8%)

## Kharif largest non-diagonal transition-rule flows
- rice -> maize: 11151357.3 ha
- rice -> jowar: 4556825.7 ha
- rice -> bajra: 3605769.9 ha
- maize -> jowar: 2009489.3 ha
- bajra -> jowar: 1653798.1 ha
- maize -> bajra: 1284208.5 ha
- maize -> rice: 1134742.6 ha
- rice -> ragi: 1088145.4 ha
- bajra -> maize: 866276.3 ha
- jowar -> bajra: 647093.3 ha
- jowar -> maize: 597862.6 ha
- ragi -> maize: 466538.8 ha

## Rabi largest non-diagonal transition-rule flows
- wheat -> maize: 1690116.2 ha
- rice -> maize: 1231701.5 ha
- wheat -> jowar: 844938.4 ha
- rice -> wheat: 686360.4 ha
- wheat -> bajra: 545003.0 ha
- maize -> jowar: 462045.8 ha
- jowar -> maize: 422828.2 ha
- wheat -> rice: 420585.2 ha
- maize -> wheat: 345512.4 ha
- jowar -> wheat: 339590.0 ha
- rice -> jowar: 326556.1 ha
- maize -> rice: 171622.2 ha

## Rice/wheat same-season audit
- rabi | rice_loss_wheat_gain: 69 districts, 686360.4 ha co-occurring area
- rabi | wheat_loss_rice_gain: 51 districts, 420585.2 ha co-occurring area

Top states for rabi rice-loss / wheat-gain co-adjustment:
- west bengal: 600517.1 ha across 8 districts
- uttar pradesh: 25761.0 ha across 21 districts
- assam: 19342.0 ha across 2 districts
- uttarakhand: 13953.0 ha across 3 districts
- madhya pradesh: 11410.0 ha across 16 districts
- gujarat: 9277.0 ha across 8 districts
- bihar: 2410.0 ha across 2 districts
- nagaland: 1596.0 ha across 1 districts
- odisha: 1340.0 ha across 1 districts
- dadra and nagar haveli: 409.0 ha across 1 districts
