from __future__ import annotations

import json
import re
import ast
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pulp
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap

from .config import RepoLayout, default_layout
from .io import ensure_directory, write_csv
from .legacy_notebook_runner import NotebookRunConfig, _rewrite_source, extract_archive_if_needed


SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}

DEFAULT_ALPHAS = [round(i / 100, 2) for i in range(0, 101)]
SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]+")
CALORIE_SCALE = 1e9
INCOME_SCALE = 1e9
RELATIVE_RHS_TOL = 1e-9
ABSOLUTE_RHS_TOL = 1e-6


def _solver(solver_name: str) -> pulp.LpSolver:
    if solver_name == "highs":
        return pulp.HiGHS(msg=False)
    if solver_name == "cbc":
        return pulp.PULP_CBC_CMD(msg=False)
    if solver_name == "glpk":
        return pulp.GLPK_CMD(path="/opt/homebrew/bin/glpsol", msg=False)
    raise ValueError(f"Unsupported solver: {solver_name}")


def _sanitize(text: str) -> str:
    return SANITIZE_RE.sub("_", str(text)).strip("_")


def _relaxed_rhs(value: float) -> float:
    tolerance = max(abs(value) * RELATIVE_RHS_TOL, ABSOLUTE_RHS_TOL)
    return value - tolerance


def _exec_until_model_block(notebook: Path, config: NotebookRunConfig) -> dict[str, object]:
    raw = json.loads(notebook.read_text())
    namespace: dict[str, object] = {"__name__": "__main__"}

    import pandas as pd  # local import to mirror legacy runner behavior

    pd.options.mode.copy_on_write = False
    namespace["pd"] = pd

    stop_marker = "prob = pulp.LpProblem"
    for idx, cell in enumerate(raw.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        rewritten = _rewrite_source(source, config)
        # The Pareto rebuild does not use geopandas; strip the import so the
        # optimization can run in a lighter environment.
        rewritten = rewritten.replace("import geopandas as gpd\n", "")
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
            continue
        if stop_marker in rewritten:
            rewritten = rewritten.split(stop_marker, 1)[0]
            if rewritten.strip():
                exec(compile(rewritten, f"{notebook.name}:cell_{idx}", "exec"), namespace, namespace)
            break
        exec(compile(rewritten, f"{notebook.name}:cell_{idx}", "exec"), namespace, namespace)
    return namespace


def _prepare_namespace(layout: RepoLayout, notebook_name: str) -> dict[str, object]:
    data_dir = extract_archive_if_needed(layout.root).resolve()
    notebook = (layout.root / notebook_name).resolve()
    config = NotebookRunConfig(
        notebook=notebook,
        data_dir=data_dir,
        generated_dir=layout.generated_dir.resolve(),
        use_cbc=False,
    )
    return _exec_until_model_block(notebook, config)


def _float_map(mapping: object, label: str) -> dict[tuple[str, str, str], float]:
    if isinstance(mapping, pd.Series):
        mapping = mapping.to_dict()
    if not isinstance(mapping, dict):
        raise RuntimeError(f"Expected dictionary for {label}, found {type(mapping)!r}")
    out: dict[tuple[str, str, str], float] = {}
    for key, value in mapping.items():
        if not isinstance(key, tuple) or len(key) != 3:
            continue
        try:
            out[(str(key[0]), str(key[1]), str(key[2]))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _float_pair_map(mapping: object, label: str) -> dict[tuple[str, str], float]:
    if isinstance(mapping, pd.Series):
        mapping = mapping.to_dict()
    if not isinstance(mapping, dict):
        raise RuntimeError(f"Expected dictionary for {label}, found {type(mapping)!r}")
    out: dict[tuple[str, str], float] = {}
    for key, value in mapping.items():
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        try:
            out[(str(key[0]), str(key[1]))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def _has_valid_core_coefficients(
    key: tuple[str, str, str],
    *,
    yield_data: dict[tuple[str, str, str], float],
    calories_per_prod: dict[tuple[str, str, str], float],
    nitrogen_rate: dict[tuple[str, str, str], float],
    nitrogen_removal_rate: dict[tuple[str, str, str], float],
    water_rate: dict[tuple[str, str, str], float],
    msp_per_prod: dict[tuple[str, str, str], float],
    cost_per_prod: dict[tuple[str, str, str], float],
) -> bool:
    return (
        yield_data.get(key, 0.0) > 0
        and calories_per_prod.get(key, 0.0) > 0
        and key in nitrogen_rate
        and key in nitrogen_removal_rate
        and key in water_rate
        and key in msp_per_prod
        and key in cost_per_prod
    )


def _state_crop_and_crop_means(
    mapping: dict[tuple[str, str, str], float],
) -> tuple[dict[tuple[str, str], float], dict[str, float]]:
    state_crop_sum: dict[tuple[str, str], float] = {}
    state_crop_count: dict[tuple[str, str], int] = {}
    crop_sum: dict[str, float] = {}
    crop_count: dict[str, int] = {}
    for (state, _district, crop), value in mapping.items():
        if value <= 0:
            continue
        state_crop_key = (state, crop)
        state_crop_sum[state_crop_key] = state_crop_sum.get(state_crop_key, 0.0) + value
        state_crop_count[state_crop_key] = state_crop_count.get(state_crop_key, 0) + 1
        crop_sum[crop] = crop_sum.get(crop, 0.0) + value
        crop_count[crop] = crop_count.get(crop, 0) + 1
    state_crop_means = {
        key: state_crop_sum[key] / state_crop_count[key]
        for key in state_crop_sum
        if state_crop_count[key] > 0
    }
    crop_means = {
        crop: crop_sum[crop] / crop_count[crop]
        for crop in crop_sum
        if crop_count[crop] > 0
    }
    return state_crop_means, crop_means


def _fill_missing_from_hierarchical_means(
    *,
    key: tuple[str, str, str],
    mapping: dict[tuple[str, str, str], float],
    state_crop_means: dict[tuple[str, str], float],
    crop_means: dict[str, float],
) -> bool:
    current_value = mapping.get(key, 0.0)
    if current_value > 0:
        return False
    fallback = state_crop_means.get((key[0], key[2]))
    if fallback is None or fallback <= 0:
        fallback = crop_means.get(key[2])
    if fallback is None or fallback <= 0:
        return False
    mapping[key] = float(fallback)
    return True


def _build_season_context(layout: RepoLayout, season: str, notebook_name: str) -> dict[str, object]:
    namespace = _prepare_namespace(layout, notebook_name)
    df = namespace.get("df")
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError(f"{notebook_name} did not expose a prepared df DataFrame")

    frame = df.copy()
    frame["State"] = frame["State"].astype(str)
    frame["District"] = frame["District"].astype(str)
    frame["Crop"] = frame["Crop"].astype(str)

    state_districts = (
        frame[["State", "District"]]
        .drop_duplicates()
        .sort_values(["State", "District"])
        .itertuples(index=False, name=None)
    )
    state_district_pairs = [(str(state), str(district)) for state, district in state_districts]

    nitrogen_rate = _float_map(namespace.get("nitrogen_rate"), "nitrogen_rate")
    nitrogen_removal_rate = _float_map(namespace.get("nitrogen_removal_rate_perkg"), "nitrogen_removal_rate_perkg")
    water_rate = _float_map(namespace.get("water_rate"), "water_rate")
    yield_data = _float_map(namespace.get("yield_data"), "yield_data")
    calories_per_prod = _float_map(namespace.get("calories_per_prod"), "calories_per_prod")
    cost_per_prod = _float_map(namespace.get("cost_per_area"), "cost_per_area")
    msp_per_prod = _float_map(namespace.get("MSP_per_prod"), "MSP_per_prod")
    current_area = (
        frame.groupby(["State", "District"])["Area (Hectare)"].sum().astype(float).to_dict()
    )
    current_cereal_area = (
        frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()
    )
    cereals = sorted(frame["Crop"].dropna().astype(str).unique().tolist())

    history_raw = namespace.get(season)
    if isinstance(history_raw, pd.DataFrame):
        history = history_raw.copy()
        rename_map = {}
        for source, target in (("state", "State"), ("district", "District"), ("crop", "Crop")):
            if source in history.columns and target not in history.columns:
                rename_map[source] = target
        if rename_map:
            history = history.rename(columns=rename_map)
        required = {"State", "District", "Crop", "Area (Hectare)"}
        if required.issubset(history.columns):
            history["State"] = history["State"].astype(str)
            history["District"] = history["District"].astype(str)
            history["Crop"] = history["Crop"].astype(str)
            history = history[history["Crop"].isin(cereals)].copy()
            historical_cereal_area = (
                history.groupby(["State", "District", "Crop"])["Area (Hectare)"].max().astype(float).to_dict()
            )
            max_area_constraints = dict(historical_cereal_area)
        else:
            historical_cereal_area = _float_map(namespace.get("historical_cereal_area"), "historical_cereal_area")
            max_area_constraints = _float_map(namespace.get("max_area_constraints"), "max_area_constraints")
    else:
        historical_cereal_area = _float_map(namespace.get("historical_cereal_area"), "historical_cereal_area")
        max_area_constraints = _float_map(namespace.get("max_area_constraints"), "max_area_constraints")
    cap_floor_adjustments: list[tuple[tuple[str, str, str], float | None, float]] = []

    for key, area in current_cereal_area.items():
        if area <= 0:
            continue
        existing_cap = max_area_constraints.get(key)
        if existing_cap is None or existing_cap < area:
            cap_floor_adjustments.append((key, existing_cap, area))
            max_area_constraints[key] = area

    states = sorted(frame["State"].dropna().astype(str).unique().tolist())
    districts_by_state = {
        state: sorted(group["District"].dropna().astype(str).unique().tolist())
        for state, group in frame.groupby("State", sort=True)
    }
    yield_state_crop_means, yield_crop_means = _state_crop_and_crop_means(yield_data)
    calorie_state_crop_means, calorie_crop_means = _state_crop_and_crop_means(calories_per_prod)
    nitrogen_state_crop_means, nitrogen_crop_means = _state_crop_and_crop_means(nitrogen_rate)
    nrem_state_crop_means, nrem_crop_means = _state_crop_and_crop_means(nitrogen_removal_rate)
    water_state_crop_means, water_crop_means = _state_crop_and_crop_means(water_rate)
    msp_state_crop_means, msp_crop_means = _state_crop_and_crop_means(msp_per_prod)
    cost_state_crop_means, cost_crop_means = _state_crop_and_crop_means(cost_per_prod)
    crops_by_pair: dict[tuple[str, str], list[str]] = {}
    coefficient_imputed = 0
    coefficient_screen_kept = 0
    coefficient_screen_removed = 0
    for state, district in state_district_pairs:
        valid_crops: list[str] = []
        for crop in cereals:
            key = (state, district, crop)
            if historical_cereal_area.get(key, 0.0) <= 0:
                continue
            if current_area.get((state, district), 0.0) > 0 and not _has_valid_core_coefficients(
                key,
                yield_data=yield_data,
                calories_per_prod=calories_per_prod,
                nitrogen_rate=nitrogen_rate,
                nitrogen_removal_rate=nitrogen_removal_rate,
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
                    mapping=nitrogen_removal_rate,
                    state_crop_means=nrem_state_crop_means,
                    crop_means=nrem_crop_means,
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
                if imputed_any and _has_valid_core_coefficients(
                    key,
                    yield_data=yield_data,
                    calories_per_prod=calories_per_prod,
                    nitrogen_rate=nitrogen_rate,
                    nitrogen_removal_rate=nitrogen_removal_rate,
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
                nitrogen_removal_rate=nitrogen_removal_rate,
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
        pair for pair in state_district_pairs if current_area.get(pair, 0.0) > 0 and crops_by_pair.get(pair)
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
    initial_state_msp = {
        state: sum(
            current_cereal_area.get((state, district, crop), 0.0)
            * yield_data.get((state, district, crop), 0.0)
            * 0.01
            * msp_per_prod.get((state, district, crop), 0.0)
            for district in districts_by_state.get(state, [])
            for crop in crops_by_pair.get((state, district), [])
        )
        for state in states
    }

    baseline_n_surplus = sum(
        current_cereal_area.get((state, district, crop), 0.0)
        * (
            nitrogen_rate.get((state, district, crop), 0.0)
            - yield_data.get((state, district, crop), 0.0) * nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district in pairs_with_area
        for crop in crops_by_pair[(state, district)]
    )
    baseline_water = sum(
        current_cereal_area.get((state, district, crop), 0.0) * water_rate.get((state, district, crop), 0.0)
        for state, district in pairs_with_area
        for crop in crops_by_pair[(state, district)]
    )
    if baseline_n_surplus <= 0 or baseline_water <= 0:
        raise RuntimeError(
            f"{season}: invalid baseline totals for normalized weighted objective "
            f"(N={baseline_n_surplus}, water={baseline_water})"
        )

    return {
        "season": season,
        "frame": frame,
        "states": states,
        "pairs_with_area": pairs_with_area,
        "districts_by_state": districts_by_state,
        "crops_by_pair": crops_by_pair,
        "current_area": current_area,
        "max_area_constraints": max_area_constraints,
        "nitrogen_rate": nitrogen_rate,
        "nitrogen_removal_rate": nitrogen_removal_rate,
        "water_rate": water_rate,
        "yield_data": yield_data,
        "calories_per_prod": calories_per_prod,
        "cost_per_prod": cost_per_prod,
        "msp_per_prod": msp_per_prod,
        "initial_state_calories": initial_state_calories,
        "initial_state_profit": initial_state_profit,
        "initial_state_msp": initial_state_msp,
        "baseline_n_surplus": baseline_n_surplus,
        "baseline_water": baseline_water,
        "cap_floor_adjustments": cap_floor_adjustments,
        "coefficient_imputed": coefficient_imputed,
        "coefficient_screen_kept": coefficient_screen_kept,
        "coefficient_screen_removed": coefficient_screen_removed,
    }


def _build_problem(
    context: dict[str, object],
    alpha: float,
    solver_name: str,
    income_mode: str,
    objective_mode: str,
    use_historical_caps: bool = True,
) -> dict[str, object]:
    pairs_with_area = context["pairs_with_area"]
    crops_by_pair = context["crops_by_pair"]
    current_area = context["current_area"]
    max_area_constraints = context["max_area_constraints"]
    nitrogen_rate = context["nitrogen_rate"]
    nitrogen_removal_rate = context["nitrogen_removal_rate"]
    water_rate = context["water_rate"]
    yield_data = context["yield_data"]
    calories_per_prod = context["calories_per_prod"]
    cost_per_prod = context["cost_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    initial_state_calories = context["initial_state_calories"]
    initial_state_profit = context["initial_state_profit"]
    initial_state_msp = context["initial_state_msp"]
    baseline_n_surplus = float(context["baseline_n_surplus"])
    baseline_water = float(context["baseline_water"])
    districts_by_state = context["districts_by_state"]
    states = context["states"]

    prob = pulp.LpProblem(f"Figure2A_{context['season']}_{alpha:.2f}", pulp.LpMinimize)
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}
    for state, district in pairs_with_area:
        for crop in crops_by_pair[(state, district)]:
            name = f"area__{_sanitize(state)}__{_sanitize(district)}__{_sanitize(crop)}"
            x[(state, district, crop)] = pulp.LpVariable(name, lowBound=0, cat=pulp.LpContinuous)

    objective_n = pulp.lpSum(
        x[(state, district, crop)]
        * (
            nitrogen_rate.get((state, district, crop), 0.0)
            - yield_data.get((state, district, crop), 0.0) * nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district, crop in x
    )
    objective_w = pulp.lpSum(
        x[(state, district, crop)] * water_rate.get((state, district, crop), 0.0)
        for state, district, crop in x
    )
    if objective_mode == "raw":
        prob += alpha * objective_n + (1.0 - alpha) * objective_w
    elif objective_mode == "normalized":
        prob += alpha * (objective_n / baseline_n_surplus) + (1.0 - alpha) * (objective_w / baseline_water)
    else:
        raise ValueError(f"Unsupported objective mode: {objective_mode}")

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

        effective_income_mode = income_mode
        if income_mode == "legacy_mixed":
            effective_income_mode = "profit" if context["season"] == "kharif" else "msp"

        if effective_income_mode == "profit":
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
            target = float(initial_state_profit.get(state, 0.0))
        elif effective_income_mode == "msp":
            income_terms = [
                x[(state, district, crop)]
                * yield_data.get((state, district, crop), 0.0)
                * 0.01
                * msp_per_prod.get((state, district, crop), 0.0)
                for district in valid_districts
                for crop in crops_by_pair.get((state, district), [])
                if (state, district, crop) in x
            ]
            target = float(initial_state_msp.get(state, 0.0))
        else:
            raise ValueError(f"Unsupported income mode: {income_mode}")
        income_target = _relaxed_rhs(target)
        prob += pulp.lpSum(income_terms) / INCOME_SCALE >= income_target / INCOME_SCALE

    solve_status_code = prob.solve(_solver(solver_name))
    solve_status = pulp.LpStatus.get(prob.status, str(prob.status))
    objective_n_value = float(pulp.value(objective_n)) if pulp.value(objective_n) is not None else float("nan")
    objective_w_value = float(pulp.value(objective_w)) if pulp.value(objective_w) is not None else float("nan")
    return {
        "Alpha": round(alpha, 4),
        "objective_nitrogen": objective_n_value,
        "objective_water": objective_w_value,
        "nitrogen_mt": objective_n_value / 1e9,
        "water_bcm": objective_w_value / 1e9,
        "solve_status": solve_status,
        "solve_status_code": solve_status_code,
        "is_valid": solve_status == "Optimal",
        "variable_count": len(x),
        "constraint_count": len(prob.constraints),
        "income_mode": effective_income_mode,
        "objective_mode": objective_mode,
    }


def _baseline_violation_summary(
    context: dict[str, object],
    *,
    use_historical_caps: bool = True,
) -> dict[str, float]:
    pairs_with_area = context["pairs_with_area"]
    crops_by_pair = context["crops_by_pair"]
    current_area = context["current_area"]
    frame = context["frame"]
    current_cereal_area = (
        frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()
    )
    max_area_constraints = context["max_area_constraints"]
    yield_data = context["yield_data"]
    calories_per_prod = context["calories_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    cost_per_prod = context["cost_per_prod"]
    initial_state_calories = context["initial_state_calories"]
    initial_state_profit = context["initial_state_profit"]
    districts_by_state = context["districts_by_state"]
    states = context["states"]

    cap_violation_count = 0
    cap_excess_ha = 0.0
    for state, district in pairs_with_area:
        lhs_area = sum(current_cereal_area.get((state, district, crop), 0.0) for crop in crops_by_pair[(state, district)])
        if abs(lhs_area - current_area.get((state, district), 0.0)) > 1e-6:
            raise RuntimeError(
                f"Baseline area accounting mismatch in {state}/{district}: "
                f"{lhs_area} vs {current_area.get((state, district), 0.0)}"
            )
        if not use_historical_caps:
            continue
        for crop in crops_by_pair[(state, district)]:
            area = current_cereal_area.get((state, district, crop), 0.0)
            cap = max_area_constraints.get((state, district, crop))
            if cap is not None and area > cap + 1e-6:
                cap_violation_count += 1
                cap_excess_ha += area - cap

    worst_calorie_gap = 0.0
    worst_income_gap = 0.0
    calorie_gap_sum = 0.0
    income_gap_sum = 0.0
    for state in states:
        calorie_lhs = sum(
            current_cereal_area.get((state, district, crop), 0.0)
            * yield_data.get((state, district, crop), 0.0)
            * calories_per_prod.get((state, district, crop), 0.0)
            for district in districts_by_state.get(state, [])
            for crop in crops_by_pair.get((state, district), [])
        )
        calorie_gap = calorie_lhs - float(initial_state_calories.get(state, 0.0))
        worst_calorie_gap = min(worst_calorie_gap, calorie_gap)
        if calorie_gap < 0:
            calorie_gap_sum += calorie_gap

        income_lhs = sum(
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
        income_gap = income_lhs - float(initial_state_profit.get(state, 0.0))
        worst_income_gap = min(worst_income_gap, income_gap)
        if income_gap < 0:
            income_gap_sum += income_gap

    return {
        "cap_violation_count": float(cap_violation_count),
        "cap_excess_ha": float(cap_excess_ha),
        "worst_calorie_gap": float(worst_calorie_gap),
        "worst_income_gap": float(worst_income_gap),
        "calorie_gap_sum": float(calorie_gap_sum),
        "income_gap_sum": float(income_gap_sum),
    }


def build_figure2a_clean_rebuild(
    layout: RepoLayout | None = None,
    alphas: list[float] | None = None,
    solver_name: str = "highs",
    income_mode: str = "profit",
    objective_mode: str = "raw",
    use_historical_caps: bool = True,
) -> dict[str, pd.DataFrame]:
    active_layout = layout or default_layout()
    active_alphas = [round(float(alpha), 4) for alpha in (alphas or DEFAULT_ALPHAS)]

    contexts = {
        season: _build_season_context(active_layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    baseline_summaries = {
        season: _baseline_violation_summary(context, use_historical_caps=use_historical_caps)
        for season, context in contexts.items()
    }
    for season, summary in baseline_summaries.items():
        if use_historical_caps and summary["cap_violation_count"] > 0:
            raise RuntimeError(f"{season}: baseline still violates crop-area caps after repair.")
        if summary["worst_calorie_gap"] < -1e-3:
            raise RuntimeError(f"{season}: baseline still violates calorie target after repair.")
        if summary["worst_income_gap"] < -1e-3:
            raise RuntimeError(f"{season}: baseline still violates income target after repair.")

    season_tables: dict[str, pd.DataFrame] = {}
    for season, context in contexts.items():
        rows = [
            _build_problem(
                context,
                alpha,
                solver_name=solver_name,
                income_mode=income_mode,
                objective_mode=objective_mode,
                use_historical_caps=use_historical_caps,
            )
            for alpha in active_alphas
        ]
        season_tables[season] = pd.DataFrame(rows).sort_values("Alpha").reset_index(drop=True)
        season_tables[season].attrs["cap_floor_adjustments"] = len(context["cap_floor_adjustments"])
        season_tables[season].attrs["baseline_summary"] = baseline_summaries[season]
        season_tables[season].attrs["use_historical_caps"] = use_historical_caps

    combined = (
        season_tables["kharif"]
        .merge(season_tables["rabi"], on="Alpha", suffixes=("_kharif", "_rabi"), how="inner")
        .sort_values("Alpha")
        .reset_index(drop=True)
    )
    combined["objective_nitrogen"] = combined["objective_nitrogen_kharif"] + combined["objective_nitrogen_rabi"]
    combined["objective_water"] = combined["objective_water_kharif"] + combined["objective_water_rabi"]
    combined["nitrogen_mt"] = combined["objective_nitrogen"] / 1e9
    combined["water_bcm"] = combined["objective_water"] / 1e9
    combined["is_valid"] = combined["is_valid_kharif"] & combined["is_valid_rabi"]
    combined["solve_status"] = combined["solve_status_kharif"] + "|" + combined["solve_status_rabi"]
    combined["income_mode"] = income_mode
    combined["objective_mode"] = objective_mode
    baseline_n_surplus = sum(float(context["baseline_n_surplus"]) for context in contexts.values())
    baseline_water = sum(float(context["baseline_water"]) for context in contexts.values())
    combined["nitrogen_pct_of_2017_baseline"] = 100.0 * combined["objective_nitrogen"] / baseline_n_surplus
    combined["water_pct_of_2017_baseline"] = 100.0 * combined["objective_water"] / baseline_water
    combined.attrs["baseline_n_surplus"] = baseline_n_surplus
    combined.attrs["baseline_water"] = baseline_water
    combined.attrs["baseline_n_tg"] = baseline_n_surplus / 1e9
    combined.attrs["baseline_w_bcm"] = baseline_water / 1e9
    combined.attrs["use_historical_caps"] = use_historical_caps
    return {"kharif": season_tables["kharif"], "rabi": season_tables["rabi"], "combined": combined}


def _plot_combined(
    frame: pd.DataFrame,
    target_dir: Path,
    *,
    x_column: str,
    y_column: str,
    x_label: str,
    y_label: str,
    stem: str,
) -> dict[str, Path]:
    valid = frame[frame["is_valid"]].copy()
    invalid = frame[~frame["is_valid"]].copy()

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 11.5,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )
    fig, ax = plt.subplots(figsize=(8.9, 5.2))
    cmap = LinearSegmentedColormap.from_list(
        "water_to_nitrogen",
        ["#5b2a86", "#4c78a8", "#d89216"],
    )
    norm = plt.Normalize(vmin=0.0, vmax=1.0)
    if not invalid.empty:
        ax.scatter(
            invalid[x_column],
            invalid[y_column],
            color="#b8b8b8",
            marker="x",
            s=52,
            linewidths=1.2,
            label="Excluded (non-optimal)",
            zorder=2,
        )
    for row in valid.itertuples(index=False):
        color = cmap(norm(float(row.Alpha)))
        alpha_value = float(row.Alpha)
        if alpha_value in {0.0, 1.0}:
            continue
        ax.scatter(
            getattr(row, x_column),
            getattr(row, y_column),
            color=color,
            edgecolors="white",
            linewidths=0.55,
            s=70,
            zorder=3,
        )
    if not valid.empty:
        water_focused = valid.loc[valid["Alpha"].idxmin()]
        nitrogen_focused = valid.loc[valid["Alpha"].idxmax()]
        ax.scatter(
            water_focused[x_column],
            water_focused[y_column],
            color="#5b2a86",
            edgecolors="black",
            linewidth=0.8,
            marker="*",
            s=340,
            zorder=5,
        )
        ax.scatter(
            nitrogen_focused[x_column],
            nitrogen_focused[y_column],
            color="#d89216",
            edgecolors="black",
            linewidth=0.8,
            marker="*",
            s=340,
            zorder=5,
        )
    ax.set_title("Pareto Front: Nitrogen Surplus vs. Consumptive Water Demand", fontweight="bold", pad=10)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.margins(x=0.05, y=0.08)
    ax.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="*",
            color="w",
            markerfacecolor="#5b2a86",
            markeredgecolor="black",
            markersize=12,
            label="Water-based",
        ),
        Line2D(
            [0],
            [0],
            marker="*",
            color="w",
            markerfacecolor="#d89216",
            markeredgecolor="black",
            markersize=12,
            label="Nitrogen-based",
        ),
    ]
    if not invalid.empty:
        legend_handles.append(
            Line2D(
                [0],
                [0],
                marker="x",
                color="#b8b8b8",
                linestyle="None",
                markersize=8,
                label="Excluded (non-optimal)",
            )
        )
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#d0d0d0",
        framealpha=0.96,
        fontsize=9.6,
    )

    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
    cbar.set_label("Nitrogen weight (α)", fontsize=10.5)
    cbar.set_ticks([0.0, 0.5, 1.0])
    cbar.ax.tick_params(labelsize=9.5)

    png_path = target_dir / f"{stem}.png"
    pdf_path = target_dir / f"{stem}.pdf"
    fig.tight_layout()
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    return {"plot_png": png_path, "plot_pdf": pdf_path}


def _write_summary(
    frames: dict[str, pd.DataFrame],
    target_dir: Path,
    solver_name: str,
    income_mode: str,
    objective_mode: str,
) -> Path:
    combined = frames["combined"]
    kharif = frames["kharif"]
    rabi = frames["rabi"]
    kharif_adjustments = int(kharif.attrs.get("cap_floor_adjustments", 0))
    rabi_adjustments = int(rabi.attrs.get("cap_floor_adjustments", 0))
    kharif_baseline = kharif.attrs.get("baseline_summary", {})
    rabi_baseline = rabi.attrs.get("baseline_summary", {})
    use_historical_caps = bool(combined.attrs.get("use_historical_caps", True))
    objective_line = (
        "- uses the paper weighted sum in raw objective units."
        if objective_mode == "raw"
        else "- normalizes the weighted objective by baseline nitrogen surplus and baseline water demand."
    )
    baseline_n_tg = float(combined.attrs.get("baseline_n_tg", float("nan")))
    baseline_w_bcm = float(combined.attrs.get("baseline_w_bcm", float("nan")))
    lines = [
        "# Figure 2(a) clean rebuild",
        "",
        "This rebuild uses the single-objective notebook data preparation but replaces the",
        "legacy multi-objective notebook formulation with a clean model that:",
        "- indexes districts jointly by `(state, district)` to avoid duplicate-name collisions,",
        (
            "- applies max-area caps using `(state, district, crop)` keys,"
            if use_historical_caps
            else "- restricts reallocation to crops already observed in each district, without imposing"
            " crop-specific historical area ceilings,"
        ),
        objective_line,
        "- records solver status explicitly and excludes non-optimal alpha points,",
        "- combines seasons by summing national totals, consistent with the paper methods summary.",
        "",
        f"Solver: `{solver_name}`",
        f"Income constraint: `{income_mode}`",
        f"Objective mode: `{objective_mode}`",
        f"Alpha count: {len(combined)}",
        f"Valid combined alphas: {int(combined['is_valid'].sum())}/{len(combined)}",
        f"Combined 2017 baseline nitrogen surplus: {baseline_n_tg:.6f} Tg N",
        f"Combined 2017 baseline water demand: {baseline_w_bcm:.6f} BCM",
        (
            f"Baseline cap repairs: kharif={kharif_adjustments}, rabi={rabi_adjustments}"
            if use_historical_caps
            else "Baseline cap repairs: not used in this approved branch"
        ),
        "Baseline feasibility after repair:",
        (
            f"- kharif worst calorie gap={kharif_baseline.get('worst_calorie_gap', float('nan')):.6g}, "
            f"worst income gap={kharif_baseline.get('worst_income_gap', float('nan')):.6g}, "
            f"cap violations={int(kharif_baseline.get('cap_violation_count', 0))}"
        ),
        (
            f"- rabi worst calorie gap={rabi_baseline.get('worst_calorie_gap', float('nan')):.6g}, "
            f"worst income gap={rabi_baseline.get('worst_income_gap', float('nan')):.6g}, "
            f"cap violations={int(rabi_baseline.get('cap_violation_count', 0))}"
        ),
        "",
        "Season status counts:",
        "Kharif:",
    ]
    for status, count in kharif["solve_status"].value_counts(dropna=False).items():
        lines.append(f"- `{status}`: {count}")
    lines.append("Rabi:")
    for status, count in rabi["solve_status"].value_counts(dropna=False).items():
        lines.append(f"- `{status}`: {count}")
    if combined["is_valid"].any():
        valid = combined[combined["is_valid"]]
        unique_points = valid[["objective_nitrogen", "objective_water"]].drop_duplicates().shape[0]
        lines.extend(
            [
                "",
                "Combined frontier range:",
                f"- nitrogen surplus: {valid['nitrogen_mt'].min():.3f} to {valid['nitrogen_mt'].max():.3f} Tg N",
                f"- water demand: {valid['water_bcm'].min():.3f} to {valid['water_bcm'].max():.3f} BCM",
                (
                    "- nitrogen surplus: "
                    f"{valid['nitrogen_pct_of_2017_baseline'].min():.3f} to "
                    f"{valid['nitrogen_pct_of_2017_baseline'].max():.3f}% of the 2017 baseline"
                ),
                (
                    "- water demand: "
                    f"{valid['water_pct_of_2017_baseline'].min():.3f} to "
                    f"{valid['water_pct_of_2017_baseline'].max():.3f}% of the 2017 baseline"
                ),
                f"- unique Pareto points: {unique_points}/{len(valid)} alpha values",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "No scientifically admissible combined frontier was obtained under the clean rebuild.",
            ]
        )
    summary_path = target_dir / "figure2a_clean_rebuild_summary.md"
    summary_path.write_text("\n".join(lines) + "\n")
    return summary_path


def export_figure2a_clean_rebuild(
    output_dir: Path | None = None,
    layout: RepoLayout | None = None,
    alphas: list[float] | None = None,
    solver_name: str = "highs",
    income_mode: str = "profit",
    objective_mode: str = "raw",
    use_historical_caps: bool = True,
) -> dict[str, Path]:
    active_layout = layout or default_layout()
    target_dir = ensure_directory(output_dir or (active_layout.outputs_dir / "generated" / "figure2a_clean_rebuild"))
    frames = build_figure2a_clean_rebuild(
        layout=active_layout,
        alphas=alphas,
        solver_name=solver_name,
        income_mode=income_mode,
        objective_mode=objective_mode,
        use_historical_caps=use_historical_caps,
    )
    written = {
        "kharif_csv": write_csv(frames["kharif"], target_dir / "kharif_by_alpha.csv"),
        "rabi_csv": write_csv(frames["rabi"], target_dir / "rabi_by_alpha.csv"),
        "combined_csv": write_csv(frames["combined"], target_dir / "combined_by_alpha.csv"),
        "summary_md": _write_summary(
            frames,
            target_dir,
            solver_name=solver_name,
            income_mode=income_mode,
            objective_mode=objective_mode,
        ),
    }
    written.update(
        _plot_combined(
            frames["combined"],
            target_dir,
            x_column="nitrogen_mt",
            y_column="water_bcm",
            x_label="Nitrogen surplus (Tg N)",
            y_label="Consumptive water demand (BCM)",
            stem="figure2a_clean_rebuild",
        )
    )
    written.update(
        _plot_combined(
            frames["combined"],
            target_dir,
            x_column="nitrogen_pct_of_2017_baseline",
            y_column="water_pct_of_2017_baseline",
            x_label="Nitrogen surplus (% of 2017 baseline)",
            y_label="Consumptive water demand (% of 2017 baseline)",
            stem="figure2a_clean_rebuild_pct_2017_baseline",
        )
    )
    return written
