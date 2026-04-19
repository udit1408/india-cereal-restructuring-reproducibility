# No-Historical-Cap Endpoint Comparison

The original `figure2d_no_historical_cap_core` rebuild allows allocation into district-crop
choices with zero yield and/or zero calorie coefficients when those crops remain in the
admissible crop list for a district-season.

Using the approved core rebuild, the summed optimized area assigned to such zero-coefficient
district-crop combinations is `9,550,434.97 ha`.

After filtering the district-season crop choice set to entries with a valid coefficient bundle
before solving, the corrected `figure2d_no_historical_cap_valid_coeffs` branch assigns
`0.00 ha` to zero-coefficient choices.

The national nitrogen-focused endpoint check from the two branches is:

- original no-cap core rebuild: `6.511651 Tg N`, `298.054182 BCM`
- corrected valid-coefficient rebuild: `6.994607 Tg N`, `445.122227 BCM`

This means the coefficient-screening repair is not cosmetic. It materially changes the
water-demand endpoint and should be treated as a model correction rather than a display-only
adjustment.

Examples of district-crop reallocations removed by the coefficient-screening repair include:

- `rajasthan / sikar / jowar`: `271,297 ha` -> `0 ha`
- `odisha / bargarh / ragi`: `233,513 ha` -> `0 ha`
- `tamil nadu / thiruvarur / maize`: `170,956 ha` -> `0 ha`

In the corrected branch, these areas are reassigned among crop options with valid coefficients
within the same district-season optimization problem.
