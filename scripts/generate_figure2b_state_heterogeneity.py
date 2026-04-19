#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "figure2b_no_historical_cap_core_state_heterogeneity"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context,
    solve_endpoint,
)
from repro.config import default_layout  # noqa: E402


OUT_PNG = FIG_DIR / "figure2b_no_historical_cap_core_state_heterogeneity.png"
OUT_PDF = FIG_DIR / "figure2b_no_historical_cap_core_state_heterogeneity.pdf"
OUT_NATIONAL = OUT_DIR / "figure2b_no_historical_cap_core_state_heterogeneity_national.csv"
OUT_STATE = OUT_DIR / "figure2b_no_historical_cap_core_state_heterogeneity_state_values.csv"
OUT_SUMMARY = OUT_DIR / "figure2b_no_historical_cap_core_state_heterogeneity_summary.csv"
OUT_AUDIT = OUT_DIR / "figure2b_no_historical_cap_core_state_heterogeneity_audit.md"


def zero_metrics() -> dict[str, float]:
    return {metric_key: 0.0 for _, metric_key in METRICS}


def accumulate_state_metrics(
    area_map: dict[tuple[str, str, str], float],
    context: dict[str, object],
) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = defaultdict(zero_metrics)
    for key, area in area_map.items():
        if not area:
            continue
        state = key[0]
        yield_kg = context["yield_data"].get(key, 0.0)
        production_kg = area * yield_kg
        n_applied = area * context["nitrogen_rate"].get(key, 0.0)
        p_applied = area * context["p_rate"].get(key, 0.0)
        n_surplus = n_applied - production_kg * context["n_removed_rate"].get(key, 0.0)
        p_surplus = p_applied - production_kg * context["p_removed_rate"].get(key, 0.0)
        bucket = totals[state]
        bucket["N_applied"] += n_applied
        bucket["P_applied"] += p_applied
        bucket["N_surplus"] += n_surplus
        bucket["P_surplus"] += p_surplus
        bucket["Calorie"] += production_kg * context["calories_per_prod"].get(key, 0.0)
        bucket["AGHG"] += area * context["aghg_per_ha"].get(key, 0.0)
        bucket["N_leach"] += n_surplus * context["n_leach_rate"].get(key, 0.0)
        bucket["N_emission"] += n_surplus * context["n_emission_rate"].get(key, 0.0)
        bucket["water"] += area * context["water_rate"].get(key, 0.0)
        bucket["profit"] += production_kg * 0.01 * (
            context["msp_per_prod"].get(key, 0.0) - context["cost_per_prod"].get(key, 0.0)
        )
    return totals


def add_metric_dicts(dst: dict[str, dict[str, float]], src: dict[str, dict[str, float]]) -> None:
    for state, metrics in src.items():
        if state not in dst:
            dst[state] = zero_metrics()
        for metric_key, value in metrics.items():
            dst[state][metric_key] += float(value)


def solve_scenario(
    contexts: dict[str, dict[str, object]],
    scenario: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    objective = "water" if scenario == "Water based" else "nitrogen"
    statuses: list[str] = []
    national_rows: list[dict[str, object]] = []
    state_rows: list[dict[str, object]] = []

    baseline_state: dict[str, dict[str, float]] = {}
    optimized_state: dict[str, dict[str, float]] = {}

    for season, context in contexts.items():
        add_metric_dicts(baseline_state, accumulate_state_metrics(context["current_cereal_area"], context))
        status, area_map = solve_endpoint(context, objective, use_historical_caps=False)
        statuses.append(f"{scenario} | {season}: {status}")
        if status != "Optimal":
            raise RuntimeError(f"{scenario} | {season} endpoint solve returned {status}")
        add_metric_dicts(optimized_state, accumulate_state_metrics(area_map, context))

    metric_order = [metric for metric, _ in METRICS]
    national_baseline = zero_metrics()
    national_optimized = zero_metrics()
    for state in sorted(set(baseline_state) | set(optimized_state)):
        base_metrics = baseline_state.get(state, zero_metrics())
        opt_metrics = optimized_state.get(state, zero_metrics())
        for metric_label, metric_key in METRICS:
            baseline_total = float(base_metrics.get(metric_key, 0.0))
            optimized_total = float(opt_metrics.get(metric_key, 0.0))
            pct_reduction = np.nan
            display_pct_change = np.nan
            if abs(baseline_total) > 1e-12:
                pct_reduction = 100.0 * (baseline_total - optimized_total) / baseline_total
                display_pct_change = -pct_reduction
            state_rows.append(
                {
                    "scenario": scenario,
                    "state": state,
                    "metric": metric_label,
                    "baseline_total": baseline_total,
                    "optimized_total": optimized_total,
                    "pct_reduction": pct_reduction,
                    "display_pct_change": display_pct_change,
                }
            )
            national_baseline[metric_key] += baseline_total
            national_optimized[metric_key] += optimized_total

    for metric_label, metric_key in METRICS:
        baseline_total = national_baseline[metric_key]
        optimized_total = national_optimized[metric_key]
        pct_reduction = 100.0 * (baseline_total - optimized_total) / baseline_total
        national_rows.append(
            {
                "scenario": scenario,
                "metric": metric_label,
                "baseline_total": baseline_total,
                "optimized_total": optimized_total,
                "pct_reduction": pct_reduction,
                "display_pct_change": -pct_reduction,
            }
        )

    national = pd.DataFrame(national_rows)
    national["metric"] = pd.Categorical(national["metric"], categories=metric_order, ordered=True)
    national = national.sort_values("metric").reset_index(drop=True)

    state_values = pd.DataFrame(state_rows)
    state_values["metric"] = pd.Categorical(state_values["metric"], categories=metric_order, ordered=True)
    state_values = state_values.sort_values(["metric", "state"]).reset_index(drop=True)
    return national, state_values, statuses


def summarize_state_heterogeneity(state_values: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (scenario, metric), group in state_values.groupby(["scenario", "metric"], observed=False, sort=False):
        values = group["display_pct_change"].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "n_states": 0,
                    "state_median_display_pct": np.nan,
                    "state_p10_display_pct": np.nan,
                    "state_p90_display_pct": np.nan,
                    "state_p25_display_pct": np.nan,
                    "state_p75_display_pct": np.nan,
                }
            )
            continue
        rows.append(
            {
                "scenario": scenario,
                "metric": metric,
                "n_states": int(len(values)),
                "state_median_display_pct": float(np.nanmedian(values)),
                "state_p10_display_pct": float(np.nanpercentile(values, 10)),
                "state_p90_display_pct": float(np.nanpercentile(values, 90)),
                "state_p25_display_pct": float(np.nanpercentile(values, 25)),
                "state_p75_display_pct": float(np.nanpercentile(values, 75)),
            }
        )
    summary = pd.DataFrame(rows)
    summary["metric"] = pd.Categorical(
        summary["metric"],
        categories=[metric for metric, _ in METRICS],
        ordered=True,
    )
    return summary.sort_values(["metric", "scenario"]).reset_index(drop=True)


def build_figure(national: pd.DataFrame, summary: pd.DataFrame) -> None:
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
    water = national[national["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    nitrogen = national[national["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]
    hetero_water = summary[summary["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    hetero_n = summary[summary["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]
    hetero_metrics = ["Nitrogen Surplus", "Water Demand"]

    fig, ax = plt.subplots(figsize=(7.2, 4.9), constrained_layout=True)
    positions = np.arange(len(metric_order))
    offset = 0.18
    bar_height = 0.32

    ax.barh(
        positions - offset,
        water["display_pct_change"].to_numpy(),
        height=bar_height,
        color="#2a9d8f",
        edgecolor="black",
        linewidth=0.5,
        label="Water based (national)",
        zorder=2,
    )
    ax.barh(
        positions + offset,
        nitrogen["display_pct_change"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        label="Nitrogen based (national)",
        zorder=2,
    )

    hetero_indices = [metric_order.index(metric) for metric in hetero_metrics]
    water_subset = hetero_water.loc[hetero_metrics]
    nitrogen_subset = hetero_n.loc[hetero_metrics]
    ax.errorbar(
        water_subset["state_median_display_pct"].to_numpy(),
        positions[hetero_indices] - offset,
        xerr=[
            water_subset["state_median_display_pct"].to_numpy()
            - water_subset["state_p10_display_pct"].to_numpy(),
            water_subset["state_p90_display_pct"].to_numpy()
            - water_subset["state_median_display_pct"].to_numpy(),
        ],
        fmt="o",
        color="black",
        ecolor="black",
        elinewidth=1.0,
        capsize=2.6,
        markersize=3.4,
        zorder=4,
    )
    ax.errorbar(
        nitrogen_subset["state_median_display_pct"].to_numpy(),
        positions[hetero_indices] + offset,
        xerr=[
            nitrogen_subset["state_median_display_pct"].to_numpy()
            - nitrogen_subset["state_p10_display_pct"].to_numpy(),
            nitrogen_subset["state_p90_display_pct"].to_numpy()
            - nitrogen_subset["state_median_display_pct"].to_numpy(),
        ],
        fmt="o",
        color="black",
        ecolor="black",
        elinewidth=1.0,
        capsize=2.6,
        markersize=3.4,
        zorder=4,
    )

    ax.axvline(0, color="black", linewidth=0.8, zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("% Change")
    ax.set_title("Percentage Change in Socio-Environmental Objectives", fontweight="bold", pad=8)
    ax.text(-0.12, 1.02, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    min_x = min(
        water["display_pct_change"].min(),
        nitrogen["display_pct_change"].min(),
        water_subset["state_p10_display_pct"].min(),
        nitrogen_subset["state_p10_display_pct"].min(),
    )
    max_x = max(
        water["display_pct_change"].max(),
        nitrogen["display_pct_change"].max(),
        water_subset["state_p90_display_pct"].max(),
        nitrogen_subset["state_p90_display_pct"].max(),
    )
    ax.set_xlim(min(-50.0, float(min_x) - 5.0), max(30.0, float(max_x) + 5.0))

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#2a9d8f", edgecolor="black", linewidth=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        Line2D([0], [0], color="black", marker="o", linestyle="-", linewidth=1.0, markersize=4.0),
    ]
    labels = [
        "Water based (national)",
        "Nitrogen based (national)",
        "State median (10th-90th percentile) for water and nitrogen",
    ]
    ax.legend(handles, labels, loc="upper right", frameon=False, fontsize=8)

    fig.savefig(OUT_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_audit(
    national: pd.DataFrame,
    summary: pd.DataFrame,
    statuses: list[str],
) -> None:
    lines = [
        "# Figure 2(b) state-heterogeneity audit",
        "",
        "This panel uses the approved endpoint branch:",
        "- unchanged district cropped area,",
        "- crop substitution limited to historically cultivated cereals,",
        "- no crop-specific historical area ceiling on future allocations,",
        "- state calorie-adequacy floor,",
        "- state MSP-benchmarked income floor.",
        "",
        "Colored bars report the national aggregate percentage change for the two endpoint strategies.",
        "Black points and whiskers are shown for water demand and nitrogen surplus only, and report",
        "the state median and 10th-90th percentile of state-level percentage changes from those same",
        "endpoint solutions. These whiskers summarize interstate heterogeneity; they are not",
        "parameter-estimation confidence intervals.",
        "",
        "Season-level solve status:",
    ]
    for status in statuses:
        lines.append(f"- {status}")
    lines.extend(["", "Headline national reductions:"])
    for scenario in ["Water based", "Nitrogen based"]:
        lines.append(f"## {scenario}")
        subset = national[national["scenario"] == scenario]
        for row in subset.itertuples(index=False):
            if row.metric in {"Nitrogen Surplus", "Water Demand"}:
                lines.append(f"- {row.metric}: {row.pct_reduction:.3f}%")
        lines.append("")
    lines.append("Selected heterogeneity summaries:")
    for scenario in ["Water based", "Nitrogen based"]:
        subset = summary[summary["scenario"] == scenario]
        for metric in ["Nitrogen Surplus", "Water Demand", "Profit", "Calorie"]:
            row = subset[subset["metric"] == metric].iloc[0]
            lines.append(
                f"- {scenario} | {metric}: median {row.state_median_display_pct:.3f}, "
                f"p10 {row.state_p10_display_pct:.3f}, p90 {row.state_p90_display_pct:.3f}"
            )
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    contexts = {
        season: build_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    for context in contexts.values():
        context["max_area_constraints"] = {}
        context["cap_repairs"] = 0

    national_frames = []
    state_frames = []
    statuses: list[str] = []
    for scenario in ["Water based", "Nitrogen based"]:
        national, state_values, scenario_statuses = solve_scenario(contexts, scenario)
        national_frames.append(national)
        state_frames.append(state_values)
        statuses.extend(scenario_statuses)

    national = pd.concat(national_frames, ignore_index=True)
    state_values = pd.concat(state_frames, ignore_index=True)
    summary = summarize_state_heterogeneity(state_values)

    national.to_csv(OUT_NATIONAL, index=False)
    state_values.to_csv(OUT_STATE, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(national, summary)
    write_audit(national, summary, statuses)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build Figure 2(b) with national bars and state-level heterogeneity bands."
    )
    parser.parse_args()
    main()
