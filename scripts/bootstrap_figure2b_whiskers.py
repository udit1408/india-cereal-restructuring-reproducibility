#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
GENERATED_DIR = AUDIT_ROOT / "generated"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"
BOOT_DIR = DATA_DIR / "figure2b_bootstrap"

sys.path.insert(0, str(AUDIT_ROOT))
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _prepare_namespace  # noqa: E402


SCENARIO_FILES = {
    "Water based": [
        GENERATED_DIR / "water_based_opt_cop_kharif.csv",
        GENERATED_DIR / "water_based_opt_cop_rabi.csv",
    ],
    "Nitrogen based": [
        GENERATED_DIR / "nutrient_based_opt_cop_kharif.csv",
        GENERATED_DIR / "nitrogen_surplus_rbased_opt_cop_rabi.csv",
    ],
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

NOTEBOOKS = {
    ("Nitrogen based", "kharif"): "kharif_nitrogen_min.ipynb",
    ("Nitrogen based", "rabi"): "rabi__nitrogen_kharif_cop.ipynb",
    ("Water based", "kharif"): "kharif_water_cop.ipynb",
    ("Water based", "rabi"): "rabi_water_cop.ipynb",
}

CANON_RE = re.compile(r"[^a-z0-9_]+")
MISSING_TOKEN = "__missing__"
GLPSOL_PATH = "/opt/homebrew/bin/glpsol"
RELATIVE_RHS_TOL = 1e-9
ABSOLUTE_RHS_TOL = 1e-6

OUT_ITERATIONS = BOOT_DIR / "figure2b_bootstrap_iterations.csv"
OUT_SUMMARY = BOOT_DIR / "figure2b_bootstrap_summary.csv"
OUT_DETERMINISTIC_CHECK = BOOT_DIR / "figure2b_deterministic_reproduction_check.csv"
OUT_AUDIT = BOOT_DIR / "figure2b_bootstrap_audit.md"
OUT_PNG = FIG_DIR / "figure2b_regenerated_with_whiskers.png"
OUT_PDF = FIG_DIR / "figure2b_regenerated_with_whiskers.pdf"


@dataclass(frozen=True)
class ScenarioConfig:
    scenario: str
    season: str
    notebook: str
    objective: str
    enforce_profit: bool


@dataclass
class SeasonContext:
    scenario: str
    season: str
    objective: str
    enforce_profit: bool
    states: list[str]
    allowed_triples: list[tuple[str, str, str]]
    current_area_sd: dict[tuple[str, str], float]
    current_cereal_area: dict[tuple[str, str, str], float]
    pair_to_keys: dict[tuple[str, str], list[tuple[str, str, str]]]
    state_keys: dict[str, list[tuple[str, str, str]]]
    profit_keys: dict[str, list[tuple[str, str, str]]]
    district_to_state: dict[str, str]
    yield_data: dict[tuple[str, str, str], float]
    nitrogen_rate: dict[tuple[str, str, str], float]
    p_rate: dict[tuple[str, str, str], float]
    water_rate: dict[tuple[str, str, str], float]
    n_removed_rate: dict[tuple[str, str, str], float]
    p_removed_rate: dict[tuple[str, str, str], float]
    calories_per_prod: dict[tuple[str, str, str], float]
    msp_per_prod: dict[tuple[str, str, str], float]
    cost_per_prod: dict[tuple[str, str, str], float]
    aghg_per_ha: dict[tuple[str, str, str], float]
    n_leach_rate: dict[tuple[str, str, str], float]
    n_emission_rate: dict[tuple[str, str, str], float]
    initial_state_calories: dict[str, float]
    initial_state_profit: dict[str, float]
    raw_panel: pd.DataFrame
    exact_pool: dict[tuple[str, str, str], list[tuple[float, float, float]]]
    state_crop_pool: dict[tuple[str, str], list[tuple[float, float, float]]]
    crop_pool: dict[str, list[tuple[float, float, float]]]
    exact_pool_mean: dict[tuple[str, str, str], tuple[float, float, float]]
    state_crop_pool_mean: dict[tuple[str, str], tuple[float, float, float]]
    crop_pool_mean: dict[str, tuple[float, float, float]]
    deterministic_totals: dict[str, float]


SCENARIOS = [
    ScenarioConfig("Nitrogen based", "kharif", NOTEBOOKS[("Nitrogen based", "kharif")], "nitrogen", True),
    ScenarioConfig("Nitrogen based", "rabi", NOTEBOOKS[("Nitrogen based", "rabi")], "nitrogen", False),
    ScenarioConfig("Water based", "kharif", NOTEBOOKS[("Water based", "kharif")], "water", True),
    ScenarioConfig("Water based", "rabi", NOTEBOOKS[("Water based", "rabi")], "water", False),
]


def canon(value: object) -> str:
    if pd.isna(value):
        return MISSING_TOKEN
    text = str(value).strip().lower()
    if not text:
        return MISSING_TOKEN
    return text


def sanitize(text: str) -> str:
    return CANON_RE.sub("_", text).strip("_") or "x"


def relaxed_rhs(value: float) -> float:
    tolerance = max(abs(value) * RELATIVE_RHS_TOL, ABSOLUTE_RHS_TOL)
    return value - tolerance


def lower_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for src, dst in (("State", "state"), ("District", "district"), ("Crop", "crop")):
        if src in frame.columns and dst not in frame.columns:
            rename_map[src] = dst
    out = frame.rename(columns=rename_map).copy()
    for col in ("state", "district", "crop"):
        if col in out.columns:
            out[col] = out[col].map(canon)
    return out


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
            out[(canon(key[0]), canon(key[1]), canon(key[2]))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def load_existing_centers() -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    metric_cols = {
        "Nitrogen Emission": ("Original N_emission", "Optimized N_emission"),
        "Nitrogen Leach": ("Original N_leach", "Optimized N_leach"),
        "Greenhouse Gas emission": ("Original AGHG", "Optimized AGHG"),
        "Profit": ("Original profit", "Optimized profit"),
        "Calorie": ("Original Calorie", "Optimized Calorie"),
        "Phosphorus application": ("Original Total P Applied", "Optimized Total P Applied"),
        "Nitrogen application": ("Original Total N Applied", "Optimized Total N Applied"),
        "Phosphorus Surplus": ("Original Total P surplus", "Optimized Total P surplus"),
        "Nitrogen Surplus": ("Original Total N surplus", "Optimized Total N surplus"),
        "Water Demand": ("Original water", "Optimized water"),
    }
    for scenario, files in SCENARIO_FILES.items():
        frames = []
        for path in files:
            frame = pd.read_csv(path)
            if frame.columns[0].startswith("Unnamed") or frame.columns[0] == "":
                frame = frame.drop(columns=frame.columns[0])
            frames.append(frame)
        combined = pd.concat(frames, ignore_index=True)
        for metric_label, (orig_col, opt_col) in metric_cols.items():
            original_total = combined[orig_col].sum()
            optimized_total = combined[opt_col].sum()
            pct_reduction = 100.0 * (original_total - optimized_total) / original_total
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric_label,
                    "center_pct_reduction": pct_reduction,
                    "center_display_pct": -pct_reduction,
                }
            )
    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["metric", "scenario"]).reset_index(drop=True)


def metric_totals(
    area_map: dict[tuple[str, str, str], float],
    yield_data: dict[tuple[str, str, str], float],
    nitrogen_rate: dict[tuple[str, str, str], float],
    p_rate: dict[tuple[str, str, str], float],
    water_rate: dict[tuple[str, str, str], float],
    n_removed_rate: dict[tuple[str, str, str], float],
    p_removed_rate: dict[tuple[str, str, str], float],
    calories_per_prod: dict[tuple[str, str, str], float],
    msp_per_prod: dict[tuple[str, str, str], float],
    cost_per_prod: dict[tuple[str, str, str], float],
    aghg_per_ha: dict[tuple[str, str, str], float],
    n_leach_rate: dict[tuple[str, str, str], float],
    n_emission_rate: dict[tuple[str, str, str], float],
) -> dict[str, float]:
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
        yield_kg = yield_data.get(key, 0.0)
        production_kg = area * yield_kg
        n_applied = area * nitrogen_rate.get(key, 0.0)
        p_applied = area * p_rate.get(key, 0.0)
        n_surplus = n_applied - production_kg * n_removed_rate.get(key, 0.0)
        p_surplus = p_applied - production_kg * p_removed_rate.get(key, 0.0)
        totals["N_applied"] += n_applied
        totals["P_applied"] += p_applied
        totals["N_surplus"] += n_surplus
        totals["P_surplus"] += p_surplus
        totals["Calorie"] += production_kg * calories_per_prod.get(key, 0.0)
        totals["AGHG"] += area * aghg_per_ha.get(key, 0.0)
        totals["N_leach"] += n_surplus * n_leach_rate.get(key, 0.0)
        totals["N_emission"] += n_surplus * n_emission_rate.get(key, 0.0)
        totals["water"] += area * water_rate.get(key, 0.0)
        totals["profit"] += production_kg * 0.01 * (
            msp_per_prod.get(key, 0.0) - cost_per_prod.get(key, 0.0)
        )
    return totals


def build_pool(frame: pd.DataFrame, cols: list[str], by: list[str]) -> dict[object, list[tuple[float, ...]]]:
    pool: dict[object, list[tuple[float, ...]]] = {}
    valid = frame.dropna(subset=cols, how="all").copy()
    grouped = valid.groupby(by, sort=False)
    for key, group in grouped:
        records = [
            tuple(float(value) for value in row)
            for row in group[cols].itertuples(index=False, name=None)
            if not any(pd.isna(value) for value in row)
        ]
        if records:
            pool[key] = records
    return pool


def build_pool_means(pool: dict[object, list[tuple[float, ...]]]) -> dict[object, tuple[float, ...]]:
    means: dict[object, tuple[float, ...]] = {}
    for key, records in pool.items():
        arr = np.asarray(records, dtype=float)
        means[key] = tuple(float(value) for value in arr.mean(axis=0))
    return means


def draw_coefficients(
    rng: np.random.Generator,
    context: SeasonContext,
) -> tuple[
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
]:
    nitrogen_rate = dict(context.nitrogen_rate)
    p_rate = dict(context.p_rate)
    water_rate = dict(context.water_rate)
    for key in context.allowed_triples:
        state, district, crop = key
        sample = None
        sample_mean = None
        for candidate, candidate_mean in (
            (context.exact_pool.get(key), context.exact_pool_mean.get(key)),
            (
                context.state_crop_pool.get((state, crop)),
                context.state_crop_pool_mean.get((state, crop)),
            ),
            (context.crop_pool.get(crop), context.crop_pool_mean.get(crop)),
        ):
            if candidate:
                sample = candidate[int(rng.integers(len(candidate)))]
                sample_mean = candidate_mean
                break
        if sample is None or sample_mean is None:
            continue
        water_draw, net_n_draw, net_p_draw = sample
        mean_water, mean_net_n, mean_net_p = sample_mean
        base_water = float(context.water_rate.get(key, mean_water))
        base_net_n = float(context.nitrogen_rate.get(key, mean_net_n))
        base_net_p = float(context.p_rate.get(key, mean_net_p))
        if math.isfinite(water_draw):
            water_rate[key] = max(0.0, base_water + (float(water_draw) - mean_water))
        if math.isfinite(net_n_draw):
            nitrogen_rate[key] = max(0.0, base_net_n + (float(net_n_draw) - mean_net_n))
        if math.isfinite(net_p_draw):
            p_rate[key] = max(0.0, base_net_p + (float(net_p_draw) - mean_net_p))
    return nitrogen_rate, p_rate, water_rate


def build_context(config: ScenarioConfig, layout) -> SeasonContext:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        namespace = _prepare_namespace(layout, config.notebook)

    df = lower_key_columns(namespace["df"])
    raw_panel = lower_key_columns(namespace[config.season])

    yield_data = float_triplet_map(namespace["yield_data"])
    nitrogen_rate = float_triplet_map(namespace["nitrogen_rate"])
    p_rate = float_triplet_map(namespace["P_rate"])
    water_rate = float_triplet_map(namespace["water_rate"])
    n_removed_rate = float_triplet_map(namespace["nitrogen_removal_rate_perkg"])
    p_removed_rate = float_triplet_map(namespace["P_removal_rate_perkg"])
    calories_per_prod = float_triplet_map(namespace["calories_per_prod"])
    msp_per_prod = float_triplet_map(namespace["MSP_per_prod"])
    cost_per_prod = float_triplet_map(namespace["cost_per_area"])
    aghg_per_ha = float_triplet_map(namespace["AGHG_per_ha"])
    n_leach_rate = float_triplet_map(namespace["nitrogen_leach_rate_perkg"])
    n_emission_rate = float_triplet_map(namespace["nitrogen_emission_rate_perkg"])

    historical_area = float_triplet_map(namespace["historical_cereal_area"])
    current_cereal_area = {
        (canon(state), canon(district), canon(crop)): float(area)
        for (state, district, crop), area in (
            df.groupby(["state", "district", "crop"])["Area (Hectare)"].sum().to_dict().items()
        )
    }
    current_area_sd = {
        (canon(state), canon(district)): float(area)
        for (state, district), area in df.groupby(["state", "district"])["Area (Hectare)"].sum().to_dict().items()
        if float(area) > 0
    }
    states = sorted(df["state"].dropna().astype(str).unique().tolist())
    selected_crops = set(df["crop"].dropna().astype(str).unique().tolist())

    allowed_triples = sorted(
        key
        for key, hist_area in historical_area.items()
        if hist_area > 0 and key[2] in selected_crops and current_area_sd.get((key[0], key[1]), 0.0) > 0
    )

    pair_to_keys: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    state_keys: dict[str, list[tuple[str, str, str]]] = {state: [] for state in states}
    for key in allowed_triples:
        pair_to_keys.setdefault((key[0], key[1]), []).append(key)
        state_keys.setdefault(key[0], []).append(key)

    district_to_state = {
        canon(district): canon(state)
        for state, district in zip(df["state"], df["district"], strict=False)
    }
    profit_keys: dict[str, list[tuple[str, str, str]]] = {}
    for state in states:
        profit_keys[state] = [
            key for key in state_keys.get(state, []) if district_to_state.get(key[1]) == state
        ]

    initial_state_calories = {
        canon(state): float(value)
        for state, value in df.groupby("state")["Total Calorie Supply"].sum().to_dict().items()
    }
    initial_state_profit = {
        canon(state): float(value)
        for state, value in df.groupby("state")["Total initial profit"].sum().to_dict().items()
    }

    raw_panel = raw_panel[raw_panel["crop"].isin(selected_crops)].copy()
    if "CWR m3/ha" not in raw_panel.columns:
        raise KeyError(f"{config.notebook} raw panel is missing CWR m3/ha")
    if "net_N_applied(kg/ha)" not in raw_panel.columns or "net_P_applied(kg/ha)" not in raw_panel.columns:
        raise KeyError(f"{config.notebook} raw panel is missing net application columns")

    coeff_cols = ["CWR m3/ha", "net_N_applied(kg/ha)", "net_P_applied(kg/ha)"]
    exact_pool = build_pool(raw_panel, coeff_cols, ["state", "district", "crop"])
    state_crop_pool = build_pool(raw_panel, coeff_cols, ["state", "crop"])
    crop_pool = build_pool(raw_panel, coeff_cols, ["crop"])
    exact_pool_mean = build_pool_means(exact_pool)
    state_crop_pool_mean = build_pool_means(state_crop_pool)
    crop_pool_mean = build_pool_means(crop_pool)

    deterministic_totals = metric_totals(
        current_cereal_area,
        yield_data,
        nitrogen_rate,
        p_rate,
        water_rate,
        n_removed_rate,
        p_removed_rate,
        calories_per_prod,
        msp_per_prod,
        cost_per_prod,
        aghg_per_ha,
        n_leach_rate,
        n_emission_rate,
    )

    return SeasonContext(
        scenario=config.scenario,
        season=config.season,
        objective=config.objective,
        enforce_profit=config.enforce_profit,
        states=states,
        allowed_triples=allowed_triples,
        current_area_sd=current_area_sd,
        current_cereal_area=current_cereal_area,
        pair_to_keys=pair_to_keys,
        state_keys=state_keys,
        profit_keys=profit_keys,
        district_to_state=district_to_state,
        yield_data=yield_data,
        nitrogen_rate=nitrogen_rate,
        p_rate=p_rate,
        water_rate=water_rate,
        n_removed_rate=n_removed_rate,
        p_removed_rate=p_removed_rate,
        calories_per_prod=calories_per_prod,
        msp_per_prod=msp_per_prod,
        cost_per_prod=cost_per_prod,
        aghg_per_ha=aghg_per_ha,
        n_leach_rate=n_leach_rate,
        n_emission_rate=n_emission_rate,
        initial_state_calories=initial_state_calories,
        initial_state_profit=initial_state_profit,
        raw_panel=raw_panel,
        exact_pool=exact_pool,
        state_crop_pool=state_crop_pool,
        crop_pool=crop_pool,
        exact_pool_mean=exact_pool_mean,
        state_crop_pool_mean=state_crop_pool_mean,
        crop_pool_mean=crop_pool_mean,
        deterministic_totals=deterministic_totals,
    )


def solve_context(
    context: SeasonContext,
    nitrogen_rate: dict[tuple[str, str, str], float],
    p_rate: dict[tuple[str, str, str], float],
    water_rate: dict[tuple[str, str, str], float],
    solver: pulp.LpSolver,
) -> tuple[str, dict[tuple[str, str, str], float]]:
    prob = pulp.LpProblem(
        f"{sanitize(context.scenario)}_{sanitize(context.season)}_{context.objective}",
        pulp.LpMinimize,
    )
    x: dict[tuple[str, str, str], pulp.LpVariable] = {
        key: pulp.LpVariable(
            f"x__{sanitize(key[0])}__{sanitize(key[1])}__{sanitize(key[2])}",
            lowBound=0,
            cat=pulp.LpContinuous,
        )
        for key in context.allowed_triples
    }

    if context.objective == "nitrogen":
        prob += pulp.lpSum(
            x[key]
            * (
                nitrogen_rate.get(key, 0.0)
                - context.yield_data.get(key, 0.0) * context.n_removed_rate.get(key, 0.0)
            )
            for key in context.allowed_triples
        )
    elif context.objective == "water":
        prob += pulp.lpSum(x[key] * water_rate.get(key, 0.0) for key in context.allowed_triples)
    else:
        raise ValueError(f"Unsupported objective {context.objective!r}")

    for pair, keys in context.pair_to_keys.items():
        prob += pulp.lpSum(x[key] for key in keys) == context.current_area_sd[pair]

    for state, keys in context.state_keys.items():
        if not keys:
            continue
        prob += (
            pulp.lpSum(
                x[key] * context.yield_data.get(key, 0.0) * context.calories_per_prod.get(key, 0.0)
                for key in keys
            )
            >= relaxed_rhs(context.initial_state_calories.get(state, 0.0))
        )

    if context.enforce_profit:
        for state, keys in context.profit_keys.items():
            if not keys:
                continue
            prob += (
                pulp.lpSum(
                    x[key]
                    * context.yield_data.get(key, 0.0)
                    * 0.01
                    * (context.msp_per_prod.get(key, 0.0) - context.cost_per_prod.get(key, 0.0))
                    for key in keys
                )
                >= relaxed_rhs(context.initial_state_profit.get(state, 0.0))
            )

    prob.solve(solver)
    status_name = pulp.LpStatus.get(prob.status, str(prob.status))
    x_sol = {key: float(pulp.value(var) or 0.0) for key, var in x.items()}
    return status_name, x_sol


def combine_totals(contexts: list[SeasonContext]) -> dict[str, float]:
    totals = {metric_key: 0.0 for _, metric_key in METRICS}
    for context in contexts:
        for metric_key, value in context.deterministic_totals.items():
            totals[metric_key] += value
    return totals


def deterministic_reproduction(
    contexts: list[SeasonContext],
    solver: pulp.LpSolver,
    centers: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    existing_center_map = {
        (row.scenario, row.metric): float(row.center_pct_reduction)
        for row in centers.itertuples(index=False)
    }
    by_scenario: dict[str, list[SeasonContext]] = {}
    for context in contexts:
        by_scenario.setdefault(context.scenario, []).append(context)

    for scenario, scenario_contexts in by_scenario.items():
        baseline = combine_totals(scenario_contexts)
        aggregated_optimized = {metric_key: 0.0 for _, metric_key in METRICS}
        statuses = []
        for context in scenario_contexts:
            status, area_map = solve_context(
                context,
                context.nitrogen_rate,
                context.p_rate,
                context.water_rate,
                solver,
            )
            statuses.append(f"{context.season}:{status}")
            if status != "Optimal":
                continue
            totals = metric_totals(
                area_map,
                context.yield_data,
                context.nitrogen_rate,
                context.p_rate,
                context.water_rate,
                context.n_removed_rate,
                context.p_removed_rate,
                context.calories_per_prod,
                context.msp_per_prod,
                context.cost_per_prod,
                context.aghg_per_ha,
                context.n_leach_rate,
                context.n_emission_rate,
            )
            for metric_key, value in totals.items():
                aggregated_optimized[metric_key] += value
        for metric_label, metric_key in METRICS:
            baseline_total = baseline[metric_key]
            reproduced = 100.0 * (baseline_total - aggregated_optimized[metric_key]) / baseline_total
            existing = existing_center_map[(scenario, metric_label)]
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric_label,
                    "baseline_total": baseline_total,
                    "reproduced_pct_reduction": reproduced,
                    "existing_center_pct_reduction": existing,
                    "delta_pct_points": reproduced - existing,
                    "solver_status": ";".join(statuses),
                }
            )
    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["metric", "scenario"]).reset_index(drop=True)


def build_summary(
    iterations: pd.DataFrame,
    centers: pd.DataFrame,
) -> pd.DataFrame:
    center_map = {
        (row.scenario, row.metric): (float(row.center_pct_reduction), float(row.center_display_pct))
        for row in centers.itertuples(index=False)
    }
    rows = []
    for (scenario, metric), group in iterations.groupby(["scenario", "metric"], sort=False):
        valid = group[group["status"] == "Optimal"]["pct_reduction"].astype(float)
        center_pct, center_display = center_map[(scenario, metric)]
        if valid.empty:
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "center_pct_reduction": center_pct,
                    "center_display_pct": center_display,
                    "bootstrap_mean_pct_reduction": np.nan,
                    "bootstrap_p2_5_pct_reduction": np.nan,
                    "bootstrap_p97_5_pct_reduction": np.nan,
                    "bootstrap_mean_display_pct": np.nan,
                    "display_interval_low": np.nan,
                    "display_interval_high": np.nan,
                    "lower_err_display": np.nan,
                    "upper_err_display": np.nan,
                    "n_optimal": int(valid.size),
                    "n_total": int(group.shape[0]),
                }
            )
            continue
        p2_5 = float(valid.quantile(0.025))
        p97_5 = float(valid.quantile(0.975))
        display_low = min(-p2_5, -p97_5)
        display_high = max(-p2_5, -p97_5)
        rows.append(
            {
                "scenario": scenario,
                "metric": metric,
                "center_pct_reduction": center_pct,
                "center_display_pct": center_display,
                "bootstrap_mean_pct_reduction": float(valid.mean()),
                "bootstrap_p2_5_pct_reduction": p2_5,
                "bootstrap_p97_5_pct_reduction": p97_5,
                "bootstrap_mean_display_pct": float((-valid).mean()),
                "display_interval_low": display_low,
                "display_interval_high": display_high,
                "lower_err_display": max(center_display - display_low, 0.0),
                "upper_err_display": max(display_high - center_display, 0.0),
                "n_optimal": int(valid.size),
                "n_total": int(group.shape[0]),
            }
        )
    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["metric", "scenario"]).reset_index(drop=True)


def build_figure(summary: pd.DataFrame) -> None:
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
    metric_order = [label for label, _ in METRICS]
    water = summary[summary["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    nitrogen = summary[summary["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]

    positions = np.arange(len(metric_order))
    offset = 0.18
    bar_height = 0.32

    fig, ax = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    ax.barh(
        positions - offset,
        water["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#2a9d8f",
        edgecolor="black",
        linewidth=0.6,
        label="Water based",
        zorder=3,
    )
    ax.barh(
        positions + offset,
        nitrogen["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.6,
        label="Nitrogen based",
        zorder=3,
    )

    ax.errorbar(
        water["center_display_pct"].to_numpy(),
        positions - offset,
        xerr=np.vstack(
            [
                water["lower_err_display"].to_numpy(dtype=float),
                water["upper_err_display"].to_numpy(dtype=float),
            ]
        ),
        fmt="none",
        ecolor="#303030",
        elinewidth=1.1,
        capsize=2.8,
        zorder=4,
    )
    ax.errorbar(
        nitrogen["center_display_pct"].to_numpy(),
        positions + offset,
        xerr=np.vstack(
            [
                nitrogen["lower_err_display"].to_numpy(dtype=float),
                nitrogen["upper_err_display"].to_numpy(dtype=float),
            ]
        ),
        fmt="none",
        ecolor="#303030",
        elinewidth=1.1,
        capsize=2.8,
        zorder=4,
    )

    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("% Change")
    ax.set_title("Percentage Change in Socio-Environmental Objectives", fontweight="bold", pad=8)
    ax.text(-0.12, 1.02, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")
    ax.grid(axis="x", color="#d6d6d6", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=8)

    x_min = min(
        float((water["center_display_pct"] - water["lower_err_display"]).min()),
        float((nitrogen["center_display_pct"] - nitrogen["lower_err_display"]).min()),
    )
    x_max = max(
        float((water["center_display_pct"] + water["upper_err_display"]).max()),
        float((nitrogen["center_display_pct"] + nitrogen["upper_err_display"]).max()),
    )
    ax.set_xlim(min(-50.0, x_min - 4.0), max(30.0, x_max + 4.0))

    fig.savefig(OUT_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_audit(
    summary: pd.DataFrame,
    reproduction: pd.DataFrame,
    iterations: pd.DataFrame,
    n_iterations: int,
    elapsed_seconds: float,
) -> None:
    lines = [
        "# Figure 2(b) whisker rebuild audit",
        "",
        "This rebuild keeps the deterministic bar centers anchored to the existing endpoint CSVs in",
        "`revision_2/_audit/Nitrogen-Surplus-restructuring/generated/`.",
        "",
        "The whiskers are rebuilt from a joint historical bootstrap over the seasonal prepared panels,",
        "sampling three environmental intensity coefficients within crop histories:",
        "",
        "- `CWR m3/ha`",
        "- `net_N_applied(kg/ha)`",
        "- `net_P_applied(kg/ha)`",
        "",
        "The bootstrap is centered on the prepared 2017 coefficients, so each draw perturbs the published",
        "endpoint locally rather than replacing it with the long-run historical mean. The calorie and",
        "farmer-income constraint coefficients remain fixed at the prepared 2017 values, which preserves",
        "the manuscript's optimization structure and avoids turning the panel into a different yield- or",
        "price-uncertainty experiment.",
        "",
        f"Bootstrap iterations requested: {n_iterations}",
        f"Elapsed time (s): {elapsed_seconds:.2f}",
        "",
        "## Deterministic reproduction check",
        "",
    ]
    for row in reproduction.itertuples(index=False):
        lines.append(
            f"- {row.scenario} | {row.metric}: reproduced {row.reproduced_pct_reduction:.3f}%, "
            f"existing {row.existing_center_pct_reduction:.3f}%, delta {row.delta_pct_points:.3f} pp "
            f"({row.solver_status})"
        )
    lines.extend(["", "## Bootstrap feasibility", ""])
    status_counts = (
        iterations[["iteration", "scenario", "status"]]
        .drop_duplicates()
        .groupby(["scenario", "status"])
        .size()
        .reset_index(name="n")
    )
    for row in status_counts.itertuples(index=False):
        lines.append(f"- {row.scenario} | {row.status}: {row.n}")
    lines.extend(["", "## Summary by metric", ""])
    for row in summary.itertuples(index=False):
        lines.append(
            f"- {row.scenario} | {row.metric}: center {row.center_pct_reduction:.3f}%, "
            f"mean {row.bootstrap_mean_pct_reduction:.3f}%, "
            f"95% CI [{row.bootstrap_p2_5_pct_reduction:.3f}, {row.bootstrap_p97_5_pct_reduction:.3f}]%, "
            f"optimal {row.n_optimal}/{row.n_total}"
        )
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n")


def run_bootstrap(contexts: list[SeasonContext], iterations: int, seed: int, solver: pulp.LpSolver) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    baseline_by_scenario: dict[str, dict[str, float]] = {}
    contexts_by_scenario: dict[str, list[SeasonContext]] = {}
    for context in contexts:
        contexts_by_scenario.setdefault(context.scenario, []).append(context)
    for scenario, scenario_contexts in contexts_by_scenario.items():
        baseline_by_scenario[scenario] = combine_totals(scenario_contexts)

    rows: list[dict[str, object]] = []
    for iteration in range(iterations):
        for scenario, scenario_contexts in contexts_by_scenario.items():
            combined = {metric_key: 0.0 for _, metric_key in METRICS}
            season_status: dict[str, str] = {}
            for context in scenario_contexts:
                n_rate_iter, p_rate_iter, water_rate_iter = draw_coefficients(rng, context)
                status, area_map = solve_context(context, n_rate_iter, p_rate_iter, water_rate_iter, solver)
                season_status[context.season] = status
                if status == "Optimal":
                    totals = metric_totals(
                        area_map,
                        context.yield_data,
                        n_rate_iter,
                        p_rate_iter,
                        water_rate_iter,
                        context.n_removed_rate,
                        context.p_removed_rate,
                        context.calories_per_prod,
                        context.msp_per_prod,
                        context.cost_per_prod,
                        context.aghg_per_ha,
                        context.n_leach_rate,
                        context.n_emission_rate,
                    )
                    for metric_key, value in totals.items():
                        combined[metric_key] += value
            scenario_status = "Optimal" if all(v == "Optimal" for v in season_status.values()) else "Infeasible"
            for metric_label, metric_key in METRICS:
                pct_reduction = np.nan
                if scenario_status == "Optimal":
                    baseline = baseline_by_scenario[scenario][metric_key]
                    pct_reduction = 100.0 * (baseline - combined[metric_key]) / baseline
                rows.append(
                    {
                        "iteration": iteration,
                        "scenario": scenario,
                        "season": "annual",
                        "metric": metric_label,
                        "metric_key": metric_key,
                        "status": scenario_status,
                        "kharif_status": season_status.get("kharif", "NA"),
                        "rabi_status": season_status.get("rabi", "NA"),
                        "pct_reduction": pct_reduction,
                        "display_pct_change": -pct_reduction if pd.notna(pct_reduction) else np.nan,
                    }
                )
    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["iteration", "metric", "scenario"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Figure 2(b) whiskers with a traceable bootstrap.")
    parser.add_argument("--iterations", type=int, default=25, help="Number of bootstrap iterations to run.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap draws.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    BOOT_DIR.mkdir(parents=True, exist_ok=True)

    solver = pulp.GLPK_CMD(path=GLPSOL_PATH, msg=False)
    layout = default_layout(AUDIT_ROOT)
    centers = load_existing_centers()

    contexts = [build_context(config, layout) for config in SCENARIOS]
    start = time.time()
    reproduction = deterministic_reproduction(contexts, solver, centers)
    iterations = run_bootstrap(contexts, args.iterations, args.seed, solver)
    summary = build_summary(iterations, centers)
    elapsed = time.time() - start

    reproduction.to_csv(OUT_DETERMINISTIC_CHECK, index=False)
    iterations.to_csv(OUT_ITERATIONS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(summary)
    write_audit(summary, reproduction, iterations, args.iterations, elapsed)


if __name__ == "__main__":
    main()
