#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "figure2_main_frontier_bootstrap"
CENTERS_CSV = DATA_DIR / "figure2_main" / "figure2_main_panel_a_combined_by_alpha.csv"
OUT_ITERATIONS = OUT_DIR / "figure2_main_frontier_bootstrap_iterations.csv"
OUT_SUMMARY = OUT_DIR / "figure2_main_frontier_bootstrap_summary.csv"
OUT_AUDIT = OUT_DIR / "figure2_main_frontier_bootstrap_audit.md"
OUT_COVERAGE = OUT_DIR / "figure2_main_frontier_bootstrap_price_coverage.csv"
OUT_PNG = FIG_DIR / "si_figure2a_frontier_bootstrap.png"
OUT_PDF = FIG_DIR / "si_figure2a_frontier_bootstrap.pdf"
PRIMARY_SCENARIO_YEAR = "2017-18"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from bootstrap_figure2b_no_historical_cap_core import canon, load_sampling_pools  # noqa: E402
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    CALORIE_SCALE,
    INCOME_SCALE,
    SEASON_NOTEBOOKS,
    _build_problem,
    _build_season_context,
    _relaxed_rhs,
    _sanitize,
    _solver,
)
import generate_figure2_main as figure2eq  # noqa: E402
from generate_si_revenue_profit_sensitivity import (  # noqa: E402
    load_national_price_lookup,
    load_ratio_scenarios,
    load_state_price_lookup,
    load_unusable_direct_price_keys,
)


def build_contexts(layout) -> tuple[dict[str, dict[str, object]], pd.DataFrame]:
    contexts: dict[str, dict[str, object]] = {}
    coverage_rows: list[dict[str, object]] = []
    crop_ratios = load_ratio_scenarios()[PRIMARY_SCENARIO_YEAR]
    state_price_lookup = load_state_price_lookup()
    national_price_lookup = load_national_price_lookup()
    unusable_direct_keys = load_unusable_direct_price_keys()
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            base_context = _build_season_context(layout, season, notebook_name)
        contexts[season], coverage = figure2eq._apply_hybrid_price_to_dict_context(
            base_context,
            scenario_year=PRIMARY_SCENARIO_YEAR,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
            panel_key="s20_frontier_bootstrap",
        )
        coverage_rows.append(coverage)
    return contexts, pd.DataFrame(coverage_rows)


def iter_allowed_triples(context: dict[str, object]) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    for state, district in context["pairs_with_area"]:
        for crop in context["crops_by_pair"][(state, district)]:
            triples.append((state, district, crop))
    return triples


def draw_frontier_coefficients(
    rng: np.random.Generator,
    context: dict[str, object],
    pools: dict[str, object],
) -> tuple[dict[tuple[str, str, str], float], dict[tuple[str, str, str], float]]:
    nitrogen_rate = dict(context["nitrogen_rate"])
    water_rate = dict(context["water_rate"])

    def signed_residual(draw: float, mean_draw: float) -> float:
        if not math.isfinite(draw) or not math.isfinite(mean_draw):
            return 0.0
        residual = float(draw) - float(mean_draw)
        return residual if rng.random() < 0.5 else -residual

    for key in iter_allowed_triples(context):
        ckey = (canon(key[0]), canon(key[1]), canon(key[2]))
        sample = None
        sample_mean = None
        for candidate, candidate_mean in (
            (pools["exact_pool"].get(ckey), pools["exact_pool_mean"].get(ckey)),
            (
                pools["state_crop_pool"].get((canon(key[0]), canon(key[2]))),
                pools["state_crop_pool_mean"].get((canon(key[0]), canon(key[2]))),
            ),
            (pools["crop_pool"].get(canon(key[2])), pools["crop_pool_mean"].get(canon(key[2]))),
        ):
            if candidate:
                sample = candidate[int(rng.integers(len(candidate)))]
                sample_mean = candidate_mean
                break

        if sample is None or sample_mean is None:
            continue

        water_draw, net_n_draw, _net_p_draw = sample
        mean_water, mean_net_n, _mean_net_p = sample_mean

        base_water = float(water_rate.get(key, mean_water))
        base_net_n = float(nitrogen_rate.get(key, mean_net_n))

        water_rate[key] = max(0.0, base_water + signed_residual(float(water_draw), float(mean_water)))
        nitrogen_rate[key] = max(0.0, base_net_n + signed_residual(float(net_n_draw), float(mean_net_n)))

    return nitrogen_rate, water_rate


def run_bootstrap(
    contexts: dict[str, dict[str, object]],
    pools: dict[str, dict[str, object]],
    alphas: list[float],
    iterations: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    for iteration in range(iterations):
        season_contexts: dict[str, dict[str, object]] = {}
        for season, context in contexts.items():
            nitrogen_rate_iter, water_rate_iter = draw_frontier_coefficients(rng, context, pools[season])
            iter_context = dict(context)
            iter_context["nitrogen_rate"] = nitrogen_rate_iter
            iter_context["water_rate"] = water_rate_iter
            season_contexts[season] = iter_context

        for alpha in alphas:
            combined_n = 0.0
            combined_w = 0.0
            statuses: dict[str, str] = {}
            valid = True

            for season in ("kharif", "rabi"):
                result = _build_problem(
                    season_contexts[season],
                    alpha,
                    solver_name="highs",
                    income_mode="profit",
                    objective_mode="normalized",
                    use_historical_caps=False,
                )
                statuses[season] = str(result["solve_status"])
                if result["solve_status"] != "Optimal":
                    valid = False
                    continue
                combined_n += float(result["objective_nitrogen"])
                combined_w += float(result["objective_water"])

            rows.append(
                {
                    "iteration": iteration,
                    "Alpha": float(alpha),
                    "nitrogen_mt": combined_n / 1e9 if valid else np.nan,
                    "water_bcm": combined_w / 1e9 if valid else np.nan,
                    "status": "Optimal" if valid else "Infeasible",
                    "kharif_status": statuses.get("kharif", "NA"),
                    "rabi_status": statuses.get("rabi", "NA"),
                }
            )

    return pd.DataFrame(rows).sort_values(["iteration", "Alpha"]).reset_index(drop=True)


def solve_area_map(
    context: dict[str, object],
    alpha: float,
    solver_name: str = "highs",
    income_mode: str = "profit",
    objective_mode: str = "normalized",
    use_historical_caps: bool = False,
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

    prob = pulp.LpProblem(f"S20_fixed_allocation_{context['season']}_{alpha:.2f}", pulp.LpMinimize)
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
    area_map = {
        key: float(variable.varValue or 0.0)
        for key, variable in x.items()
    }
    return {
        "Alpha": round(alpha, 4),
        "objective_nitrogen": objective_n_value,
        "objective_water": objective_w_value,
        "nitrogen_mt": objective_n_value / 1e9,
        "water_bcm": objective_w_value / 1e9,
        "solve_status": solve_status,
        "solve_status_code": solve_status_code,
        "is_valid": solve_status == "Optimal",
        "area_map": area_map,
    }


def build_deterministic_allocations(
    contexts: dict[str, dict[str, object]],
    alphas: list[float],
) -> dict[tuple[str, float], dict[str, object]]:
    allocations: dict[tuple[str, float], dict[str, object]] = {}
    for season in ("kharif", "rabi"):
        for alpha in alphas:
            result = solve_area_map(
                contexts[season],
                alpha,
                solver_name="highs",
                income_mode="profit",
                objective_mode="normalized",
                use_historical_caps=False,
            )
            if result["solve_status"] != "Optimal":
                raise RuntimeError(f"Deterministic solve failed for {season} alpha={alpha}: {result['solve_status']}")
            allocations[(season, float(alpha))] = result
    return allocations


def evaluate_area_map(
    context: dict[str, object],
    area_map: dict[tuple[str, str, str], float],
    nitrogen_rate: dict[tuple[str, str, str], float],
    water_rate: dict[tuple[str, str, str], float],
) -> tuple[float, float]:
    yield_data = context["yield_data"]
    nitrogen_removal_rate = context["nitrogen_removal_rate"]
    total_n = 0.0
    total_w = 0.0
    for key, area in area_map.items():
        if not math.isfinite(area) or area == 0:
            continue
        total_n += area * (
            nitrogen_rate.get(key, 0.0)
            - yield_data.get(key, 0.0) * nitrogen_removal_rate.get(key, 0.0)
        )
        total_w += area * water_rate.get(key, 0.0)
    return total_n, total_w


def run_fixed_allocation_bootstrap(
    contexts: dict[str, dict[str, object]],
    pools: dict[str, dict[str, object]],
    allocations: dict[tuple[str, float], dict[str, object]],
    alphas: list[float],
    iterations: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    for iteration in range(iterations):
        drawn_by_season: dict[str, tuple[dict[tuple[str, str, str], float], dict[tuple[str, str, str], float]]] = {}
        for season, context in contexts.items():
            drawn_by_season[season] = draw_frontier_coefficients(rng, context, pools[season])

        for alpha in alphas:
            combined_n = 0.0
            combined_w = 0.0
            for season in ("kharif", "rabi"):
                nitrogen_rate_iter, water_rate_iter = drawn_by_season[season]
                season_n, season_w = evaluate_area_map(
                    contexts[season],
                    allocations[(season, float(alpha))]["area_map"],
                    nitrogen_rate_iter,
                    water_rate_iter,
                )
                combined_n += season_n
                combined_w += season_w

            rows.append(
                {
                    "iteration": iteration,
                    "Alpha": float(alpha),
                    "nitrogen_mt": combined_n / 1e9,
                    "water_bcm": combined_w / 1e9,
                    "status": "Evaluated",
                    "kharif_status": "FixedAllocation",
                    "rabi_status": "FixedAllocation",
                }
            )

    return pd.DataFrame(rows).sort_values(["iteration", "Alpha"]).reset_index(drop=True)


def build_summary(iterations: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
    center_map = centers.set_index("Alpha")[["nitrogen_mt", "water_bcm"]]
    rows: list[dict[str, object]] = []

    for alpha, group in iterations.groupby("Alpha", sort=True):
        valid = group[group["status"].isin(["Optimal", "Evaluated"])]
        nitrogen = valid["nitrogen_mt"].astype(float)
        water = valid["water_bcm"].astype(float)
        center_nitrogen = float(center_map.loc[alpha, "nitrogen_mt"])
        center_water = float(center_map.loc[alpha, "water_bcm"])
        min_nitrogen = float(nitrogen.min()) if not nitrogen.empty else np.nan
        max_nitrogen = float(nitrogen.max()) if not nitrogen.empty else np.nan
        min_water = float(water.min()) if not water.empty else np.nan
        max_water = float(water.max()) if not water.empty else np.nan
        rows.append(
            {
                "Alpha": float(alpha),
                "center_nitrogen_mt": center_nitrogen,
                "center_water_bcm": center_water,
                "mean_nitrogen_mt": float(nitrogen.mean()) if not nitrogen.empty else np.nan,
                "p2_5_nitrogen_mt": float(nitrogen.quantile(0.025)) if not nitrogen.empty else np.nan,
                "p97_5_nitrogen_mt": float(nitrogen.quantile(0.975)) if not nitrogen.empty else np.nan,
                "min_nitrogen_mt": min_nitrogen,
                "max_nitrogen_mt": max_nitrogen,
                "envelope_low_nitrogen_mt": float(min(center_nitrogen, min_nitrogen)) if not np.isnan(min_nitrogen) else center_nitrogen,
                "envelope_high_nitrogen_mt": float(max(center_nitrogen, max_nitrogen)) if not np.isnan(max_nitrogen) else center_nitrogen,
                "mean_water_bcm": float(water.mean()) if not water.empty else np.nan,
                "p2_5_water_bcm": float(water.quantile(0.025)) if not water.empty else np.nan,
                "p97_5_water_bcm": float(water.quantile(0.975)) if not water.empty else np.nan,
                "min_water_bcm": min_water,
                "max_water_bcm": max_water,
                "envelope_low_water_bcm": float(min(center_water, min_water)) if not np.isnan(min_water) else center_water,
                "envelope_high_water_bcm": float(max(center_water, max_water)) if not np.isnan(max_water) else center_water,
                "n_optimal": int(valid.shape[0]),
                "n_total": int(group.shape[0]),
            }
        )

    return pd.DataFrame(rows).sort_values("Alpha").reset_index(drop=True)


def build_figure(centers: pd.DataFrame, iterations: pd.DataFrame, summary: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )

    fig = plt.figure(figsize=(12.6, 4.2), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=[1.4, 1.0, 1.0], wspace=0.32)
    ax_frontier = fig.add_subplot(grid[0, 0])
    ax_n = fig.add_subplot(grid[0, 1])
    ax_w = fig.add_subplot(grid[0, 2])

    for _iteration, group in iterations.groupby("iteration", sort=True):
        valid = group[group["status"].isin(["Optimal", "Evaluated"])].sort_values("Alpha")
        if valid.shape[0] < 2:
            continue
        ax_frontier.plot(
            valid["nitrogen_mt"],
            valid["water_bcm"],
            color="#b7c2cc",
            linewidth=0.75,
            alpha=0.22,
            zorder=1,
        )

    ax_frontier.plot(
        centers["nitrogen_mt"],
        centers["water_bcm"],
        color="#253243",
        linewidth=2.0,
        zorder=3,
        label="Deterministic frontier",
    )
    ax_frontier.scatter(
        centers["nitrogen_mt"],
        centers["water_bcm"],
        color="#253243",
        s=10,
        zorder=4,
    )

    water_endpoint = centers.loc[centers["Alpha"] == centers["Alpha"].min()].iloc[0]
    nitrogen_endpoint = centers.loc[centers["Alpha"] == centers["Alpha"].max()].iloc[0]
    ax_frontier.scatter(
        [water_endpoint["nitrogen_mt"]],
        [water_endpoint["water_bcm"]],
        marker="*",
        s=130,
        color="#5b2a86",
        edgecolor="#253243",
        linewidth=0.8,
        zorder=5,
        label="Water-based endpoint",
    )
    ax_frontier.scatter(
        [nitrogen_endpoint["nitrogen_mt"]],
        [nitrogen_endpoint["water_bcm"]],
        marker="*",
        s=130,
        color="#d89216",
        edgecolor="#253243",
        linewidth=0.8,
        zorder=5,
        label="Nitrogen-based endpoint",
    )

    ax_frontier.set_xlabel("Nitrogen surplus (Tg N)")
    ax_frontier.set_ylabel("Consumptive water demand (BCM)")
    ax_frontier.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.85)
    ax_frontier.spines["top"].set_visible(False)
    ax_frontier.spines["right"].set_visible(False)
    ax_frontier.text(-0.12, 1.03, "a", transform=ax_frontier.transAxes, fontsize=12, fontweight="bold")
    ax_frontier.legend(
        handles=[
            plt.Line2D([0], [0], color="#b7c2cc", lw=1.0, label="Fixed-allocation bootstrap"),
            plt.Line2D([0], [0], color="#253243", lw=2.0, label="Deterministic frontier"),
            plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#5b2a86", markeredgecolor="#253243", markersize=10, label="Water-based endpoint"),
            plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#d89216", markeredgecolor="#253243", markersize=10, label="Nitrogen-based endpoint"),
        ],
        loc="upper right",
        fontsize=8,
        frameon=True,
        framealpha=0.92,
    )

    alpha = summary["Alpha"].to_numpy()

    ax_n.fill_between(
        alpha,
        summary["envelope_low_nitrogen_mt"],
        summary["envelope_high_nitrogen_mt"],
        color="#efc27a",
        alpha=0.45,
        linewidth=0,
        zorder=1,
    )
    ax_n.plot(alpha, centers["nitrogen_mt"], color="#d89216", linewidth=2.0, zorder=3)
    ax_n.set_xlabel("Nitrogen weight ($\\alpha$)")
    ax_n.set_ylabel("Nitrogen surplus (Tg N)")
    ax_n.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.85)
    ax_n.spines["top"].set_visible(False)
    ax_n.spines["right"].set_visible(False)
    ax_n.text(-0.16, 1.03, "b", transform=ax_n.transAxes, fontsize=12, fontweight="bold")

    ax_w.fill_between(
        alpha,
        summary["envelope_low_water_bcm"],
        summary["envelope_high_water_bcm"],
        color="#9ecae1",
        alpha=0.5,
        linewidth=0,
        zorder=1,
    )
    ax_w.plot(alpha, centers["water_bcm"], color="#2b7bba", linewidth=2.0, zorder=3)
    ax_w.set_xlabel("Nitrogen weight ($\\alpha$)")
    ax_w.set_ylabel("Consumptive water demand (BCM)")
    ax_w.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.85)
    ax_w.spines["top"].set_visible(False)
    ax_w.spines["right"].set_visible(False)
    ax_w.text(-0.16, 1.03, "c", transform=ax_w.transAxes, fontsize=12, fontweight="bold")

    fig.savefig(OUT_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_audit(
    summary: pd.DataFrame,
    iterations: pd.DataFrame,
    coverage: pd.DataFrame,
    *,
    n_iterations: int,
    seed: int,
    elapsed_seconds: float,
) -> None:
    status_counts = (
        iterations.groupby("status")
        .size()
        .reset_index(name="n")
        .sort_values("status")
    )
    lines = [
        "# Figure 2(a) frontier bootstrap audit",
        "",
        "This SI-only robustness figure propagates local coefficient uncertainty through",
        "the deterministic optimized allocations that define the primary Figure 2(a) alpha frontier",
        f"under the primary {PRIMARY_SCENARIO_YEAR} revenue benchmark, fixed district cropped area,",
        "and substitution among historically observed cereals.",
        "",
        "For each bootstrap iteration, district crop-specific water demand and net nitrogen application rates",
        "are perturbed around the prepared 2017 coefficient fields using sign-symmetric residual draws",
        "from the historical prepared-panel bootstrap pools.",
        "The deterministic area allocation at each alpha is then held fixed and re-evaluated under the perturbed",
        "coefficients. This reports coefficient-propagation uncertainty around the reported frontier rather than",
        "a separate set of re-optimized frontiers.",
        "",
        "## Revenue benchmark coverage",
        "",
    ]
    for row in coverage.itertuples(index=False):
        lines.append(
            f"- {row.season}: direct realized-price coverage = "
            f"{100.0 * float(row.direct_key_share):.2f}% of decision keys and "
            f"{100.0 * float(row.direct_area_share):.2f}% of baseline cereal area"
        )
    lines.extend(
        [
            "",
            "## Run metadata",
            "",
        f"Bootstrap iterations requested: {n_iterations}",
        f"Random seed: {seed}",
        f"Elapsed time (s): {elapsed_seconds:.2f}",
        "",
        "## Solve status counts",
        "",
        ]
    )
    for row in status_counts.itertuples(index=False):
        lines.append(f"- {row.status}: {row.n}")

    endpoint_rows = summary[summary["Alpha"].isin([0.0, 1.0])]
    lines.extend(
        [
            "",
            "The alpha-wise shaded bands in panels b-c are plotted as envelopes spanning the deterministic",
            "frontier and the fixed-allocation bootstrap ensemble.",
            "",
            "## Endpoint envelopes",
            "",
        ]
    )
    for row in endpoint_rows.itertuples(index=False):
        label = "Water-based endpoint" if abs(row.Alpha - 0.0) < 1e-9 else "Nitrogen-based endpoint"
        lines.append(
            f"- {label}: nitrogen {row.center_nitrogen_mt:.3f} Tg N "
            f"(envelope {row.envelope_low_nitrogen_mt:.3f} to {row.envelope_high_nitrogen_mt:.3f}), "
            f"water {row.center_water_bcm:.3f} BCM "
            f"(envelope {row.envelope_low_water_bcm:.3f} to {row.envelope_high_water_bcm:.3f}), "
            f"optimal {row.n_optimal}/{row.n_total}"
        )

    lines.extend(["", "## Mid-frontier check", ""])
    mid = summary.iloc[len(summary) // 2]
    lines.append(
        f"- Alpha={mid.Alpha:.2f}: nitrogen {mid.center_nitrogen_mt:.3f} Tg N "
        f"(envelope {mid.envelope_low_nitrogen_mt:.3f} to {mid.envelope_high_nitrogen_mt:.3f}), "
        f"water {mid.center_water_bcm:.3f} BCM "
        f"(envelope {mid.envelope_low_water_bcm:.3f} to {mid.envelope_high_water_bcm:.3f}), "
        f"optimal {mid.n_optimal}/{mid.n_total}"
    )
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an SI robustness figure showing uncertainty around the approved Figure 2(a) frontier."
    )
    parser.add_argument("--iterations", type=int, default=500, help="Number of fixed-allocation bootstrap frontier evaluations.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap draws.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    centers = pd.read_csv(CENTERS_CSV).sort_values("Alpha").reset_index(drop=True)
    alphas = centers["Alpha"].astype(float).round(4).tolist()

    layout = default_layout(AUDIT_ROOT)
    contexts, coverage = build_contexts(layout)
    pools = {
        season: load_sampling_pools(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }

    deterministic_allocations = build_deterministic_allocations(contexts, alphas)

    start = time.time()
    iterations = run_fixed_allocation_bootstrap(
        contexts,
        pools,
        deterministic_allocations,
        alphas,
        args.iterations,
        args.seed,
    )
    elapsed = time.time() - start

    summary = build_summary(iterations, centers)

    iterations.to_csv(OUT_ITERATIONS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    coverage.to_csv(OUT_COVERAGE, index=False)
    build_figure(centers, iterations, summary)
    write_audit(
        summary,
        iterations,
        coverage,
        n_iterations=args.iterations,
        seed=args.seed,
        elapsed_seconds=elapsed,
    )

    print(f"figure_png: {OUT_PNG}")
    print(f"figure_pdf: {OUT_PDF}")
    print(f"summary_csv: {OUT_SUMMARY}")
    print(f"audit_md: {OUT_AUDIT}")


if __name__ == "__main__":
    main()
