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

For Figure 3(b), baseline interstate alternate-cereal links (maize, ragi, bajra, jowar)
are preserved as the network topology. Source-wise optimized alternate trade is then scaled
from that baseline using:

optimized alternate trade = baseline alternate trade + alternate-calorie surplus +
change in rice+wheat interstate trade from the same source state.

Negative source totals are clipped to zero to avoid implying negative exports. Source states
with no baseline alternate-trade links are not assigned new destinations in this figure,
because the panel is intended as a conservative network rescaling rather than a new trade-allocation model.

Figure 3(b) displayed states: west bengal, andhra pradesh, assam, bihar, chhattisgarh, gujarat, haryana, karnataka, kerala, madhya pradesh, maharashtra, odisha, punjab, rajasthan, tamil nadu, telangana, uttar pradesh, uttarakhand.
Figure 3(c) displayed states: west bengal, andhra pradesh, assam, bihar, chhattisgarh, gujarat, haryana, jharkhand, jammu and kashmir, karnataka, kerala, madhya pradesh, maharashtra, nagaland, odisha, punjab, rajasthan, tamil nadu, uttar pradesh, chandigarh.

Alternate-network source states clipped to zero after the raw trade update: tripura, rajasthan, punjab, kerala, jharkhand, himachal pradesh, goa, delhi, dadra and nagar haveli.

