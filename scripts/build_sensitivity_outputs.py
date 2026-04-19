#!/usr/bin/env python3

import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


FOCUS_YEARS = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]
CROPS = ["Rice", "Wheat", "Jowar", "Bajra", "Maize", "Ragi"]
ALT_CROPS = ["Jowar", "Bajra", "Maize", "Ragi"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def latex_escape(text):
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
    }
    out = str(text)
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    return out


def fmt_num(x, digits=2):
    if x is None or x == "":
        return "--"
    return f"{x:.{digits}f}"


def fmt_pct(x, digits=1):
    if x is None or x == "":
        return "--"
    return f"{x * 100:.{digits}f}"


def tex_table(path, colspec, header, rows, caption=None, label=None, notes=None, size="small"):
    lines = []
    if size:
        lines.append(f"\\begin{{{size}}}")
    lines.append(f"\\begin{{tabular}}{{{colspec}}}")
    lines.append("\\toprule")
    lines.append(" & ".join(header) + r" \\")
    lines.append("\\midrule")
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    if notes:
        lines.append(r"\\[0.3em]")
        lines.append(r"\parbox{0.95\linewidth}{\footnotesize " + notes + "}")
    if size:
        lines.append(f"\\end{{{size}}}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("Usage: build_sensitivity_outputs.py <input_dir> <output_dir>", file=sys.stderr)
        return 2

    input_dir = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    unit_state = read_csv(input_dir / "reviewer_unit_price_state_year_inputs_2011_12_to_2017_18.csv")
    join_audit = read_csv(input_dir / "reviewer_unit_price_join_audit_2011_12_to_2017_18.csv")
    unit_all_india = read_csv(input_dir / "reviewer_unit_price_all_india_year_inputs_2011_12_to_2017_18.csv")
    msp_rows = read_csv(input_dir / "des_msp_selected_crops_2013_14_to_2017_18.csv")

    # Coverage summary
    coverage_rows = []
    by_crop_audit = defaultdict(list)
    for row in join_audit:
        by_crop_audit[row["crop_name"]].append(row)
    for crop in CROPS:
        rows = by_crop_audit[crop]
        matched = sum(int(r["matched_rows"]) for r in rows)
        missing = sum(int(r["missing_or_zero_production_rows"]) for r in rows)
        coverage_rows.append(
            {
                "crop_name": crop,
                "matched_state_years": matched,
                "missing_or_zero_state_years": missing,
                "mean_matched_states_per_year": statistics.mean(int(r["matched_rows"]) for r in rows),
                "mean_match_rate_pct": 100 * statistics.mean(float(r["match_rate"]) for r in rows),
                "min_match_rate_pct": 100 * min(float(r["match_rate"]) for r in rows),
                "max_match_rate_pct": 100 * max(float(r["match_rate"]) for r in rows),
            }
        )
    write_csv(
        output_dir / "coverage_summary.csv",
        list(coverage_rows[0].keys()),
        coverage_rows,
    )
    tex_table(
        output_dir / "coverage_summary.tex",
        "lrrrrr",
        [
            "Crop",
            "Direct match",
            "Other/zero-output",
            "Mean rate (\\%)",
            "Min rate (\\%)",
            "Max rate (\\%)",
        ],
        [
            [
                latex_escape(r["crop_name"]),
                f"{int(r['matched_state_years'])}",
                f"{int(r['missing_or_zero_state_years'])}",
                fmt_num(r["mean_match_rate_pct"], 1),
                fmt_num(r["min_match_rate_pct"], 1),
                fmt_num(r["max_match_rate_pct"], 1),
            ]
            for r in coverage_rows
        ],
        notes="Directly matched counts refer to state-year observations where the MoSPI value-output series could be joined to a positive DES APY production total. Unmatched/zero-output entries are retained in the source-series audit and do not imply missing modeled crop-area data in the 2017 optimization benchmark.",
    )

    # All-India unit prices in Rs/quintal
    all_india_lookup = {}
    for row in unit_all_india:
        if row["year"] in FOCUS_YEARS and row["unit_price_inr_per_tonne"]:
            all_india_lookup[(row["crop_name"], row["year"])] = float(row["unit_price_inr_per_tonne"]) / 10.0

    all_india_unit_rows = []
    for crop in CROPS:
        out = {"crop_name": crop}
        for year in FOCUS_YEARS:
            out[year] = all_india_lookup.get((crop, year))
        all_india_unit_rows.append(out)
    write_csv(
        output_dir / "all_india_unit_prices_rs_per_quintal_2013_14_to_2017_18.csv",
        ["crop_name"] + FOCUS_YEARS,
        all_india_unit_rows,
    )
    tex_table(
        output_dir / "all_india_unit_prices_rs_per_quintal_2013_14_to_2017_18.tex",
        "l" + "r" * len(FOCUS_YEARS),
        ["Crop"] + FOCUS_YEARS,
        [
            [latex_escape(r["crop_name"])] + [fmt_num(r[y], 1) for y in FOCUS_YEARS]
            for r in all_india_unit_rows
        ],
        notes="Derived unit prices are computed as MoSPI current-price value of output divided by summed matched DES APY state production, reported in rupees per quintal.",
    )

    # MSP comparison
    msp_lookup = {(r["crop_name"], r["year"]): float(r["msp_rs_per_quintal"]) for r in msp_rows}
    msp_ratio_rows = []
    for crop in CROPS:
        out = {"crop_name": crop}
        for year in FOCUS_YEARS:
            derived = all_india_lookup.get((crop, year))
            msp = msp_lookup.get((crop, year))
            out[year] = (derived / msp) if derived and msp else None
        msp_ratio_rows.append(out)
    write_csv(
        output_dir / "all_india_unit_price_to_msp_ratio_2013_14_to_2017_18.csv",
        ["crop_name"] + FOCUS_YEARS,
        msp_ratio_rows,
    )
    tex_table(
        output_dir / "all_india_unit_price_to_msp_ratio_2013_14_to_2017_18.tex",
        "l" + "r" * len(FOCUS_YEARS),
        ["Crop"] + FOCUS_YEARS,
        [
            [latex_escape(r["crop_name"])] + [fmt_num(r[y], 2) for y in FOCUS_YEARS]
            for r in msp_ratio_rows
        ],
        notes="Values greater than 1 indicate that the derived all-India realized unit price exceeds the corresponding national MSP in the downloaded DES table.",
    )

    # Terms of trade summary
    tot_rows = []
    for crop in ALT_CROPS:
        ratios_to_rice = []
        ratios_to_wheat = []
        for year in FOCUS_YEARS:
            if (crop, year) in all_india_lookup and ("Rice", year) in all_india_lookup:
                ratios_to_rice.append(all_india_lookup[(crop, year)] / all_india_lookup[("Rice", year)])
            if (crop, year) in all_india_lookup and ("Wheat", year) in all_india_lookup:
                ratios_to_wheat.append(all_india_lookup[(crop, year)] / all_india_lookup[("Wheat", year)])
        tot_rows.append(
            {
                "crop_name": crop,
                "mean_ratio_to_rice": statistics.mean(ratios_to_rice),
                "min_ratio_to_rice": min(ratios_to_rice),
                "max_ratio_to_rice": max(ratios_to_rice),
                "mean_ratio_to_wheat": statistics.mean(ratios_to_wheat),
                "min_ratio_to_wheat": min(ratios_to_wheat),
                "max_ratio_to_wheat": max(ratios_to_wheat),
            }
        )
    write_csv(output_dir / "terms_of_trade_summary_2013_14_to_2017_18.csv", list(tot_rows[0].keys()), tot_rows)
    tex_table(
        output_dir / "terms_of_trade_summary_2013_14_to_2017_18.tex",
        "lrrrrrr",
        ["Crop", "Mean/Rice", "Min/Rice", "Max/Rice", "Mean/Wheat", "Min/Wheat", "Max/Wheat"],
        [
            [
                latex_escape(r["crop_name"]),
                fmt_num(r["mean_ratio_to_rice"], 2),
                fmt_num(r["min_ratio_to_rice"], 2),
                fmt_num(r["max_ratio_to_rice"], 2),
                fmt_num(r["mean_ratio_to_wheat"], 2),
                fmt_num(r["min_ratio_to_wheat"], 2),
                fmt_num(r["max_ratio_to_wheat"], 2),
            ]
            for r in tot_rows
        ],
        notes="Ratios are computed from the derived all-India unit-price series. Values below 1 indicate a lower price benchmark than the reference crop.",
    )

    # State-level dispersion summary
    by_crop_values = defaultdict(list)
    for row in unit_state:
        if row["join_status"] == "matched" and row["unit_price_inr_per_kg"]:
            by_crop_values[row["crop_name"]].append(float(row["unit_price_inr_per_kg"]))
    dispersion_rows = []
    for crop in CROPS:
        vals = sorted(by_crop_values[crop])
        dispersion_rows.append(
            {
                "crop_name": crop,
                "matched_state_year_obs": len(vals),
                "median_rs_per_kg": statistics.median(vals),
                "p25_rs_per_kg": vals[len(vals) // 4],
                "p75_rs_per_kg": vals[(3 * len(vals)) // 4],
            }
        )
    write_csv(output_dir / "state_dispersion_summary.csv", list(dispersion_rows[0].keys()), dispersion_rows)
    tex_table(
        output_dir / "state_dispersion_summary.tex",
        "lrrrr",
        ["Crop", "Matched obs.", "Median (Rs/kg)", "P25", "P75"],
        [
            [
                latex_escape(r["crop_name"]),
                f"{int(r['matched_state_year_obs'])}",
                fmt_num(r["median_rs_per_kg"], 2),
                fmt_num(r["p25_rs_per_kg"], 2),
                fmt_num(r["p75_rs_per_kg"], 2),
            ]
            for r in dispersion_rows
        ],
        notes="Dispersion is calculated across matched state-year observations, pooling 2011-12 to 2017-18.",
    )

    # Short findings file for the LaTeX narrative
    rice_cov = next(r for r in coverage_rows if r["crop_name"] == "Rice")
    maize_cov = next(r for r in coverage_rows if r["crop_name"] == "Maize")
    wheat_cov = next(r for r in coverage_rows if r["crop_name"] == "Wheat")
    minor_cov = [r for r in coverage_rows if r["crop_name"] in {"Jowar", "Bajra", "Ragi"}]
    minor_cov_text = ", ".join(
        f"{r['crop_name']} {r['mean_match_rate_pct']:.1f}%"
        for r in minor_cov
    )
    findings = [
        "Key findings used in the standalone note:",
        f"- Rice has the strongest join coverage, with mean match rate {rice_cov['mean_match_rate_pct']:.1f}% across 2011-12 to 2017-18.",
        f"- Maize coverage is also reasonably strong at {maize_cov['mean_match_rate_pct']:.1f}% on average, whereas wheat is moderate at {wheat_cov['mean_match_rate_pct']:.1f}%.",
        f"- Minor cereal coverage is materially thinner: the mean match rates are {minor_cov_text}.",
        "- The derived all-India unit-price series does not imply a uniform coarse-cereal revenue premium over rice; Bajra and Maize stay below rice in every benchmark year, while Ragi is higher than wheat in each benchmark year and exceeds rice only in 2016-17.",
        "- Because the alternative price series is state-year and partly coverage-limited, it is more appropriate as a supplementary robustness exercise than as a replacement for the district-level baseline revenue specification in the main optimization.",
    ]
    (output_dir / "key_findings.txt").write_text("\n".join(findings) + "\n", encoding="utf-8")

    print(
        {
            "coverage_rows": len(coverage_rows),
            "all_india_unit_rows": len(all_india_unit_rows),
            "msp_ratio_rows": len(msp_ratio_rows),
            "terms_rows": len(tot_rows),
            "dispersion_rows": len(dispersion_rows),
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
