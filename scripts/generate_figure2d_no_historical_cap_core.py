#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated" / "figure2d_no_historical_cap_core"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _build_season_context  # noqa: E402
from generate_figure2d_clean import (  # noqa: E402
    _ordered_crops,
    build_crop_summary,
    build_transition_matrix,
    pivot_transition_matrix,
    plot_alluvial,
    solve_nitrogen_focused_areas,
)


OUT_STEM = "figure2d_no_historical_cap_core"


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
        "# Figure 2(d) approved core rebuild",
        "",
        "This panel is aligned to the same approved optimization branch used for Figure 2(a),",
        "Figure 2(b), and the displayed Figure 2(c) variant: unchanged district cropped area,",
        "substitution among historically observed cereals, and shared state calorie and",
        "MSP-benchmarked income constraints.",
        "",
        "To keep the panel text consistent with the visual transition diagram, the rice and wheat",
        "reallocation magnitudes reported below use gross district-level losses relative to each crop's",
        "national baseline area, alongside the corresponding net national area changes.",
        "",
        f"- rice gross reallocation: {rice['gross_loss_pct']:.1f}% of baseline rice area",
        f"- wheat gross reallocation: {wheat['gross_loss_pct']:.1f}% of baseline wheat area",
        f"- rice net national area change: {rice['net_change_pct']:.1f}%",
        f"- wheat net national area change: {wheat['net_change_pct']:.1f}%",
        "",
        "The optimized national cereal-area shares under this same branch are:",
        "",
        f"- millet (bajra + ragi): {millet_share:.1f}% of optimized cropland area",
        f"- jowar: {jowar_share:.1f}% of optimized cropland area",
        f"- maize: {maize_share:.1f}% of optimized cropland area",
        "",
        f"District-area conservation check: maximum district-season residual = {max_residual:.6e} ha.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        season_contexts = {
            season: _build_season_context(layout, season, notebook_name)
            for season, notebook_name in {
                "kharif": "kharif_nitrogen_min.ipynb",
                "rabi": "rabi__nitrogen_kharif_cop.ipynb",
            }.items()
        }

    solved_frames = []
    state_audits = []
    district_audits = []
    for season, context in season_contexts.items():
        area_frame, state_audit, district_audit = solve_nitrogen_focused_areas(
            context,
            solver_name="highs",
            income_mode="profit",
            use_historical_caps=False,
        )
        solved_frames.append(area_frame)
        state_audits.append(state_audit)
        district_audits.append(district_audit)

    combined_areas = pd.concat(solved_frames, ignore_index=True)
    combined_state_audit = pd.concat(state_audits, ignore_index=True)
    combined_district_audit = pd.concat(district_audits, ignore_index=True)
    crop_order = _ordered_crops(combined_areas)
    crop_summary = build_crop_summary(combined_areas, crop_order)
    transition_long = build_transition_matrix(combined_areas, crop_order)
    transition_matrix = pivot_transition_matrix(transition_long, crop_order)
    gross_metrics = pd.DataFrame([_gross_shift(combined_areas, "rice"), _gross_shift(combined_areas, "wheat")])
    district_audit = _district_audit(combined_areas)
    summary_text = build_summary_markdown(crop_summary, gross_metrics, district_audit)

    combined_areas.to_csv(DATA_DIR / f"{OUT_STEM}_optimized_areas.csv", index=False)
    combined_state_audit.to_csv(DATA_DIR / f"{OUT_STEM}_state_constraint_audit.csv", index=False)
    combined_district_audit.to_csv(DATA_DIR / f"{OUT_STEM}_district_area_audit.csv", index=False)
    crop_summary.to_csv(DATA_DIR / f"{OUT_STEM}_crop_summary.csv", index=False)
    transition_long.to_csv(DATA_DIR / f"{OUT_STEM}_transition_long.csv", index=False)
    transition_matrix.to_csv(DATA_DIR / f"{OUT_STEM}_transition_matrix.csv")
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
