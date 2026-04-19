#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import math
import re
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated" / "figure2c"

sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    _fill_missing_from_hierarchical_means,
    _state_crop_and_crop_means,
)
from repro.legacy_notebook_runner import (  # noqa: E402
    NotebookRunConfig,
    _rewrite_source,
    extract_archive_if_needed,
)


GAMMA_VALUES = [i / 10 for i in range(11)]
CALORIE_SCALE = 1e9
INCOME_SCALE = 1e9
RELATIVE_RHS_TOL = 1e-9
ABSOLUTE_RHS_TOL = 1e-6
SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]+")


@dataclass(frozen=True)
class CulturalNotebookConfig:
    season: str
    notebook_name: str
    preamble_code_cell: int
    retain_crop: str
    history_frame_name: str


@dataclass
class SeasonContext:
    season: str
    retain_crop: str
    states: list[str]
    pairs_with_area: list[tuple[str, str]]
    districts_by_state: dict[str, list[str]]
    crops_by_pair: dict[tuple[str, str], list[str]]
    current_area: dict[tuple[str, str], float]
    current_cereal_area: dict[tuple[str, str, str], float]
    max_area_constraints: dict[tuple[str, str, str], float]
    nitrogen_rate: dict[tuple[str, str, str], float]
    nitrogen_removal_rate: dict[tuple[str, str, str], float]
    yield_data: dict[tuple[str, str, str], float]
    calories_per_prod: dict[tuple[str, str, str], float]
    msp_per_prod: dict[tuple[str, str, str], float]
    cost_per_prod: dict[tuple[str, str, str], float]
    initial_state_calories: dict[str, float]
    initial_state_profit: dict[str, float]
    initial_state_crop_area: dict[str, float]
    baseline_retained_area: float
    baseline_n_surplus: float
    cap_floor_repairs: int
    coefficient_imputed: int
    coefficient_screen_removed: int


def has_valid_figure2c_coefficients(
    key: tuple[str, str, str],
    *,
    yield_data: dict[tuple[str, str, str], float],
    calories_per_prod: dict[tuple[str, str, str], float],
    nitrogen_rate: dict[tuple[str, str, str], float],
    nitrogen_removal_rate: dict[tuple[str, str, str], float],
    msp_per_prod: dict[tuple[str, str, str], float],
    cost_per_prod: dict[tuple[str, str, str], float],
) -> bool:
    return (
        yield_data.get(key, 0.0) > 0
        and calories_per_prod.get(key, 0.0) > 0
        and key in nitrogen_rate
        and key in nitrogen_removal_rate
        and key in msp_per_prod
        and key in cost_per_prod
    )


NOTEBOOKS = {
    "kharif": CulturalNotebookConfig(
        season="kharif",
        notebook_name="kharif_n_culture.ipynb",
        preamble_code_cell=10,
        retain_crop="rice",
        history_frame_name="kharif",
    ),
    "rabi": CulturalNotebookConfig(
        season="rabi",
        notebook_name="rabi_n_cultural_cop.ipynb",
        preamble_code_cell=6,
        retain_crop="wheat",
        history_frame_name="rabi",
    ),
}


def relaxed_rhs(value: float) -> float:
    tolerance = max(abs(value) * RELATIVE_RHS_TOL, ABSOLUTE_RHS_TOL)
    return value - tolerance


def sanitize(text: str) -> str:
    return SANITIZE_RE.sub("_", str(text)).strip("_") or "x"


def solver() -> pulp.LpSolver:
    try:
        return pulp.HiGHS(msg=False)
    except Exception:
        return pulp.PULP_CBC_CMD(msg=False)


def cleanup_source(source: str) -> str:
    filtered_lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('print("Original Total'):
            continue
        filtered_lines.append(line)
    rewritten = "\n".join(filtered_lines)
    if source.endswith("\n"):
        rewritten += "\n"
    return rewritten


def execute_notebook_preamble(config: CulturalNotebookConfig, layout_root: Path) -> dict[str, object]:
    notebook_path = (AUDIT_ROOT / config.notebook_name).resolve()
    raw = json.loads(notebook_path.read_text())
    namespace: dict[str, object] = {"__name__": "__main__", "pd": pd}
    if "geopandas" not in sys.modules:
        sys.modules["geopandas"] = types.ModuleType("geopandas")

    layout = default_layout(layout_root)
    data_dir = extract_archive_if_needed(layout.root)
    run_config = NotebookRunConfig(
        notebook=notebook_path,
        data_dir=data_dir.resolve(),
        generated_dir=layout.generated_dir.resolve(),
        use_cbc=False,
    )

    code_idx = 0
    for cell in raw.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        code_idx += 1
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue

        rewritten = cleanup_source(_rewrite_source(source, run_config))
        rewritten = rewritten.replace("import geopandas as gpd\n", "")
        if code_idx == config.preamble_code_cell:
            rewritten = rewritten.split("gamma_values =", 1)[0]

        try:
            parsed = ast.parse(rewritten, mode="exec")
        except SyntaxError:
            parsed = None

        if (
            parsed is not None
            and len(parsed.body) == 1
            and isinstance(parsed.body[0], ast.Expr)
            and isinstance(parsed.body[0].value, ast.Name)
            and parsed.body[0].value.id not in namespace
        ):
            if code_idx == config.preamble_code_cell:
                break
            continue

        if rewritten.strip():
            exec(compile(rewritten, f"{config.notebook_name}:cell_{code_idx}", "exec"), namespace, namespace)

        if code_idx == config.preamble_code_cell:
            break

    return namespace


def build_context(config: CulturalNotebookConfig) -> SeasonContext:
    namespace = execute_notebook_preamble(config, AUDIT_ROOT)
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
    cereals = sorted(frame["Crop"].dropna().astype(str).unique().tolist())

    history = namespace[config.history_frame_name].copy()
    history = history.rename(columns={"state": "State", "district": "District", "crop": "Crop"})
    history["State"] = history["State"].astype(str)
    history["District"] = history["District"].astype(str)
    history["Crop"] = history["Crop"].astype(str)
    history = history[history["Crop"].isin(cereals)].copy()

    current_area = frame.groupby(["State", "District"])["Area (Hectare)"].sum().astype(float).to_dict()
    current_cereal_area = (
        frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()
    )
    historical_cereal_area = (
        history.groupby(["State", "District", "Crop"])["Area (Hectare)"].max().astype(float).to_dict()
    )
    max_area_constraints = dict(historical_cereal_area)

    cap_floor_repairs = 0
    for key, area in current_cereal_area.items():
        if area <= 0:
            continue
        existing = max_area_constraints.get(key)
        if existing is None or existing < area:
            max_area_constraints[key] = area
            cap_floor_repairs += 1

    districts_by_state = {
        state: sorted(group["District"].dropna().astype(str).unique().tolist())
        for state, group in frame.groupby("State", sort=True)
    }
    nitrogen_rate = namespace["nitrogen_rate"]
    nitrogen_removal_rate = namespace["nitrogen_removal_rate_perkg"]
    yield_data = namespace["yield_data"]
    calories_per_prod = namespace["calories_per_prod"]
    msp_per_prod = namespace["MSP_per_prod"]
    cost_per_prod = namespace["cost_per_area"]

    yield_state_crop_means, yield_crop_means = _state_crop_and_crop_means(yield_data)
    calorie_state_crop_means, calorie_crop_means = _state_crop_and_crop_means(calories_per_prod)
    nitrogen_state_crop_means, nitrogen_crop_means = _state_crop_and_crop_means(nitrogen_rate)
    nrem_state_crop_means, nrem_crop_means = _state_crop_and_crop_means(nitrogen_removal_rate)
    msp_state_crop_means, msp_crop_means = _state_crop_and_crop_means(msp_per_prod)
    cost_state_crop_means, cost_crop_means = _state_crop_and_crop_means(cost_per_prod)

    crops_by_pair: dict[tuple[str, str], list[str]] = {}
    coefficient_imputed = 0
    coefficient_screen_removed = 0
    for state, district in state_district_pairs:
        valid_crops: list[str] = []
        for crop in cereals:
            key = (state, district, crop)
            if historical_cereal_area.get(key, 0.0) <= 0:
                continue
            if current_area.get((state, district), 0.0) > 0 and not has_valid_figure2c_coefficients(
                key,
                yield_data=yield_data,
                calories_per_prod=calories_per_prod,
                nitrogen_rate=nitrogen_rate,
                nitrogen_removal_rate=nitrogen_removal_rate,
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
                    mapping=nitrogen_removal_rate,
                    state_crop_means=nrem_state_crop_means,
                    crop_means=nrem_crop_means,
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
                if imputed_any and has_valid_figure2c_coefficients(
                    key,
                    yield_data=yield_data,
                    calories_per_prod=calories_per_prod,
                    nitrogen_rate=nitrogen_rate,
                    nitrogen_removal_rate=nitrogen_removal_rate,
                    msp_per_prod=msp_per_prod,
                    cost_per_prod=cost_per_prod,
                ):
                    coefficient_imputed += 1
            if has_valid_figure2c_coefficients(
                key,
                yield_data=yield_data,
                calories_per_prod=calories_per_prod,
                nitrogen_rate=nitrogen_rate,
                nitrogen_removal_rate=nitrogen_removal_rate,
                msp_per_prod=msp_per_prod,
                cost_per_prod=cost_per_prod,
            ):
                valid_crops.append(crop)
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
    initial_state_crop_area = (
        frame[frame["Crop"] == config.retain_crop].groupby("State")["Area (Hectare)"].sum().astype(float).to_dict()
    )
    baseline_retained_area = sum(
        current_cereal_area.get((state, district, config.retain_crop), 0.0)
        for state, district in pairs_with_area
        if (state, district, config.retain_crop) in current_cereal_area
    )
    baseline_n_surplus = sum(
        current_cereal_area.get((state, district, crop), 0.0)
        * (
            nitrogen_rate.get((state, district, crop), 0.0)
            - yield_data.get((state, district, crop), 0.0)
            * nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district in pairs_with_area
        for crop in crops_by_pair[(state, district)]
    )

    return SeasonContext(
        season=config.season,
        retain_crop=config.retain_crop,
        states=states,
        pairs_with_area=pairs_with_area,
        districts_by_state=districts_by_state,
        crops_by_pair=crops_by_pair,
        current_area=current_area,
        current_cereal_area=current_cereal_area,
        max_area_constraints=max_area_constraints,
        nitrogen_rate=nitrogen_rate,
        nitrogen_removal_rate=nitrogen_removal_rate,
        yield_data=yield_data,
        calories_per_prod=calories_per_prod,
        msp_per_prod=msp_per_prod,
        cost_per_prod=cost_per_prod,
        initial_state_calories=initial_state_calories,
        initial_state_profit=initial_state_profit,
        initial_state_crop_area=initial_state_crop_area,
        baseline_retained_area=baseline_retained_area,
        baseline_n_surplus=baseline_n_surplus,
        cap_floor_repairs=cap_floor_repairs,
        coefficient_imputed=coefficient_imputed,
        coefficient_screen_removed=coefficient_screen_removed,
    )


def solve_gamma(
    context: SeasonContext,
    gamma: float,
    use_historical_caps: bool,
    retention_level: str = "state",
) -> dict[str, float | str]:
    prob = pulp.LpProblem(
        f"Figure2C_{context.season}_{context.retain_crop}_{gamma:.2f}",
        pulp.LpMinimize,
    )
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}

    for state, district in context.pairs_with_area:
        for crop in context.crops_by_pair[(state, district)]:
            name = f"area__{sanitize(state)}__{sanitize(district)}__{sanitize(crop)}"
            x[(state, district, crop)] = pulp.LpVariable(name, lowBound=0, cat=pulp.LpContinuous)

    objective_n = pulp.lpSum(
        x[(state, district, crop)]
        * (
            context.nitrogen_rate.get((state, district, crop), 0.0)
            - context.yield_data.get((state, district, crop), 0.0)
            * context.nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district, crop in x
    )
    prob += objective_n

    for state, district in context.pairs_with_area:
        prob += (
            pulp.lpSum(x[(state, district, crop)] for crop in context.crops_by_pair[(state, district)])
            == context.current_area.get((state, district), 0.0)
        )
        if use_historical_caps:
            for crop in context.crops_by_pair[(state, district)]:
                cap = context.max_area_constraints.get((state, district, crop))
                if cap is not None:
                    prob += x[(state, district, crop)] <= cap

    for state in context.states:
        valid_districts = context.districts_by_state.get(state, [])
        calorie_terms = [
            x[(state, district, crop)]
            * context.yield_data.get((state, district, crop), 0.0)
            * context.calories_per_prod.get((state, district, crop), 0.0)
            for district in valid_districts
            for crop in context.crops_by_pair.get((state, district), [])
            if (state, district, crop) in x
        ]
        profit_terms = [
            x[(state, district, crop)]
            * context.yield_data.get((state, district, crop), 0.0)
            * 0.01
            * (
                context.msp_per_prod.get((state, district, crop), 0.0)
                - context.cost_per_prod.get((state, district, crop), 0.0)
            )
            for district in valid_districts
            for crop in context.crops_by_pair.get((state, district), [])
            if (state, district, crop) in x
        ]
        prob += pulp.lpSum(calorie_terms) / CALORIE_SCALE >= relaxed_rhs(
            context.initial_state_calories.get(state, 0.0)
        ) / CALORIE_SCALE
        prob += pulp.lpSum(profit_terms) / INCOME_SCALE >= relaxed_rhs(
            context.initial_state_profit.get(state, 0.0)
        ) / INCOME_SCALE
        if retention_level == "state":
            retain_terms = [
                x[(state, district, context.retain_crop)]
                for district in valid_districts
                if (state, district, context.retain_crop) in x
            ]
            prob += pulp.lpSum(retain_terms) >= gamma * context.initial_state_crop_area.get(state, 0.0)
        elif retention_level == "district":
            for district in valid_districts:
                baseline = context.current_cereal_area.get((state, district, context.retain_crop), 0.0)
                if baseline > 0 and (state, district, context.retain_crop) in x:
                    prob += x[(state, district, context.retain_crop)] >= gamma * baseline
        else:
            raise ValueError(f"Unsupported retention level: {retention_level}")

    prob.solve(solver())
    status = pulp.LpStatus.get(prob.status, str(prob.status))
    optimized_n_surplus = float(pulp.value(objective_n)) if pulp.value(objective_n) is not None else math.nan
    pct_reduction = 100.0 * (context.baseline_n_surplus - optimized_n_surplus) / context.baseline_n_surplus
    optimized_retained_area = sum(
        (x[(state, district, context.retain_crop)].value() or 0.0)
        for state, district in context.pairs_with_area
        if (state, district, context.retain_crop) in x
    )
    realized_retained_share_pct = (
        100.0 * optimized_retained_area / context.baseline_retained_area
        if context.baseline_retained_area > 0
        else math.nan
    )
    realized_staple_replacement_pct = (
        100.0 * (context.baseline_retained_area - optimized_retained_area) / context.baseline_retained_area
        if context.baseline_retained_area > 0
        else math.nan
    )
    return {
        "season": context.season,
        "retain_crop": context.retain_crop,
        "gamma": gamma,
        "nominal_substitution_pct": 100.0 * (1.0 - gamma),
        "original_n_surplus": context.baseline_n_surplus,
        "optimized_n_surplus": optimized_n_surplus,
        "pct_reduction_n_surplus": pct_reduction,
        "baseline_retained_area": context.baseline_retained_area,
        "optimized_retained_area": optimized_retained_area,
        "realized_retained_share_pct": realized_retained_share_pct,
        "realized_staple_replacement_pct": realized_staple_replacement_pct,
        "solve_status": status,
        "use_historical_caps": bool(use_historical_caps),
        "retention_level": retention_level,
        "cap_floor_repairs": context.cap_floor_repairs,
    }


def solve_season(
    context: SeasonContext,
    use_historical_caps: bool,
    retention_level: str = "state",
) -> pd.DataFrame:
    rows = [
        solve_gamma(
            context,
            gamma,
            use_historical_caps=use_historical_caps,
            retention_level=retention_level,
        )
        for gamma in GAMMA_VALUES
    ]
    out = pd.DataFrame(rows).sort_values("gamma").reset_index(drop=True)
    return out


def combine_seasons(kharif: pd.DataFrame, rabi: pd.DataFrame, label: str) -> pd.DataFrame:
    combined = pd.concat([kharif, rabi], ignore_index=True)
    agg = (
        combined.groupby("gamma", as_index=False)
        .agg(
            {
                "nominal_substitution_pct": "first",
                "original_n_surplus": "sum",
                "optimized_n_surplus": "sum",
                "baseline_retained_area": "sum",
                "optimized_retained_area": "sum",
            }
        )
        .sort_values("nominal_substitution_pct")
        .reset_index(drop=True)
    )
    agg["pct_reduction_n_surplus"] = (
        100.0 * (agg["original_n_surplus"] - agg["optimized_n_surplus"]) / agg["original_n_surplus"]
    )
    agg["realized_retained_share_pct"] = (
        100.0 * agg["optimized_retained_area"] / agg["baseline_retained_area"]
    )
    agg["realized_staple_replacement_pct"] = (
        100.0 * (agg["baseline_retained_area"] - agg["optimized_retained_area"]) / agg["baseline_retained_area"]
    )
    agg["configuration"] = label
    return agg


def plot_nominal_panel(frame: pd.DataFrame, output_stem: str) -> tuple[Path, Path]:
    plot_frame = frame.sort_values("nominal_substitution_pct").reset_index(drop=True)
    with plt.style.context("default"):
        fig, ax = plt.subplots(figsize=(6.2, 4.4))
        ax.set_facecolor("white")

        ax.plot(
            plot_frame["nominal_substitution_pct"],
            plot_frame["pct_reduction_n_surplus"],
            color="#348ABD",
            linewidth=2.1,
            marker="o",
            markersize=4.0,
            markerfacecolor="#348ABD",
            markeredgewidth=0.0,
            zorder=3,
        )

        for x in (25, 50, 75):
            ax.axvline(x, color="gray", linestyle="--", linewidth=1.0, alpha=0.9, zorder=1)

        minimum = plot_frame.iloc[0]
        maximum = plot_frame.iloc[-1]
        ax.plot(
            maximum["nominal_substitution_pct"],
            maximum["pct_reduction_n_surplus"],
            marker="o",
            markersize=5.5,
            color="red",
            linestyle="None",
            label="Maximum alternate crop penetration",
            zorder=4,
        )
        ax.plot(
            minimum["nominal_substitution_pct"],
            minimum["pct_reduction_n_surplus"],
            marker="o",
            markersize=5.5,
            color="green",
            linestyle="None",
            label="Minimum alternate crop penetration",
            zorder=4,
        )

        ax.set_xlim(-2, 102)
        y_min = float(plot_frame["pct_reduction_n_surplus"].min())
        y_max = float(plot_frame["pct_reduction_n_surplus"].max())
        pad = max(0.2, 0.08 * (y_max - y_min))
        ax.set_ylim(y_min - pad, y_max + pad)
        ax.set_xlabel("Nominal allowed staple-area substitution (%)", fontsize=12, fontweight="bold")
        ax.set_ylabel("% reduction in Nitrogen Surplus", fontsize=12, fontweight="bold")
        ax.set_title("Cultural significance of Rice and Wheat", fontsize=15, fontweight="bold", pad=8)
        ax.text(-0.1, 1.02, "c", transform=ax.transAxes, fontsize=12, fontweight="bold")
        ax.grid(axis="y", color="#d8d8d8", linewidth=0.7, alpha=0.75)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(loc="lower right", prop={"weight": "bold", "size": 8.5}, frameon=True, facecolor="white")

        png_path = FIG_DIR / f"{output_stem}.png"
        pdf_path = FIG_DIR / f"{output_stem}.pdf"
        fig.tight_layout()
        fig.savefig(png_path, dpi=400, bbox_inches="tight", facecolor="white")
        fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
        plt.close(fig)
    return png_path, pdf_path


def plot_realized_panel(frame: pd.DataFrame, output_stem: str) -> tuple[Path, Path]:
    plot_frame = frame.sort_values("realized_staple_replacement_pct").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))

    ax.plot(
        plot_frame["realized_staple_replacement_pct"],
        plot_frame["pct_reduction_n_surplus"],
        color="#2166ac",
        linewidth=1.6,
        marker="o",
        markersize=4.8,
        markerfacecolor="white",
        markeredgewidth=1.1,
        markeredgecolor="#2166ac",
        zorder=3,
    )

    minimum = plot_frame.iloc[0]
    maximum = plot_frame.iloc[-1]
    ax.scatter(
        minimum["realized_staple_replacement_pct"],
        minimum["pct_reduction_n_surplus"],
        s=68,
        color="#1b9e77",
        edgecolors="black",
        linewidths=0.6,
        zorder=4,
    )
    ax.scatter(
        maximum["realized_staple_replacement_pct"],
        maximum["pct_reduction_n_surplus"],
        s=68,
        color="#d95f02",
        edgecolors="black",
        linewidths=0.6,
        zorder=4,
    )

    x_min = float(plot_frame["realized_staple_replacement_pct"].min())
    x_max = float(plot_frame["realized_staple_replacement_pct"].max())
    x_pad = max(0.05, 0.1 * (x_max - x_min))
    y_min = float(plot_frame["pct_reduction_n_surplus"].min())
    y_max = float(plot_frame["pct_reduction_n_surplus"].max())
    y_pad = max(0.15, 0.1 * (y_max - y_min))

    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xlabel("Realized rice+wheat area replaced by alternate cereals (%)")
    ax.set_ylabel("% reduction in Nitrogen Surplus")
    ax.set_title("Cultural significance of Rice and Wheat", fontsize=11, pad=8)
    ax.grid(axis="both", color="#d6d6d6", linewidth=0.6, alpha=0.85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    png_path = FIG_DIR / f"{output_stem}.png"
    pdf_path = FIG_DIR / f"{output_stem}.pdf"
    fig.tight_layout()
    fig.savefig(png_path, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path, pdf_path


def plot_cap_sensitivity(
    method_frame: pd.DataFrame,
    no_cap_frame: pd.DataFrame,
    output_stem: str,
) -> tuple[Path, Path]:
    method_plot = method_frame.sort_values("nominal_substitution_pct").reset_index(drop=True)
    no_cap_plot = no_cap_frame.sort_values("nominal_substitution_pct").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.plot(
        method_plot["nominal_substitution_pct"],
        method_plot["pct_reduction_n_surplus"],
        color="#2166ac",
        linewidth=1.7,
        marker="o",
        markersize=4.5,
        label="Method-consistent constraints",
    )
    ax.plot(
        no_cap_plot["nominal_substitution_pct"],
        no_cap_plot["pct_reduction_n_surplus"],
        color="#b2182b",
        linewidth=1.5,
        marker="s",
        markersize=4.0,
        label="Without historical crop-area caps",
    )
    for x in (25, 50, 75):
        ax.axvline(x, color="#8a8a8a", linestyle="--", linewidth=0.8, alpha=0.8, zorder=1)

    ax.set_xlim(-2, 102)
    y_min = min(
        float(method_plot["pct_reduction_n_surplus"].min()),
        float(no_cap_plot["pct_reduction_n_surplus"].min()),
    )
    y_max = max(
        float(method_plot["pct_reduction_n_surplus"].max()),
        float(no_cap_plot["pct_reduction_n_surplus"].max()),
    )
    pad = max(0.5, 0.08 * (y_max - y_min))
    ax.set_ylim(y_min - pad, y_max + pad)
    ax.set_xlabel("Nominal allowed staple-area substitution (%)")
    ax.set_ylabel("% reduction in Nitrogen Surplus")
    ax.set_title("Figure 2(c) cap-sensitivity audit", fontsize=11, pad=8)
    ax.grid(axis="y", color="#d6d6d6", linewidth=0.6, alpha=0.85)
    ax.legend(frameon=False, fontsize=8.5, loc="best")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    png_path = FIG_DIR / f"{output_stem}.png"
    pdf_path = FIG_DIR / f"{output_stem}.pdf"
    fig.tight_layout()
    fig.savefig(png_path, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png_path, pdf_path


def write_audit(
    kharif_context: SeasonContext,
    rabi_context: SeasonContext,
    kharif_caps: pd.DataFrame,
    rabi_caps: pd.DataFrame,
    combined_caps: pd.DataFrame,
    kharif_no_caps: pd.DataFrame,
    rabi_no_caps: pd.DataFrame,
    combined_no_caps: pd.DataFrame,
    combined_equation_aligned: pd.DataFrame,
) -> Path:
    method_min = combined_caps["pct_reduction_n_surplus"].min()
    method_max = combined_caps["pct_reduction_n_surplus"].max()
    no_cap_min = combined_no_caps["pct_reduction_n_surplus"].min()
    no_cap_max = combined_no_caps["pct_reduction_n_surplus"].max()
    equation_min = combined_equation_aligned["pct_reduction_n_surplus"].min()
    equation_max = combined_equation_aligned["pct_reduction_n_surplus"].max()

    lines = [
        "# Figure 2(c) regeneration audit",
        "",
        "This rebuild uses the cultural-significance notebooks",
        "`kharif_n_culture.ipynb` and `rabi_n_cultural_cop.ipynb`, but executes only their",
        "data-preparation preambles and then resolves the optimization cleanly in Python.",
        "",
        "The notebook preamble contains broken diagnostic print statements in the rabi notebook;",
        "those lines are stripped before execution because they do not affect any model inputs.",
        "",
        "Two configurations are exported:",
        "",
        "1. `method_consistent`: nitrogen-minimization with unchanged district cropped area,",
        "   historically observed district crops as the admissible menu, historical maximum crop-area",
        "   caps, state calorie constraints, state profit constraints, and the seasonal rice/wheat",
        "   retention constraint.",
        "2. `no_historical_caps`: the same model, but with the historical crop-area cap removed",
        "   to diagnose the source of the published panel magnitude.",
        "",
        (
            "Historically admissible district-crop options missing one or more 2017 coefficient bundles "
            "are completed from state-crop means and then crop-level means before solving."
        ),
        (
            f"Completed district-crop coefficient bundles: kharif {kharif_context.coefficient_imputed}, "
            f"rabi {rabi_context.coefficient_imputed}."
        ),
        "",
        "Combined national nitrogen-surplus reduction ranges:",
        f"- method-consistent: {method_min:.3f}% to {method_max:.3f}%",
        f"- state-retention (no historical caps): {no_cap_min:.3f}% to {no_cap_max:.3f}%",
        (
            f"- equation-aligned (district retention, no historical caps): "
            f"{equation_min:.3f}% to {equation_max:.3f}%"
        ),
        "",
        "Axis interpretation:",
        "- The legacy combined notebook sets `gamma_values = 100 - summed_df['Gamma'] * 100` and labels that axis as substitution rate.",
        "- That quantity is a nominal retention-relaxation parameter, not the realized rice+wheat area replaced after optimization.",
        (
            f"- In the method-consistent rebuild, the realized combined rice+wheat replacement is only "
            f"{combined_caps['realized_staple_replacement_pct'].min():.3f}% to "
            f"{combined_caps['realized_staple_replacement_pct'].max():.3f}%."
        ),
        "",
        "Interpretation:",
        "- The published panel magnitude is only approached when the historical crop-area caps are off.",
        "- The state-retention no-cap variant stays closest to the published Figure 2(c) magnitude.",
        "- The district-level no-cap variant stays closer to the subsection equations x_{i,r} and x_{i,w}.",
        "- Once those caps are enforced cleanly, the cultural-significance curve remains monotone but drops to about 3%.",
        "- The legacy x-axis label therefore overstates how much staple area is actually replaced in the clean rebuild.",
        "- The historical crop-area cap is therefore the dominant source of the discrepancy between the legacy panel and the method-consistent rebuild.",
        "",
        "Season-level ranges:",
        f"- kharif method-consistent: {kharif_caps['pct_reduction_n_surplus'].min():.3f}% to {kharif_caps['pct_reduction_n_surplus'].max():.3f}%",
        f"- rabi method-consistent: {rabi_caps['pct_reduction_n_surplus'].min():.3f}% to {rabi_caps['pct_reduction_n_surplus'].max():.3f}%",
        f"- kharif without caps: {kharif_no_caps['pct_reduction_n_surplus'].min():.3f}% to {kharif_no_caps['pct_reduction_n_surplus'].max():.3f}%",
        f"- rabi without caps: {rabi_no_caps['pct_reduction_n_surplus'].min():.3f}% to {rabi_no_caps['pct_reduction_n_surplus'].max():.3f}%",
        "",
        "For manuscript revision, there are therefore two plausible candidate panels if the goal",
        "is to stay near the legacy magnitude while avoiding a silent mismatch in interpretation:",
        "- use the state-level/no-cap variant and revise the Methods paragraph to state-level retention explicitly;",
        "- or use the district-level/no-cap variant and revise the Methods paragraph to clarify that the cultural sensitivity analysis relaxes historical area caps.",
        "",
        "The strict method-consistent panel remains the cleanest reconstruction of the primary optimization framework.",
        "",
    ]
    audit_path = DATA_DIR / "figure2c_regeneration_audit.md"
    audit_path.write_text("\n".join(lines))
    return audit_path


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    kharif_context = build_context(NOTEBOOKS["kharif"])
    rabi_context = build_context(NOTEBOOKS["rabi"])

    kharif_caps = solve_season(kharif_context, use_historical_caps=True)
    rabi_caps = solve_season(rabi_context, use_historical_caps=True)
    combined_caps = combine_seasons(kharif_caps, rabi_caps, label="method_consistent")

    kharif_no_caps = solve_season(kharif_context, use_historical_caps=False)
    rabi_no_caps = solve_season(rabi_context, use_historical_caps=False)
    combined_no_caps = combine_seasons(kharif_no_caps, rabi_no_caps, label="no_historical_caps")

    kharif_equation_aligned = solve_season(
        kharif_context,
        use_historical_caps=False,
        retention_level="district",
    )
    rabi_equation_aligned = solve_season(
        rabi_context,
        use_historical_caps=False,
        retention_level="district",
    )
    combined_equation_aligned = combine_seasons(
        kharif_equation_aligned,
        rabi_equation_aligned,
        label="equation_aligned_district_no_historical_caps",
    )

    kharif_caps.to_csv(DATA_DIR / "kharif_method_consistent.csv", index=False)
    rabi_caps.to_csv(DATA_DIR / "rabi_method_consistent.csv", index=False)
    combined_caps.to_csv(DATA_DIR / "combined_method_consistent.csv", index=False)
    kharif_no_caps.to_csv(DATA_DIR / "kharif_no_historical_caps.csv", index=False)
    rabi_no_caps.to_csv(DATA_DIR / "rabi_no_historical_caps.csv", index=False)
    combined_no_caps.to_csv(DATA_DIR / "combined_no_historical_caps.csv", index=False)
    kharif_equation_aligned.to_csv(DATA_DIR / "kharif_equation_aligned_district_no_caps.csv", index=False)
    rabi_equation_aligned.to_csv(DATA_DIR / "rabi_equation_aligned_district_no_caps.csv", index=False)
    combined_equation_aligned.to_csv(DATA_DIR / "combined_equation_aligned_district_no_caps.csv", index=False)

    plot_nominal_panel(combined_caps, output_stem="figure2c_regenerated_method_consistent")
    plot_realized_panel(combined_caps, output_stem="figure2c_regenerated_realized_replacement")
    plot_nominal_panel(combined_no_caps, output_stem="figure2c_regenerated_state_retention")
    plot_nominal_panel(
        combined_equation_aligned,
        output_stem="figure2c_regenerated_district_retention",
    )
    plot_cap_sensitivity(
        combined_caps,
        combined_no_caps,
        output_stem="figure2c_cap_sensitivity_audit",
    )
    write_audit(
        kharif_context,
        rabi_context,
        kharif_caps,
        rabi_caps,
        combined_caps,
        kharif_no_caps,
        rabi_no_caps,
        combined_no_caps,
        combined_equation_aligned,
    )


if __name__ == "__main__":
    main()
