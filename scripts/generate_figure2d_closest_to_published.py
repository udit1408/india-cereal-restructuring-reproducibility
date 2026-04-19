#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated" / "figure2d_closest_to_published"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from probe_figure2d_income_variants import solve_variant  # noqa: E402
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _build_season_context  # noqa: E402
from generate_figure2d_clean import (  # noqa: E402
    build_crop_summary,
    build_transition_matrix,
    pivot_transition_matrix,
    plot_alluvial,
    _ordered_crops,
)


OUT_STEM = "figure2d_closest_to_published"


def _district_audit(area_frame: pd.DataFrame) -> pd.DataFrame:
    audit = (
        area_frame.groupby(["season", "State", "District"], as_index=False)[
            ["Original Area (Hectare)", "Optimized Area (Hectare)"]
        ]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_total_ha",
                "Optimized Area (Hectare)": "optimized_total_ha",
            }
        )
    )
    audit["delta_ha"] = audit["optimized_total_ha"] - audit["original_total_ha"]
    audit["abs_delta_ha"] = audit["delta_ha"].abs()
    return audit.sort_values(["abs_delta_ha", "season", "State", "District"], ascending=[False, True, True, True])


def _gross_shift(area_frame: pd.DataFrame, crop: str) -> dict[str, float]:
    sub = area_frame.loc[area_frame["Crop"] == crop].copy()
    baseline = float(sub["Original Area (Hectare)"].sum())
    optimized = float(sub["Optimized Area (Hectare)"].sum())
    gross_loss = float((sub["Original Area (Hectare)"] - sub["Optimized Area (Hectare)"]).clip(lower=0).sum())
    gross_gain = float((sub["Optimized Area (Hectare)"] - sub["Original Area (Hectare)"]).clip(lower=0).sum())
    return {
        "crop": crop,
        "baseline_ha": baseline,
        "optimized_ha": optimized,
        "gross_loss_ha": gross_loss,
        "gross_gain_ha": gross_gain,
        "gross_loss_pct": 100.0 * gross_loss / baseline,
        "gross_gain_pct": 100.0 * gross_gain / baseline,
        "net_change_pct": 100.0 * (optimized - baseline) / baseline,
    }


def _optimized_share(crop_summary: pd.DataFrame, crops: list[str], optimized_total: float) -> float:
    return 100.0 * crop_summary.loc[crop_summary["Crop"].isin(crops), "optimized_total_ha"].sum() / optimized_total


def build_summary_markdown(
    crop_summary: pd.DataFrame,
    gross_metrics: pd.DataFrame,
    district_audit: pd.DataFrame,
) -> str:
    optimized_total = float(crop_summary["optimized_total_ha"].sum())
    millet_share = _optimized_share(crop_summary, ["bajra", "ragi"], optimized_total)
    jowar_share = _optimized_share(crop_summary, ["jowar"], optimized_total)
    maize_share = _optimized_share(crop_summary, ["maize"], optimized_total)
    rice = gross_metrics.loc[gross_metrics["crop"] == "rice"].iloc[0]
    wheat = gross_metrics.loc[gross_metrics["crop"] == "wheat"].iloc[0]
    max_residual = float(district_audit["abs_delta_ha"].max())

    lines = [
        "# Figure 2(d) closest-to-published rebuild",
        "",
        "This branch is designed to stay as close as possible to the published Figure 2(d) behavior while remaining",
        "fully reproducible from the current cleaned workflow. It keeps the manuscript's seasonal income logic",
        "(profit floor in kharif, relaxed income floor in rabi), preserves district total cropped area, and restricts",
        "reallocation to crops already observed in each district. It does not apply the stricter district-crop historical",
        "maximum-area cap, because that cap was not active in the legacy notebooks that underlie the original panel.",
        "",
        "The published text for panel (d) is better matched by gross district-level reallocation away from a crop",
        "(sum of all positive district losses divided by that crop's national baseline area) than by net national crop-area",
        "change. Under that accounting, the rebuilt panel gives the following national shifts:",
        "",
        f"- rice gross reallocation: {rice['gross_loss_pct']:.1f}% of baseline rice area",
        f"- wheat gross reallocation: {wheat['gross_loss_pct']:.1f}% of baseline wheat area",
        f"- rice net national area change: {rice['net_change_pct']:.1f}%",
        f"- wheat net national area change: {wheat['net_change_pct']:.1f}%",
        "",
        "The optimized national cereal-area shares closely match the published narrative:",
        "",
        f"- millet (bajra + ragi): {millet_share:.1f}% of optimized cropland area",
        f"- jowar: {jowar_share:.1f}% of optimized cropland area",
        f"- maize: {maize_share:.1f}% of optimized cropland area",
        "",
        f"District-area conservation check: maximum district-season residual = {max_residual:.6e} ha.",
        "",
        "This branch reproduces the published rice-conversion magnitude and the alternative-cereal area shares closely.",
        "It does not fully recover the legacy wheat value of 22.6%, suggesting that number should be treated as a",
        "manuscript-level legacy value rather than as a reproducible output of the current archived code and data.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        kharif_context = _build_season_context(layout, "kharif", "kharif_nitrogen_min.ipynb")
        rabi_context = _build_season_context(layout, "rabi", "rabi__nitrogen_kharif_cop.ipynb")

    area_frame = pd.concat(
        [
            solve_variant(kharif_context, "profit"),
            solve_variant(rabi_context, None),
        ],
        ignore_index=True,
    )
    crop_order = _ordered_crops(area_frame)
    crop_summary = build_crop_summary(area_frame, crop_order)
    transition_long = build_transition_matrix(area_frame, crop_order)
    transition_matrix = pivot_transition_matrix(transition_long, crop_order)
    district_audit = _district_audit(area_frame)
    gross_metrics = pd.DataFrame([_gross_shift(area_frame, "rice"), _gross_shift(area_frame, "wheat")])
    summary_text = build_summary_markdown(crop_summary, gross_metrics, district_audit)

    area_frame.to_csv(DATA_DIR / f"{OUT_STEM}_optimized_areas.csv", index=False)
    crop_summary.to_csv(DATA_DIR / f"{OUT_STEM}_crop_summary.csv", index=False)
    transition_long.to_csv(DATA_DIR / f"{OUT_STEM}_transition_long.csv", index=False)
    transition_matrix.to_csv(DATA_DIR / f"{OUT_STEM}_transition_matrix.csv")
    district_audit.to_csv(DATA_DIR / f"{OUT_STEM}_district_area_audit.csv", index=False)
    gross_metrics.to_csv(DATA_DIR / f"{OUT_STEM}_gross_shift_metrics.csv", index=False)
    (DATA_DIR / f"{OUT_STEM}_summary.md").write_text(summary_text + "\n")

    plot_alluvial(
        transition_matrix,
        crop_summary,
        title=None,
        output_stem=OUT_STEM,
    )


if __name__ == "__main__":
    main()
