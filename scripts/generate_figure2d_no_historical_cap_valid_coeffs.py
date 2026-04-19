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
DATA_DIR = ROOT / "data" / "generated" / "figure2d_no_historical_cap_valid_coeffs"

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
from generate_figure2d_no_historical_cap_core import (  # noqa: E402
    _district_audit,
    _gross_shift,
    build_summary_markdown,
)


OUT_STEM = "figure2d_no_historical_cap_valid_coeffs"
SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}


def filter_context_to_valid_coefficients(context: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame]:
    filtered = dict(context)
    crops_by_pair: dict[tuple[str, str], list[str]] = {}
    kept_pairs: list[tuple[str, str]] = []
    audit_rows: list[dict[str, object]] = []

    for pair in context["pairs_with_area"]:
        valid_crops: list[str] = []
        for crop in context["crops_by_pair"][pair]:
            key = (pair[0], pair[1], crop)
            has_valid_coeffs = (
                context["yield_data"].get(key, 0.0) > 0
                and context["calories_per_prod"].get(key, 0.0) > 0
                and key in context["nitrogen_rate"]
                and key in context["nitrogen_removal_rate"]
                and key in context["water_rate"]
                and key in context["msp_per_prod"]
                and key in context["cost_per_prod"]
            )
            audit_rows.append(
                {
                    "season": context["season"],
                    "State": pair[0],
                    "District": pair[1],
                    "Crop": crop,
                    "kept": has_valid_coeffs,
                    "yield_kg_ha": float(context["yield_data"].get(key, 0.0)),
                    "kcal_per_kg": float(context["calories_per_prod"].get(key, 0.0)),
                    "nitrogen_rate": float(context["nitrogen_rate"].get(key, 0.0)),
                    "nitrogen_removal_rate": float(context["nitrogen_removal_rate"].get(key, 0.0)),
                    "water_rate": float(context["water_rate"].get(key, 0.0)),
                    "msp_per_prod": float(context["msp_per_prod"].get(key, 0.0)),
                    "cost_per_prod": float(context["cost_per_prod"].get(key, 0.0)),
                }
            )
            if has_valid_coeffs:
                valid_crops.append(crop)
        if valid_crops:
            crops_by_pair[pair] = valid_crops
            kept_pairs.append(pair)

    filtered["crops_by_pair"] = crops_by_pair
    filtered["pairs_with_area"] = kept_pairs
    return filtered, pd.DataFrame(audit_rows)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    season_contexts: dict[str, dict[str, object]] = {}
    coefficient_audits: list[pd.DataFrame] = []
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for season, notebook_name in SEASON_NOTEBOOKS.items():
            raw_context = _build_season_context(layout, season, notebook_name)
            season_contexts[season], audit = filter_context_to_valid_coefficients(raw_context)
            coefficient_audits.append(audit)

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
    coefficient_audit = pd.concat(coefficient_audits, ignore_index=True)
    crop_order = _ordered_crops(combined_areas)
    crop_summary = build_crop_summary(combined_areas, crop_order)
    transition_long = build_transition_matrix(combined_areas, crop_order)
    transition_matrix = pivot_transition_matrix(transition_long, crop_order)
    gross_metrics = pd.DataFrame([_gross_shift(combined_areas, "rice"), _gross_shift(combined_areas, "wheat")])
    district_audit = _district_audit(combined_areas)
    summary_text = build_summary_markdown(crop_summary, gross_metrics, district_audit)
    removed_count = int((~coefficient_audit["kept"]).sum())
    kept_count = int(coefficient_audit["kept"].sum())
    extra_note = "\n".join(
        [
            "",
            "This corrected variant keeps the same no-historical-cap nitrogen-focused optimization",
            "structure as the core rebuild, but filters each district-season crop choice set to entries",
            "with a valid coefficient bundle before solving.",
            "",
            f"- kept crop-choice entries: {kept_count}",
            f"- removed crop-choice entries with incomplete or zero core coefficients: {removed_count}",
            "",
            "This is intended to prevent allocation into district-crop combinations with zero yield/calorie",
            "or otherwise missing core coefficients.",
            "",
        ]
    )

    combined_areas.to_csv(DATA_DIR / f"{OUT_STEM}_optimized_areas.csv", index=False)
    combined_state_audit.to_csv(DATA_DIR / f"{OUT_STEM}_state_constraint_audit.csv", index=False)
    combined_district_audit.to_csv(DATA_DIR / f"{OUT_STEM}_district_area_audit.csv", index=False)
    coefficient_audit.to_csv(DATA_DIR / f"{OUT_STEM}_coefficient_audit.csv", index=False)
    crop_summary.to_csv(DATA_DIR / f"{OUT_STEM}_crop_summary.csv", index=False)
    transition_long.to_csv(DATA_DIR / f"{OUT_STEM}_transition_long.csv", index=False)
    transition_matrix.to_csv(DATA_DIR / f"{OUT_STEM}_transition_matrix.csv")
    gross_metrics.to_csv(DATA_DIR / f"{OUT_STEM}_gross_shift_metrics.csv", index=False)
    (DATA_DIR / f"{OUT_STEM}_summary.md").write_text(summary_text + extra_note + "\n")

    plot_alluvial(
        transition_matrix,
        crop_summary,
        title=None,
        output_stem=OUT_STEM,
    )


if __name__ == "__main__":
    main()
