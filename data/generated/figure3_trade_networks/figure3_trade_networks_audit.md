# Figure 3 trade-network rebuild

This rebuild aligns Figure 3(b) and Figure 3(c) to the same approved nitrogen-focused
optimization branch used for the revised Figure 2(d): fixed district cropped area,
substitution among historically observed cereals, and the shared state calorie and
MSP-benchmarked income floors.

District-crop optimized production is reconstructed from the approved optimized-area table
using notebook-derived district yield and calorie coefficients, with historical-but-missing
district-crop options completed from state-crop and crop-level means before reconstruction.

District-crop combinations still unresolved after coefficient completion: 0

For Figure 3(c), interstate rice and wheat flows are rebuilt by scaling each source state's
2016-2018 average trade links in proportion to the change in that source state's optimized
versus baseline production for the corresponding crop. Same-state flows are excluded.

For Figure 3(b), positive rice-wheat calorie deficits on exporter-importer links are added
to the corresponding baseline alternate-cereal links. This allows new alternate-cereal
links to appear when a staple-deficit link exists but no baseline alternate-cereal link was
present. If the resulting outbound alternate trade from a source state exceeds its optimized
alternate-cereal production, all outbound alternate links from that source are scaled
proportionally to satisfy the exporter production-capacity constraint.

Figure 3(b) displayed states: west bengal, andhra pradesh, assam, bihar, chhattisgarh, haryana, jharkhand, karnataka, kerala, madhya pradesh, maharashtra, odisha, punjab, rajasthan, tamil nadu, telangana, uttar pradesh, uttarakhand.
Figure 3(c) displayed states: west bengal, andhra pradesh, assam, bihar, chhattisgarh, gujarat, haryana, jharkhand, jammu and kashmir, karnataka, kerala, madhya pradesh, maharashtra, nagaland, odisha, punjab, rajasthan, tamil nadu, uttar pradesh, chandigarh.

Alternate-network source states with capacity-limited outbound trade: kerala, goa, delhi.
New alternate-cereal links introduced: 253.
Largest new alternate-cereal links:
- chhattisgarh -> andhra pradesh: 1.778e+12 kcal
- chhattisgarh -> jharkhand: 1.632e+12 kcal
- chhattisgarh -> bihar: 1.009e+12 kcal
- chhattisgarh -> maharashtra: 9.307e+11 kcal
- odisha -> jharkhand: 7.153e+11 kcal
- rajasthan -> assam: 6.821e+11 kcal
- rajasthan -> uttar pradesh: 6.417e+11 kcal
- rajasthan -> bihar: 5.483e+11 kcal
- haryana -> maharashtra: 5.127e+11 kcal
- rajasthan -> maharashtra: 4.636e+11 kcal

