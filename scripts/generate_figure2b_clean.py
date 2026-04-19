#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"

sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    CALORIE_SCALE,
    INCOME_SCALE,
    _fill_missing_from_hierarchical_means,
    _has_valid_core_coefficients,
    _prepare_namespace,
    _relaxed_rhs,
    _sanitize,
    _solver,
    _state_crop_and_crop_means,
)


SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}

METRICS = [
    ("Nitrogen Emission", "N_emission"),
    ("Nitrogen Leach", "N_leach"),
    ("Greenhouse Gas emission", "AGHG"),
    ("Profit", "profit"),
    ("Calorie", "Calorie"),
    ("Phosphorus application", "P_applied"),
    ("Nitrogen application", "N_applied"),
    ("Phosphorus Surplus", "P_surplus"),
    ("Nitrogen Surplus", "N_surplus"),
    ("Water Demand", "water"),
]

DEFAULT_OUTPUT_STEM = "figure2b_clean_method_consistent"


def output_paths(stem: str) -> dict[str, Path]:
    return {
        "values_csv": DATA_DIR / f"{stem}_values.csv",
        "values_tex": DATA_DIR / f"{stem}_values.tex",
        "audit_md": DATA_DIR / f"{stem}_audit.md",
        "png": FIG_DIR / f"{stem}.png",
        "pdf": FIG_DIR / f"{stem}.pdf",
    }


def signed_display_change(metric: str, pct_reduction: float, original_total: float) -> float:
    del metric
    pct = float(pct_reduction)
    if float(original_total) < 0:
        return pct
    return -pct


def float_triplet_map(mapping: object) -> dict[tuple[str, str, str], float]:
    if isinstance(mapping, pd.Series):
        mapping = mapping.to_dict()
    if not isinstance(mapping, dict):
        raise TypeError(f"Expected dict-like mapping, found {type(mapping)!r}")
    out: dict[tuple[str, str, str], float] = {}
    for key, value in mapping.items():
        if not isinstance(key, tuple) or len(key) != 3:
            continue
        try:
            out[(str(key[0]), str(key[1]), str(key[2]))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def build_context(layout, season: str, notebook_name: str) -> dict[str, object]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        namespace = _prepare_namespace(layout, notebook_name)

    frame = namespace["df"].copy()
    frame["State"] = frame["State"].astype(str)
    frame["District"] = frame["District"].astype(str)
    frame["Crop"] = frame["Crop"].astype(str)

    state_district_pairs = list(
        frame[["State", "District"]]
        .drop_duplicates()
        .sort_values(["State", "District"])
        .itertuples(index=False, name=None)
    )
    states = sorted(frame["State"].dropna().astype(str).unique().tolist())
    crops = sorted(frame["Crop"].dropna().astype(str).unique().tolist())

    history = namespace[season].copy()
    history = history.rename(columns={"state": "State", "district": "District", "crop": "Crop"})
    history["State"] = history["State"].astype(str)
    history["District"] = history["District"].astype(str)
    history["Crop"] = history["Crop"].astype(str)
    history = history[history["Crop"].isin(crops)].copy()

    current_area = frame.groupby(["State", "District"])["Area (Hectare)"].sum().astype(float).to_dict()
    current_cereal_area = (
        frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()
    )
    historical_cereal_area = (
        history.groupby(["State", "District", "Crop"])["Area (Hectare)"].max().astype(float).to_dict()
    )
    max_area_constraints = dict(historical_cereal_area)
    cap_repairs = 0
    for key, area in current_cereal_area.items():
        if area <= 0:
            continue
        existing = max_area_constraints.get(key)
        if existing is None or existing < area:
            max_area_constraints[key] = area
            cap_repairs += 1

    nitrogen_rate = float_triplet_map(namespace["nitrogen_rate"])
    p_rate = float_triplet_map(namespace["P_rate"])
    water_rate = float_triplet_map(namespace["water_rate"])
    yield_data = float_triplet_map(namespace["yield_data"])
    n_removed_rate = float_triplet_map(namespace["nitrogen_removal_rate_perkg"])
    p_removed_rate = float_triplet_map(namespace["P_removal_rate_perkg"])
    calories_per_prod = float_triplet_map(namespace["calories_per_prod"])
    msp_per_prod = float_triplet_map(namespace["MSP_per_prod"])
    cost_per_prod = float_triplet_map(namespace["cost_per_area"])
    aghg_per_ha = float_triplet_map(namespace["AGHG_per_ha"])
    n_leach_rate = float_triplet_map(namespace["nitrogen_leach_rate_perkg"])
    n_emission_rate = float_triplet_map(namespace["nitrogen_emission_rate_perkg"])

    yield_state_crop_means, yield_crop_means = _state_crop_and_crop_means(yield_data)
    calorie_state_crop_means, calorie_crop_means = _state_crop_and_crop_means(calories_per_prod)
    nitrogen_state_crop_means, nitrogen_crop_means = _state_crop_and_crop_means(nitrogen_rate)
    n_removed_state_crop_means, n_removed_crop_means = _state_crop_and_crop_means(n_removed_rate)
    p_state_crop_means, p_crop_means = _state_crop_and_crop_means(p_rate)
    p_removed_state_crop_means, p_removed_crop_means = _state_crop_and_crop_means(p_removed_rate)
    water_state_crop_means, water_crop_means = _state_crop_and_crop_means(water_rate)
    msp_state_crop_means, msp_crop_means = _state_crop_and_crop_means(msp_per_prod)
    cost_state_crop_means, cost_crop_means = _state_crop_and_crop_means(cost_per_prod)
    aghg_state_crop_means, aghg_crop_means = _state_crop_and_crop_means(aghg_per_ha)
    n_leach_state_crop_means, n_leach_crop_means = _state_crop_and_crop_means(n_leach_rate)
    n_emission_state_crop_means, n_emission_crop_means = _state_crop_and_crop_means(n_emission_rate)

    districts_by_state = {
        state: sorted(group["District"].dropna().astype(str).unique().tolist())
        for state, group in frame.groupby("State", sort=True)
    }
    crops_by_pair: dict[tuple[str, str], list[str]] = {}
    coefficient_imputed = 0
    coefficient_screen_kept = 0
    coefficient_screen_removed = 0
    for state, district in state_district_pairs:
        valid_crops: list[str] = []
        for crop in crops:
            key = (state, district, crop)
            if historical_cereal_area.get(key, 0.0) <= 0:
                continue
            if current_area.get((state, district), 0.0) > 0 and not _has_valid_core_coefficients(
                key,
                yield_data=yield_data,
                calories_per_prod=calories_per_prod,
                nitrogen_rate=nitrogen_rate,
                nitrogen_removal_rate=n_removed_rate,
                water_rate=water_rate,
                msp_per_prod=msp_per_prod,
                cost_per_prod=cost_per_prod,
            ):
                imputed_any = False
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=yield_data,
                    state_crop_means=yield_state_crop_means,
                    crop_means=yield_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=calories_per_prod,
                    state_crop_means=calorie_state_crop_means,
                    crop_means=calorie_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=nitrogen_rate,
                    state_crop_means=nitrogen_state_crop_means,
                    crop_means=nitrogen_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=n_removed_rate,
                    state_crop_means=n_removed_state_crop_means,
                    crop_means=n_removed_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=p_rate,
                    state_crop_means=p_state_crop_means,
                    crop_means=p_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=p_removed_rate,
                    state_crop_means=p_removed_state_crop_means,
                    crop_means=p_removed_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=water_rate,
                    state_crop_means=water_state_crop_means,
                    crop_means=water_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=msp_per_prod,
                    state_crop_means=msp_state_crop_means,
                    crop_means=msp_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=cost_per_prod,
                    state_crop_means=cost_state_crop_means,
                    crop_means=cost_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=aghg_per_ha,
                    state_crop_means=aghg_state_crop_means,
                    crop_means=aghg_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=n_leach_rate,
                    state_crop_means=n_leach_state_crop_means,
                    crop_means=n_leach_crop_means,
                )
                imputed_any |= _fill_missing_from_hierarchical_means(
                    key=key,
                    mapping=n_emission_rate,
                    state_crop_means=n_emission_state_crop_means,
                    crop_means=n_emission_crop_means,
                )
                if imputed_any and _has_valid_core_coefficients(
                    key,
                    yield_data=yield_data,
                    calories_per_prod=calories_per_prod,
                    nitrogen_rate=nitrogen_rate,
                    nitrogen_removal_rate=n_removed_rate,
                    water_rate=water_rate,
                    msp_per_prod=msp_per_prod,
                    cost_per_prod=cost_per_prod,
                ):
                    coefficient_imputed += 1
            if _has_valid_core_coefficients(
                key,
                yield_data=yield_data,
                calories_per_prod=calories_per_prod,
                nitrogen_rate=nitrogen_rate,
                nitrogen_removal_rate=n_removed_rate,
                water_rate=water_rate,
                msp_per_prod=msp_per_prod,
                cost_per_prod=cost_per_prod,
            ):
                valid_crops.append(crop)
                coefficient_screen_kept += 1
            else:
                coefficient_screen_removed += 1
        crops_by_pair[(state, district)] = valid_crops
    pairs_with_area = [
        pair
        for pair in state_district_pairs
        if current_area.get(pair, 0.0) > 0 and crops_by_pair.get(pair)
    ]

    initial_state_calories = {
        state: sum(
            current_cereal_area.get((state, district, crop), 0.0)
            * yield_data.get((state, district, crop), 0.0)
            * calories_per_prod.get((state, district, crop), 0.0)
            for district in districts_by_state.get(state, [])
            for crop in crops_by_pair.get((state, district), [])
        )
        for state in states
    }
    initial_state_profit = {
        state: sum(
            current_cereal_area.get((state, district, crop), 0.0)
            * yield_data.get((state, district, crop), 0.0)
            * 0.01
            * (
                msp_per_prod.get((state, district, crop), 0.0)
                - cost_per_prod.get((state, district, crop), 0.0)
            )
            for district in districts_by_state.get(state, [])
            for crop in crops_by_pair.get((state, district), [])
        )
        for state in states
    }

    return {
        "season": season,
        "states": states,
        "pairs_with_area": pairs_with_area,
        "districts_by_state": districts_by_state,
        "crops_by_pair": crops_by_pair,
        "current_area": current_area,
        "current_cereal_area": current_cereal_area,
        "max_area_constraints": max_area_constraints,
        "yield_data": yield_data,
        "nitrogen_rate": nitrogen_rate,
        "p_rate": p_rate,
        "water_rate": water_rate,
        "n_removed_rate": n_removed_rate,
        "p_removed_rate": p_removed_rate,
        "calories_per_prod": calories_per_prod,
        "msp_per_prod": msp_per_prod,
        "cost_per_prod": cost_per_prod,
        "aghg_per_ha": aghg_per_ha,
        "n_leach_rate": n_leach_rate,
        "n_emission_rate": n_emission_rate,
        "initial_state_calories": initial_state_calories,
        "initial_state_profit": initial_state_profit,
        "cap_repairs": cap_repairs,
        "coefficient_imputed": coefficient_imputed,
        "coefficient_screen_kept": coefficient_screen_kept,
        "coefficient_screen_removed": coefficient_screen_removed,
    }


def solve_endpoint(
    context: dict[str, object],
    objective: str,
    *,
    use_historical_caps: bool = True,
) -> tuple[str, dict[tuple[str, str, str], float]]:
    pairs_with_area = context["pairs_with_area"]
    crops_by_pair = context["crops_by_pair"]
    current_area = context["current_area"]
    max_area_constraints = context["max_area_constraints"]
    nitrogen_rate = context["nitrogen_rate"]
    water_rate = context["water_rate"]
    yield_data = context["yield_data"]
    n_removed_rate = context["n_removed_rate"]
    calories_per_prod = context["calories_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    cost_per_prod = context["cost_per_prod"]
    initial_state_calories = context["initial_state_calories"]
    initial_state_profit = context["initial_state_profit"]
    districts_by_state = context["districts_by_state"]
    states = context["states"]

    prob = pulp.LpProblem(f"Figure2B_{context['season']}_{objective}", pulp.LpMinimize)
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}
    for state, district in pairs_with_area:
        for crop in crops_by_pair[(state, district)]:
            name = f"area__{_sanitize(state)}__{_sanitize(district)}__{_sanitize(crop)}"
            x[(state, district, crop)] = pulp.LpVariable(name, lowBound=0, cat=pulp.LpContinuous)

    if objective == "nitrogen":
        prob += pulp.lpSum(
            x[(state, district, crop)]
            * (
                nitrogen_rate.get((state, district, crop), 0.0)
                - yield_data.get((state, district, crop), 0.0)
                * n_removed_rate.get((state, district, crop), 0.0)
            )
            for state, district, crop in x
        )
    elif objective == "water":
        prob += pulp.lpSum(
            x[(state, district, crop)] * water_rate.get((state, district, crop), 0.0)
            for state, district, crop in x
        )
    else:
        raise ValueError(f"Unsupported objective: {objective}")

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
        profit_terms = [
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
        prob += pulp.lpSum(calorie_terms) / CALORIE_SCALE >= _relaxed_rhs(
            float(initial_state_calories.get(state, 0.0))
        ) / CALORIE_SCALE
        prob += pulp.lpSum(profit_terms) / INCOME_SCALE >= _relaxed_rhs(
            float(initial_state_profit.get(state, 0.0))
        ) / INCOME_SCALE

    prob.solve(_solver("highs"))
    status = pulp.LpStatus.get(prob.status, str(prob.status))
    solution = {key: float(var.value() or 0.0) for key, var in x.items()}
    return status, solution


def metric_totals(area_map: dict[tuple[str, str, str], float], context: dict[str, object]) -> dict[str, float]:
    totals = {
        "N_emission": 0.0,
        "N_leach": 0.0,
        "AGHG": 0.0,
        "profit": 0.0,
        "Calorie": 0.0,
        "P_applied": 0.0,
        "N_applied": 0.0,
        "P_surplus": 0.0,
        "N_surplus": 0.0,
        "water": 0.0,
    }
    for key, area in area_map.items():
        if not area:
            continue
        yield_kg = context["yield_data"].get(key, 0.0)
        production_kg = area * yield_kg
        n_applied = area * context["nitrogen_rate"].get(key, 0.0)
        p_applied = area * context["p_rate"].get(key, 0.0)
        n_surplus = n_applied - production_kg * context["n_removed_rate"].get(key, 0.0)
        p_surplus = p_applied - production_kg * context["p_removed_rate"].get(key, 0.0)
        totals["N_applied"] += n_applied
        totals["P_applied"] += p_applied
        totals["N_surplus"] += n_surplus
        totals["P_surplus"] += p_surplus
        totals["Calorie"] += production_kg * context["calories_per_prod"].get(key, 0.0)
        totals["AGHG"] += area * context["aghg_per_ha"].get(key, 0.0)
        totals["N_leach"] += n_surplus * context["n_leach_rate"].get(key, 0.0)
        totals["N_emission"] += n_surplus * context["n_emission_rate"].get(key, 0.0)
        totals["water"] += area * context["water_rate"].get(key, 0.0)
        totals["profit"] += production_kg * 0.01 * (
            context["msp_per_prod"].get(key, 0.0) - context["cost_per_prod"].get(key, 0.0)
        )
    return totals


def build_metric_table(
    contexts: dict[str, dict[str, object]],
    *,
    use_historical_caps: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, float | str]] = []
    statuses: list[str] = []
    baseline_totals = {
        season: metric_totals(context["current_cereal_area"], context)
        for season, context in contexts.items()
    }
    for scenario in ["Water based", "Nitrogen based"]:
        objective = "water" if scenario == "Water based" else "nitrogen"
        optimized = {metric_key: 0.0 for _, metric_key in METRICS}
        baseline = {metric_key: 0.0 for _, metric_key in METRICS}
        for season, context in contexts.items():
            status, area_map = solve_endpoint(context, objective, use_historical_caps=use_historical_caps)
            statuses.append(f"{scenario} | {season}: {status}")
            if status != "Optimal":
                raise RuntimeError(f"{scenario} | {season} endpoint solve returned {status}")
            season_totals = metric_totals(area_map, context)
            for metric_key in baseline:
                baseline[metric_key] += baseline_totals[season][metric_key]
                optimized[metric_key] += season_totals[metric_key]
        for metric_label, metric_key in METRICS:
            original_total = baseline[metric_key]
            optimized_total = optimized[metric_key]
            pct_reduction = 100.0 * (original_total - optimized_total) / original_total
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric_label,
                    "original_total": original_total,
                    "optimized_total": optimized_total,
                    "pct_reduction": pct_reduction,
                    "display_pct_change": signed_display_change(
                        metric_label,
                        pct_reduction,
                        original_total,
                    ),
                }
            )
    table = pd.DataFrame(rows)
    table["metric"] = pd.Categorical(table["metric"], [metric for metric, _ in METRICS], ordered=True)
    return table.sort_values(["metric", "scenario"]).reset_index(drop=True), statuses


def write_latex_table(table: pd.DataFrame, out_tex: Path) -> None:
    pivot = table.pivot(index="metric", columns="scenario", values="pct_reduction").loc[
        [metric for metric, _ in METRICS]
    ]
    lines = [
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Metric & Water based (\%) & Nitrogen based (\%) \\",
        r"\midrule",
    ]
    for metric, row in pivot.iterrows():
        lines.append(f"{metric} & {row['Water based']:.3f} & {row['Nitrogen based']:.3f} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    out_tex.write_text("\n".join(lines) + "\n")


def write_audit_note(
    table: pd.DataFrame,
    statuses: list[str],
    contexts: dict[str, dict[str, object]],
    out_md: Path,
    *,
    use_historical_caps: bool = True,
) -> None:
    constraint_line = (
        "- district-crop historical maximum area ceilings,"
        if use_historical_caps
        else "- substitution among historically observed cereals without crop-specific historical area ceilings,"
    )
    lines = [
        "# Figure 2(b) clean deterministic rebuild audit",
        "",
        "This rebuild uses the same seasonal contexts as the clean Figure 2(a) frontier:",
        "- unchanged district cropped area,",
        "- crop substitution limited to historically grown crops,",
        constraint_line,
        "- state calorie constraints,",
        "- state profit constraints.",
        "",
        "The panel is regenerated deterministically for the two endpoint strategies only:",
        "- `Water based`: minimize water demand in each season under the shared constraint set.",
        "- `Nitrogen based`: minimize nitrogen surplus in each season under the shared constraint set.",
        "",
        (
            "This file is intended as the clean method-consistent alternative to the approved manuscript branch."
            if use_historical_caps
            else "This file is intended as the approved Figure 2(b) rebuild used in the revised manuscript."
        ),
        "It does not include whiskers, because the currently reproducible bootstrap pipeline is not yet aligned",
        (
            "with the strict ceiling-constrained model used for the clean endpoints."
            if use_historical_caps
            else "with the cleaned endpoint formulation used for this approved branch."
        ),
        "",
        "Season-level solve status:",
    ]
    for status in statuses:
        lines.append(f"- {status}")
    lines.extend(["", "Cap-floor repairs inherited from seasonal contexts:"])
    for season, context in contexts.items():
        lines.append(f"- {season}: {int(context['cap_repairs'])}")
    lines.extend(["", "Combined annual percentage reductions:"])
    for scenario in ["Water based", "Nitrogen based"]:
        subset = table[table["scenario"] == scenario]
        lines.append(f"## {scenario}")
        for row in subset.itertuples(index=False):
            lines.append(f"- {row.metric}: {row.pct_reduction:.3f}%")
        lines.append("")
    out_md.write_text("\n".join(lines).rstrip() + "\n")


def build_figure(table: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "font.family": "DejaVu Sans",
        }
    )
    metric_order = [metric for metric, _ in METRICS]
    water = table[table["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    nitrogen = table[table["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]

    fig, ax = plt.subplots(figsize=(7.0, 4.6), constrained_layout=True)
    positions = list(range(len(metric_order)))
    offset = 0.18
    bar_height = 0.32

    ax.barh(
        [p - offset for p in positions],
        water["display_pct_change"].to_numpy(),
        height=bar_height,
        color="#2a9d8f",
        edgecolor="black",
        linewidth=0.5,
        label="Water based",
        zorder=3,
    )
    ax.barh(
        [p + offset for p in positions],
        nitrogen["display_pct_change"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        label="Nitrogen based",
        zorder=3,
    )

    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("Change relative to baseline (%)")
    ax.set_title("Percentage Change in Socio-Environmental Objectives", fontweight="bold", pad=8)
    ax.text(-0.12, 1.02, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    min_x = min(water["display_pct_change"].min(), nitrogen["display_pct_change"].min())
    max_x = max(water["display_pct_change"].max(), nitrogen["display_pct_change"].max())
    ax.set_xlim(min(-52.0, float(min_x) - 5.0), max(30.0, float(max_x) + 5.0))
    ax.legend(loc="upper right", frameon=False, fontsize=8)

    fig.savefig(out_png, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(*, output_stem: str = DEFAULT_OUTPUT_STEM, use_historical_caps: bool = True) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    outputs = output_paths(output_stem)
    layout = default_layout(AUDIT_ROOT)
    contexts = {
        season: build_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    if not use_historical_caps:
        for context in contexts.values():
            context["max_area_constraints"] = {}
            context["cap_repairs"] = 0
    table, statuses = build_metric_table(contexts, use_historical_caps=use_historical_caps)
    table.to_csv(outputs["values_csv"], index=False)
    write_latex_table(table, outputs["values_tex"])
    write_audit_note(table, statuses, contexts, outputs["audit_md"], use_historical_caps=use_historical_caps)
    build_figure(table, outputs["png"], outputs["pdf"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    parser.add_argument(
        "--no-historical-caps",
        action="store_true",
        help="Drop the hard district-crop historical maximum area caps from the endpoint solves.",
    )
    args = parser.parse_args()
    main(output_stem=args.output_stem, use_historical_caps=not args.no_historical_caps)
