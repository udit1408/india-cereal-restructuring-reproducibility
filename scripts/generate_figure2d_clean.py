#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MplPath


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated" / "figure2d"

sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    CALORIE_SCALE,
    INCOME_SCALE,
    _build_season_context,
    _relaxed_rhs,
    _sanitize,
    _solver,
)


CROP_ORDER = ["wheat", "rice", "bajra", "maize", "jowar", "ragi"]
CROP_COLORS = {
    "wheat": "#ff3b30",
    "rice": "#4f81bd",
    "bajra": "#ffd23f",
    "maize": "#57cc99",
    "jowar": "#8d99ae",
    "ragi": "#cfc8ff",
}
SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}
FLOAT_TOL = 1e-6


def _ordered_crops(frame: pd.DataFrame) -> list[str]:
    observed = frame["Crop"].astype(str).unique().tolist()
    ordered = [crop for crop in CROP_ORDER if crop in observed]
    ordered.extend(sorted(crop for crop in observed if crop not in ordered))
    return ordered


def _baseline_crop_area(frame: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    return frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()


def solve_nitrogen_focused_areas(
    context: dict[str, object],
    *,
    solver_name: str = "highs",
    income_mode: str = "profit",
    use_historical_caps: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pairs_with_area = context["pairs_with_area"]
    crops_by_pair = context["crops_by_pair"]
    current_area = context["current_area"]
    max_area_constraints = context["max_area_constraints"]
    nitrogen_rate = context["nitrogen_rate"]
    nitrogen_removal_rate = context["nitrogen_removal_rate"]
    yield_data = context["yield_data"]
    calories_per_prod = context["calories_per_prod"]
    cost_per_prod = context["cost_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    initial_state_calories = context["initial_state_calories"]
    initial_state_profit = context["initial_state_profit"]
    initial_state_msp = context["initial_state_msp"]
    districts_by_state = context["districts_by_state"]
    states = context["states"]
    frame = context["frame"]
    season = str(context["season"])

    original_area = _baseline_crop_area(frame)

    prob = pulp.LpProblem(f"Figure2D_{season}_nitrogen_focus", pulp.LpMinimize)
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}
    for state, district in pairs_with_area:
        for crop in crops_by_pair[(state, district)]:
            var_name = f"area__{_sanitize(state)}__{_sanitize(district)}__{_sanitize(crop)}"
            x[(state, district, crop)] = pulp.LpVariable(var_name, lowBound=0, cat=pulp.LpContinuous)

    objective_n = pulp.lpSum(
        x[(state, district, crop)]
        * (
            nitrogen_rate.get((state, district, crop), 0.0)
            - yield_data.get((state, district, crop), 0.0)
            * nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district, crop in x
    )
    prob += objective_n

    for state, district in pairs_with_area:
        prob += (
            pulp.lpSum(x[(state, district, crop)] for crop in crops_by_pair[(state, district)])
            == current_area.get((state, district), 0.0)
        )
        if use_historical_caps:
            for crop in crops_by_pair[(state, district)]:
                cap = max_area_constraints.get((state, district, crop))
                if cap is not None:
                    prob += x[(state, district, crop)] <= cap

    for state in states:
        valid_districts = districts_by_state.get(state, [])
        calorie_terms = [
            x[(state, district, crop)]
            * yield_data.get((state, district, crop), 0.0)
            * calories_per_prod.get((state, district, crop), 0.0)
            for district in valid_districts
            for crop in crops_by_pair.get((state, district), [])
            if (state, district, crop) in x
        ]
        calorie_target = _relaxed_rhs(float(initial_state_calories.get(state, 0.0)))
        prob += pulp.lpSum(calorie_terms) / CALORIE_SCALE >= calorie_target / CALORIE_SCALE

        if income_mode == "profit":
            income_terms = [
                x[(state, district, crop)]
                * yield_data.get((state, district, crop), 0.0)
                * 0.01
                * (
                    msp_per_prod.get((state, district, crop), 0.0)
                    - cost_per_prod.get((state, district, crop), 0.0)
                )
                for district in valid_districts
                for crop in crops_by_pair.get((state, district), [])
                if (state, district, crop) in x
            ]
            income_target = _relaxed_rhs(float(initial_state_profit.get(state, 0.0)))
        elif income_mode == "msp":
            income_terms = [
                x[(state, district, crop)]
                * yield_data.get((state, district, crop), 0.0)
                * 0.01
                * msp_per_prod.get((state, district, crop), 0.0)
                for district in valid_districts
                for crop in crops_by_pair.get((state, district), [])
                if (state, district, crop) in x
            ]
            income_target = _relaxed_rhs(float(initial_state_msp.get(state, 0.0)))
        else:
            raise ValueError(f"Unsupported income mode: {income_mode}")
        prob += pulp.lpSum(income_terms) / INCOME_SCALE >= income_target / INCOME_SCALE

    prob.solve(_solver(solver_name))
    status = pulp.LpStatus.get(prob.status, str(prob.status))
    if status != "Optimal":
        raise RuntimeError(f"{season}: solver returned {status} for the nitrogen-focused rebuild")

    rows = []
    for (state, district, crop), variable in sorted(x.items()):
        rows.append(
            {
                "season": season,
                "State": state,
                "District": district,
                "Crop": crop,
                "Original Area (Hectare)": float(original_area.get((state, district, crop), 0.0)),
                "Optimized Area (Hectare)": float(variable.value() or 0.0),
            }
        )
    area_frame = pd.DataFrame(rows)

    district_audit = (
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
    district_audit["delta_ha"] = district_audit["optimized_total_ha"] - district_audit["original_total_ha"]
    district_audit["abs_delta_ha"] = district_audit["delta_ha"].abs()

    state_rows = []
    for state in states:
        valid_districts = districts_by_state.get(state, [])
        optimized_calories = 0.0
        optimized_income = 0.0
        for district in valid_districts:
            for crop in crops_by_pair.get((state, district), []):
                key = (state, district, crop)
                area = float(area_frame.loc[
                    (area_frame["State"] == state)
                    & (area_frame["District"] == district)
                    & (area_frame["Crop"] == crop),
                    "Optimized Area (Hectare)",
                ].iloc[0])
                optimized_calories += (
                    area
                    * yield_data.get(key, 0.0)
                    * calories_per_prod.get(key, 0.0)
                )
                if income_mode == "profit":
                    optimized_income += (
                        area
                        * yield_data.get(key, 0.0)
                        * 0.01
                        * (msp_per_prod.get(key, 0.0) - cost_per_prod.get(key, 0.0))
                    )
                else:
                    optimized_income += (
                        area * yield_data.get(key, 0.0) * 0.01 * msp_per_prod.get(key, 0.0)
                    )
        baseline_calories = float(initial_state_calories.get(state, 0.0))
        relaxed_calories = _relaxed_rhs(baseline_calories)
        baseline_income = float(
            initial_state_profit.get(state, 0.0) if income_mode == "profit" else initial_state_msp.get(state, 0.0)
        )
        relaxed_income = _relaxed_rhs(baseline_income)
        state_rows.append(
            {
                "season": season,
                "State": state,
                "baseline_calories": baseline_calories,
                "relaxed_calorie_target": relaxed_calories,
                "optimized_calories": optimized_calories,
                "calorie_gap": optimized_calories - baseline_calories,
                "calorie_gap_vs_relaxed_target": optimized_calories - relaxed_calories,
                "baseline_income": baseline_income,
                "relaxed_income_target": relaxed_income,
                "optimized_income": optimized_income,
                "income_gap": optimized_income - baseline_income,
                "income_gap_vs_relaxed_target": optimized_income - relaxed_income,
            }
        )
    state_audit = pd.DataFrame(state_rows)
    return area_frame, state_audit, district_audit


def build_transition_matrix(area_frame: pd.DataFrame, crop_order: list[str]) -> pd.DataFrame:
    flows: list[dict[str, object]] = []
    grouped = area_frame.groupby(["season", "State", "District"], sort=True)

    for (season, state, district), group in grouped:
        original = {crop: 0.0 for crop in crop_order}
        optimized = {crop: 0.0 for crop in crop_order}
        for crop, original_area, optimized_area in group[
            ["Crop", "Original Area (Hectare)", "Optimized Area (Hectare)"]
        ].itertuples(index=False, name=None):
            original[str(crop)] = float(original_area)
            optimized[str(crop)] = float(optimized_area)

        retained = {crop: min(original[crop], optimized[crop]) for crop in crop_order}
        losses = {crop: max(original[crop] - optimized[crop], 0.0) for crop in crop_order}
        gains = {crop: max(optimized[crop] - original[crop], 0.0) for crop in crop_order}

        total_loss = sum(losses.values())
        total_gain = sum(gains.values())
        if total_loss <= FLOAT_TOL and total_gain <= FLOAT_TOL:
            for crop in crop_order:
                if retained[crop] > FLOAT_TOL:
                    flows.append(
                        {
                            "season": season,
                            "State": state,
                            "District": district,
                            "source_crop": crop,
                            "target_crop": crop,
                            "flow_ha": retained[crop],
                            "flow_type": "retained",
                        }
                    )
            continue

        if abs(total_loss - total_gain) > max(1e-5, 1e-8 * max(total_loss, total_gain, 1.0)):
            raise RuntimeError(
                f"District-season area flow mismatch in {season}/{state}/{district}: "
                f"loss={total_loss}, gain={total_gain}"
            )

        gain_scale = 1.0 if total_gain <= FLOAT_TOL else total_loss / total_gain
        scaled_gains = {crop: gains[crop] * gain_scale for crop in crop_order}

        for crop in crop_order:
            if retained[crop] > FLOAT_TOL:
                flows.append(
                    {
                        "season": season,
                        "State": state,
                        "District": district,
                        "source_crop": crop,
                        "target_crop": crop,
                        "flow_ha": retained[crop],
                        "flow_type": "retained",
                    }
                )

        for source_crop in crop_order:
            loss = losses[source_crop]
            if loss <= FLOAT_TOL:
                continue
            for target_crop in crop_order:
                gain = scaled_gains[target_crop]
                if gain <= FLOAT_TOL:
                    continue
                flow = loss * gain / total_loss
                if flow > FLOAT_TOL:
                    flows.append(
                        {
                            "season": season,
                            "State": state,
                            "District": district,
                            "source_crop": source_crop,
                            "target_crop": target_crop,
                            "flow_ha": flow,
                            "flow_type": "reallocated",
                        }
                    )

    transition_long = pd.DataFrame(flows)
    transition_long = (
        transition_long.groupby(
            ["source_crop", "target_crop", "flow_type"],
            as_index=False,
        )["flow_ha"]
        .sum()
        .sort_values(["source_crop", "target_crop", "flow_type"])
        .reset_index(drop=True)
    )
    return transition_long


def pivot_transition_matrix(transition_long: pd.DataFrame, crop_order: list[str]) -> pd.DataFrame:
    pivot = (
        transition_long.groupby(["source_crop", "target_crop"], as_index=False)["flow_ha"]
        .sum()
        .pivot(index="source_crop", columns="target_crop", values="flow_ha")
        .reindex(index=crop_order, columns=crop_order, fill_value=0.0)
    )
    return pivot


def build_crop_summary(area_frame: pd.DataFrame, crop_order: list[str]) -> pd.DataFrame:
    summary = (
        area_frame.groupby("Crop", as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_total_ha",
                "Optimized Area (Hectare)": "optimized_total_ha",
            }
        )
    )
    summary["delta_ha"] = summary["optimized_total_ha"] - summary["original_total_ha"]
    summary["pct_change"] = np.where(
        summary["original_total_ha"] > 0,
        100.0 * summary["delta_ha"] / summary["original_total_ha"],
        math.nan,
    )
    summary["Crop"] = pd.Categorical(summary["Crop"], categories=crop_order, ordered=True)
    summary = summary.sort_values("Crop").reset_index(drop=True)
    summary["Crop"] = summary["Crop"].astype(str)
    return summary


def _crop_positions(totals: dict[str, float], crop_order: list[str], gap: float = 0.018) -> tuple[dict[str, tuple[float, float]], float]:
    total = sum(totals.get(crop, 0.0) for crop in crop_order)
    if total <= 0:
        raise ValueError("Cannot place crops for an empty transition matrix")
    usable_height = 1.0 - gap * (len(crop_order) - 1)
    scale = usable_height / total
    positions: dict[str, tuple[float, float]] = {}
    cursor_top = 1.0
    for crop in crop_order:
        height = totals.get(crop, 0.0) * scale
        bottom = cursor_top - height
        positions[crop] = (bottom, height)
        cursor_top = bottom - gap
    return positions, scale


def _ribbon_patch(
    x0: float,
    x1: float,
    y0_low: float,
    y0_high: float,
    y1_low: float,
    y1_high: float,
    *,
    facecolor: str,
    alpha: float = 0.62,
) -> PathPatch:
    xs = np.linspace(x0, x1, 80)
    t = np.linspace(0.0, 1.0, 80)
    smooth = 3 * t**2 - 2 * t**3
    lower = y0_low + (y1_low - y0_low) * smooth
    upper = y0_high + (y1_high - y0_high) * smooth
    vertices = np.column_stack(
        [
            np.concatenate([xs, xs[::-1], [xs[0]]]),
            np.concatenate([lower, upper[::-1], [lower[0]]]),
        ]
    )
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(xs) - 1) + [MplPath.LINETO] * len(xs) + [MplPath.CLOSEPOLY]
    return PathPatch(
        MplPath(vertices, codes),
        facecolor=facecolor,
        edgecolor="none",
        alpha=alpha,
        zorder=2,
    )


def plot_alluvial(
    transition_matrix: pd.DataFrame,
    crop_summary: pd.DataFrame,
    *,
    title: str | None,
    output_stem: str,
) -> tuple[Path, Path]:
    crop_order = [crop for crop in CROP_ORDER if crop in transition_matrix.index]
    left_totals = crop_summary.set_index("Crop")["original_total_ha"].to_dict()
    right_totals = crop_summary.set_index("Crop")["optimized_total_ha"].to_dict()
    left_positions, scale_left = _crop_positions(left_totals, crop_order)
    right_positions, scale_right = _crop_positions(right_totals, crop_order)

    if abs(scale_left - scale_right) > 1e-12:
        raise RuntimeError("Left and right scales differ in the alluvial renderer")
    scale = scale_left

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    left_x = 0.07
    right_x = 0.87
    bar_width = 0.055
    ribbon_start = left_x + bar_width
    ribbon_end = right_x

    source_offsets = {crop: 0.0 for crop in crop_order}
    target_offsets = {crop: 0.0 for crop in crop_order}

    for source_crop in crop_order:
        source_bottom, source_height = left_positions[source_crop]
        source_top = source_bottom + source_height
        for target_crop in crop_order:
            value = float(transition_matrix.loc[source_crop, target_crop])
            if value <= FLOAT_TOL:
                continue
            target_bottom, target_height = right_positions[target_crop]
            target_top = target_bottom + target_height
            flow_height = value * scale

            source_upper = source_top - source_offsets[source_crop]
            source_lower = source_upper - flow_height
            target_upper = target_top - target_offsets[target_crop]
            target_lower = target_upper - flow_height

            patch = _ribbon_patch(
                ribbon_start,
                ribbon_end,
                source_lower,
                source_upper,
                target_lower,
                target_upper,
                facecolor=CROP_COLORS.get(source_crop, "#999999"),
            )
            ax.add_patch(patch)
            source_offsets[source_crop] += flow_height
            target_offsets[target_crop] += flow_height

    for crop in crop_order:
        bottom, height = left_positions[crop]
        ax.add_patch(
            Rectangle(
                (left_x, bottom),
                bar_width,
                height,
                facecolor=CROP_COLORS.get(crop, "#999999"),
                edgecolor="white",
                linewidth=1.2,
                zorder=3,
            )
        )
        ax.text(
            left_x - 0.01,
            bottom + height / 2,
            crop,
            ha="right",
            va="center",
            fontsize=8.0,
            fontweight="bold",
        )

    for crop in crop_order:
        bottom, height = right_positions[crop]
        ax.add_patch(
            Rectangle(
                (right_x, bottom),
                bar_width,
                height,
                facecolor=CROP_COLORS.get(crop, "#999999"),
                edgecolor="white",
                linewidth=1.2,
                zorder=3,
            )
        )
        ax.text(
            right_x + bar_width + 0.01,
            bottom + height / 2,
            crop,
            ha="left",
            va="center",
            fontsize=8.0,
            fontweight="bold",
        )

    ax.text(left_x + bar_width / 2, -0.045, "Original", ha="center", va="top", fontsize=9.5, fontweight="bold")
    ax.text(right_x + bar_width / 2, -0.045, "Optimized", ha="center", va="top", fontsize=9.5, fontweight="bold")
    ax.text(-0.01, 1.01, "d", transform=ax.transAxes, fontsize=12, fontweight="bold")

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.06, 1.02)
    if title:
        ax.set_title(title, fontsize=11, pad=6)
    ax.axis("off")

    png_path = FIG_DIR / f"{output_stem}.png"
    pdf_path = FIG_DIR / f"{output_stem}.pdf"
    fig.tight_layout()
    fig.savefig(png_path, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path, pdf_path


def build_summary_markdown(
    area_frame: pd.DataFrame,
    crop_summary: pd.DataFrame,
    transition_long: pd.DataFrame,
    state_audit: pd.DataFrame,
    district_audit: pd.DataFrame,
) -> str:
    diagonal = (
        transition_long.loc[transition_long["source_crop"] == transition_long["target_crop"], "flow_ha"].sum()
    )
    total_area = crop_summary["original_total_ha"].sum()
    reallocated = total_area - diagonal

    rice_original = float(crop_summary.loc[crop_summary["Crop"] == "rice", "original_total_ha"].iloc[0])
    rice_optimized = float(crop_summary.loc[crop_summary["Crop"] == "rice", "optimized_total_ha"].iloc[0])
    wheat_original = float(crop_summary.loc[crop_summary["Crop"] == "wheat", "original_total_ha"].iloc[0])
    wheat_optimized = float(crop_summary.loc[crop_summary["Crop"] == "wheat", "optimized_total_ha"].iloc[0])

    off_diagonal = transition_long.loc[transition_long["source_crop"] != transition_long["target_crop"]].copy()
    top_flows = off_diagonal.sort_values("flow_ha", ascending=False).head(10)
    max_district_residual = float(district_audit["abs_delta_ha"].max())
    worst_calorie_gap = float(state_audit["calorie_gap_vs_relaxed_target"].min())
    worst_income_gap = float(state_audit["income_gap_vs_relaxed_target"].min())

    lines = [
        "# Figure 2(d) clean rebuild",
        "",
        "This rebuild uses the same clean nitrogen-focused optimization formulation adopted for the updated",
        "Figure 2(a) reconstruction: unchanged district cropped area, state-level calorie and profit constraints,",
        "district-crop historical maximum area caps, and crop availability restricted to crops observed in the",
        "historical record for each district.",
        "",
        "The transition panel is not read directly from an optimization variable because the model optimizes",
        "pre- and post-optimization crop areas rather than crop-to-crop movement. The alluvial panel therefore",
        "uses a deterministic allocation rule within each district-season:",
        "1. retain `min(original, optimized)` area on the diagonal for each crop;",
        "2. compute residual crop losses and gains;",
        "3. distribute each losing crop's residual area across gaining crops in proportion to those gains.",
        "",
        "Constraint audit:",
        f"- max district-season area residual: {max_district_residual:.6e} ha",
        f"- worst state calorie gap vs. relaxed model target: {worst_calorie_gap:.6e} kcal (solver tolerance only)",
        f"- worst state profit gap vs. relaxed model target: {worst_income_gap:.6e} Rs (solver tolerance only)",
        "",
        "National area changes:",
        (
            f"- rice: {rice_original / 1e6:.3f} Mha -> {rice_optimized / 1e6:.3f} Mha "
            f"({100.0 * (rice_optimized - rice_original) / rice_original:.3f}%)"
        ),
        (
            f"- wheat: {wheat_original / 1e6:.3f} Mha -> {wheat_optimized / 1e6:.3f} Mha "
            f"({100.0 * (wheat_optimized - wheat_original) / wheat_original:.3f}%)"
        ),
        (
            f"- total area reallocated off the diagonal: {reallocated / 1e6:.3f} Mha "
            f"({100.0 * reallocated / total_area:.3f}% of baseline cereal area)"
        ),
        "",
        "Largest off-diagonal flows under the proportional within-district allocation rule:",
    ]
    for row in top_flows.itertuples(index=False):
        lines.append(
            f"- {row.source_crop} -> {row.target_crop}: {float(row.flow_ha) / 1e6:.3f} Mha"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    with contextlib.redirect_stdout(io.StringIO()):
        season_contexts = {
            season: _build_season_context(layout, season, notebook_name)
            for season, notebook_name in SEASON_NOTEBOOKS.items()
        }

    solved_frames = []
    state_audits = []
    district_audits = []
    for season, context in season_contexts.items():
        area_frame, state_audit, district_audit = solve_nitrogen_focused_areas(
            context,
            solver_name="highs",
            income_mode="profit",
            use_historical_caps=True,
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
    summary_text = build_summary_markdown(
        combined_areas,
        crop_summary,
        transition_long,
        combined_state_audit,
        combined_district_audit,
    )

    combined_areas.to_csv(DATA_DIR / "figure2d_method_consistent_optimized_areas.csv", index=False)
    combined_state_audit.to_csv(DATA_DIR / "figure2d_method_consistent_state_constraint_audit.csv", index=False)
    combined_district_audit.to_csv(DATA_DIR / "figure2d_method_consistent_district_area_audit.csv", index=False)
    crop_summary.to_csv(DATA_DIR / "figure2d_method_consistent_crop_summary.csv", index=False)
    transition_long.to_csv(DATA_DIR / "figure2d_method_consistent_transition_long.csv", index=False)
    transition_matrix.to_csv(DATA_DIR / "figure2d_method_consistent_transition_matrix.csv")
    (DATA_DIR / "figure2d_method_consistent_summary.md").write_text(summary_text + "\n")

    plot_alluvial(
        transition_matrix,
        crop_summary,
        title=None,
        output_stem="figure2d_method_consistent_clean_rebuild",
    )


if __name__ == "__main__":
    main()
