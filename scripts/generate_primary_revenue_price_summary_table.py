#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
OUT_DIR = ROOT / "data" / "generated" / "primary_revenue_price_summary"
OUT_CSV = OUT_DIR / "primary_revenue_price_summary.csv"
OUT_TEX = OUT_DIR / "primary_revenue_price_summary.tex"
OUT_AUDIT = OUT_DIR / "primary_revenue_price_summary_audit.md"

SCENARIO_YEAR = "2017-18"
CROP_ORDER = ["rice", "wheat", "maize", "jowar", "bajra", "ragi"]
CROP_LABELS = {
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "jowar": "Jowar",
    "bajra": "Bajra",
    "ragi": "Ragi",
}


def configure_imports() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(AUDIT_ROOT))


def format_number(value: float, decimals: int | None = 0) -> str:
    if pd.isna(value):
        return "--"
    numeric = float(value)
    if decimals is None:
        decimals = 0 if abs(numeric - round(numeric)) < 1e-9 else 1
    return f"{numeric:,.{decimals}f}"


def build_summary() -> pd.DataFrame:
    configure_imports()
    from generate_figure2b_clean import SEASON_NOTEBOOKS, build_context
    from official_price_benchmark import (
        canon,
        load_price_bundle,
    )
    from repro.config import default_layout

    layout = default_layout(AUDIT_ROOT)
    price_df, _, state_price_lookup, national_price_lookup, _ = load_price_bundle()

    records: list[dict[str, object]] = []
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        context = build_context(layout, season, notebook_name)
        current_area = context["current_cereal_area"]

        for key, msp_value in context["msp_per_prod"].items():
            state, district, crop = key
            crop_key = str(crop).strip().lower()
            if crop_key not in CROP_ORDER:
                continue

            lookup_key = (SCENARIO_YEAR, canon(state), crop_key)
            direct_price = state_price_lookup.get(lookup_key)
            national_price = national_price_lookup.get((SCENARIO_YEAR, crop_key))
            if direct_price is not None:
                benchmark_price = float(direct_price)
                price_source = "direct_state_year"
            elif national_price is not None:
                benchmark_price = float(national_price)
                price_source = "national_mean_fill"
            else:
                raise KeyError(
                    f"Missing official realized-price benchmark for year={SCENARIO_YEAR}, state={state}, crop={crop}"
                )

            records.append(
                {
                    "season": season,
                    "state": canon(state),
                    "district": district,
                    "crop": crop_key,
                    "baseline_area_ha": float(current_area.get(key, 0.0)),
                    "msp_reference_rs_per_quintal": float(msp_value),
                    "national_mean_price_rs_per_quintal": float(national_price)
                    if national_price is not None
                    else float("nan"),
                    "benchmark_price_rs_per_quintal": benchmark_price,
                    "direct_realized_price_used": direct_price is not None,
                    "national_mean_fill_used": direct_price is None and national_price is not None,
                    "price_source": price_source,
                }
            )

    detail = pd.DataFrame.from_records(records)
    rows: list[dict[str, object]] = []
    for crop in CROP_ORDER:
        crop_df = detail[detail["crop"] == crop].copy()
        if crop_df.empty:
            continue

        state_df = (
            crop_df.groupby(["state", "direct_realized_price_used"], as_index=False)[
                "baseline_area_ha"
            ]
            .sum()
            .sort_values(["state", "direct_realized_price_used"])
        )
        direct_states = int(
            state_df[state_df["direct_realized_price_used"]]["state"].nunique()
        )
        total_states = int(state_df["state"].nunique())
        total_area = float(crop_df["baseline_area_ha"].sum())
        direct_area = float(
            crop_df.loc[crop_df["direct_realized_price_used"], "baseline_area_ha"].sum()
        )
        price_weighted = (
            float(
                (crop_df["benchmark_price_rs_per_quintal"] * crop_df["baseline_area_ha"]).sum()
            )
            / total_area
            if total_area > 0
            else float("nan")
        )

        rows.append(
            {
                "crop": CROP_LABELS[crop],
                "msp_reference_rs_per_quintal": crop_df[
                    "msp_reference_rs_per_quintal"
                ].median(),
                "national_mean_price_rs_per_quintal": crop_df[
                    "national_mean_price_rs_per_quintal"
                ].median(),
                "matched_states_in_model": f"{direct_states}/{total_states}",
                "direct_area_coverage_percent": 100.0 * direct_area / total_area
                if total_area > 0
                else float("nan"),
                "national_fill_area_percent": 100.0
                * float(crop_df.loc[crop_df["national_mean_fill_used"], "baseline_area_ha"].sum())
                / total_area
                if total_area > 0
                else float("nan"),
                "area_weighted_benchmark_price_rs_per_quintal": price_weighted,
            }
        )

    return pd.DataFrame(rows)


def write_latex_table(summary: pd.DataFrame) -> None:
    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"\textbf{Crop} & \textbf{MSP reference} & "
            r"\textbf{National mean price} & "
            r"\textbf{Matched states} & \textbf{Direct area} & "
            r"\textbf{National fill area} & \textbf{Area-weighted price} \\"
        ),
        (
            r" & \textbf{(Rs qtl$^{-1}$)} & \textbf{(Rs qtl$^{-1}$)} & "
            r"\textbf{(n/n)} & \textbf{(\%)} & \textbf{(\%)} & "
            r"\textbf{(Rs qtl$^{-1}$)} \\"
        ),
        r"\midrule",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            " & ".join(
                [
                    str(row.crop),
                    format_number(row.msp_reference_rs_per_quintal, None),
                    format_number(row.national_mean_price_rs_per_quintal, 0),
                    str(row.matched_states_in_model),
                    format_number(row.direct_area_coverage_percent, 1),
                    format_number(row.national_fill_area_percent, 3),
                    format_number(row.area_weighted_benchmark_price_rs_per_quintal, 0),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    OUT_TEX.write_text("\n".join(lines) + "\n")


def write_audit(summary: pd.DataFrame) -> None:
    preview = summary.to_csv(index=False).strip()
    lines = [
        "# Primary revenue price summary",
        "",
        f"Scenario year: `{SCENARIO_YEAR}`.",
        "",
        "This table summarizes the 2017-18 official price benchmark used in the revised main optimization.",
        "Matched state-crop combinations use direct state-year realized prices derived from official",
        "value-of-output divided by production. Remaining state-crop combinations use the corresponding",
        "national crop-level realized price for 2017-18. The MSP reference is retained here only as a",
        "comparison column against the benchmarked realized prices; it is not used as a residual fallback",
        "in the primary benchmarked optimization branch.",
        "",
        "Output files:",
        f"- `{OUT_CSV.relative_to(ROOT)}`",
        f"- `{OUT_TEX.relative_to(ROOT)}`",
        "",
        "Summary:",
        "",
        "```csv",
        preview,
        "```",
    ]
    OUT_AUDIT.write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    summary.to_csv(OUT_CSV, index=False)
    write_latex_table(summary)
    write_audit(summary)
    print(f"csv: {OUT_CSV}")
    print(f"tex: {OUT_TEX}")
    print(f"audit: {OUT_AUDIT}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
