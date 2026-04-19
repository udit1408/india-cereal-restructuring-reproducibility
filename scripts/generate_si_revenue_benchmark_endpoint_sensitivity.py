#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "si_revenue_benchmark_endpoint_sensitivity"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context,
    metric_totals,
    solve_endpoint,
)
from repro.config import default_layout  # noqa: E402


RATIO_CSV = DATA_DIR / "all_india_unit_price_to_msp_ratio_2013_14_to_2017_18.csv"
OUT_PNG = FIG_DIR / "si_revenue_benchmark_endpoint_sensitivity.png"
OUT_PDF = FIG_DIR / "si_revenue_benchmark_endpoint_sensitivity.pdf"
OUT_SCENARIOS = OUT_DIR / "si_revenue_benchmark_endpoint_sensitivity_values.csv"
OUT_SUMMARY = OUT_DIR / "si_revenue_benchmark_endpoint_sensitivity_summary.csv"
OUT_AUDIT = OUT_DIR / "si_revenue_benchmark_endpoint_sensitivity_audit.md"

CROP_MAP = {
    "Rice": "rice",
    "Wheat": "wheat",
    "Jowar": "jowar",
    "Bajra": "bajra",
    "Maize": "maize",
    "Ragi": "ragi",
}

SCENARIO_LABELS = {
    "MSP": "MSP baseline",
    "2013-14": "Realized-price 2013-14",
    "2014-15": "Realized-price 2014-15",
    "2015-16": "Realized-price 2015-16",
    "2016-17": "Realized-price 2016-17",
    "2017-18": "Realized-price 2017-18",
}


def zero_metrics() -> dict[str, float]:
    return {metric_key: 0.0 for _, metric_key in METRICS}


def load_ratio_scenarios() -> list[tuple[str, dict[str, float]]]:
    ratio = pd.read_csv(RATIO_CSV)
    years = [column for column in ratio.columns if column != "crop_name"]
    scenarios: list[tuple[str, dict[str, float]]] = [("MSP", {crop: 1.0 for crop in CROP_MAP.values()})]
    for year in years:
        crop_ratios = {}
        for _, row in ratio.iterrows():
            crop_key = CROP_MAP.get(row["crop_name"])
            if crop_key is None:
                continue
            value = row[year]
            crop_ratios[crop_key] = float(value) if pd.notna(value) else 1.0
        scenarios.append((year, crop_ratios))
    return scenarios


def scenario_context(base_context: dict[str, object], crop_ratios: dict[str, float]) -> dict[str, object]:
    context = copy.deepcopy(base_context)
    scaled_msp = {}
    for key, value in context["msp_per_prod"].items():
        crop = key[2]
        scaled_msp[key] = float(value) * float(crop_ratios.get(crop, 1.0))
    context["msp_per_prod"] = scaled_msp

    initial_state_profit = {}
    for state in context["states"]:
        total = 0.0
        for district in context["districts_by_state"].get(state, []):
            for crop in context["crops_by_pair"].get((state, district), []):
                key = (state, district, crop)
                total += (
                    context["current_cereal_area"].get(key, 0.0)
                    * context["yield_data"].get(key, 0.0)
                    * 0.01
                    * (context["msp_per_prod"].get(key, 0.0) - context["cost_per_prod"].get(key, 0.0))
                )
        initial_state_profit[state] = total
    context["initial_state_profit"] = initial_state_profit
    context["max_area_constraints"] = {}
    context["cap_repairs"] = 0
    return context


def solve_scenario_bundle(
    base_contexts: dict[str, dict[str, object]],
    scenario_key: str,
    crop_ratios: dict[str, float],
) -> pd.DataFrame:
    contexts = {
        season: scenario_context(context, crop_ratios)
        for season, context in base_contexts.items()
    }
    rows: list[dict[str, object]] = []
    baseline_totals = {
        season: metric_totals(context["current_cereal_area"], context)
        for season, context in contexts.items()
    }

    for strategy in ["Water based", "Nitrogen based"]:
        objective = "water" if strategy == "Water based" else "nitrogen"
        optimized = zero_metrics()
        baseline = zero_metrics()
        statuses = []

        for season, context in contexts.items():
            status, area_map = solve_endpoint(context, objective, use_historical_caps=False)
            statuses.append(f"{season}:{status}")
            if status != "Optimal":
                raise RuntimeError(f"{scenario_key} | {strategy} | {season} returned {status}")
            season_totals = metric_totals(area_map, context)
            for metric_key in baseline:
                baseline[metric_key] += baseline_totals[season][metric_key]
                optimized[metric_key] += season_totals[metric_key]

        for metric_label, metric_key in METRICS:
            baseline_total = baseline[metric_key]
            optimized_total = optimized[metric_key]
            pct_reduction = 100.0 * (baseline_total - optimized_total) / baseline_total
            rows.append(
                {
                    "scenario_key": scenario_key,
                    "scenario_label": SCENARIO_LABELS[scenario_key],
                    "strategy": strategy,
                    "metric": metric_label,
                    "baseline_total": baseline_total,
                    "optimized_total": optimized_total,
                    "pct_reduction": pct_reduction,
                    "display_pct_change": -pct_reduction,
                    "solver_status": ";".join(statuses),
                }
            )
    return pd.DataFrame(rows)


def summarize_ranges(values: pd.DataFrame) -> pd.DataFrame:
    rows = []
    realized = values[values["scenario_key"] != "MSP"].copy()
    for strategy in ["Water based", "Nitrogen based"]:
        for metric in ["Water Demand", "Nitrogen Surplus", "Profit", "Calorie"]:
            subset = realized[(realized["strategy"] == strategy) & (realized["metric"] == metric)]
            if subset.empty:
                continue
            rows.append(
                {
                    "strategy": strategy,
                    "metric": metric,
                    "realized_price_min_pct_reduction": float(subset["pct_reduction"].min()),
                    "realized_price_max_pct_reduction": float(subset["pct_reduction"].max()),
                    "realized_price_mean_pct_reduction": float(subset["pct_reduction"].mean()),
                }
            )
    return pd.DataFrame(rows)


def build_figure(values: pd.DataFrame) -> None:
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

    scenario_order = list(SCENARIO_LABELS.keys())
    y_labels = [SCENARIO_LABELS[key] for key in scenario_order]
    y_positions = list(range(len(y_labels)))
    primary_colors = {"Water Demand": "#1f78b4", "Nitrogen Surplus": "#b15928"}
    markers = {"MSP": "D", "realized": "o"}

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.1), sharey=True, constrained_layout=True)
    panel_specs = [
        ("Water based", "a  Water-based endpoint", ["Water Demand", "Nitrogen Surplus"]),
        ("Nitrogen based", "b  Nitrogen-based endpoint", ["Nitrogen Surplus", "Water Demand"]),
    ]
    plotted_values = values[values["metric"].isin(["Water Demand", "Nitrogen Surplus"])].copy()

    for ax, (strategy, title, metrics) in zip(axes, panel_specs):
        subset = values[values["strategy"] == strategy].copy()
        subset["scenario_key"] = pd.Categorical(subset["scenario_key"], categories=scenario_order, ordered=True)
        subset = subset.sort_values(["scenario_key", "metric"]).reset_index(drop=True)

        for metric, y_offset in zip(metrics, [-0.12, 0.12]):
            metric_df = subset[subset["metric"] == metric].set_index("scenario_key").loc[scenario_order].reset_index()
            x = metric_df["pct_reduction"].to_numpy()
            y = [value + y_offset for value in y_positions]
            for xi, yi, key in zip(x, y, metric_df["scenario_key"]):
                marker = markers["MSP"] if key == "MSP" else markers["realized"]
                face = primary_colors[metric] if key == "MSP" else "white"
                ax.scatter(
                    xi,
                    yi,
                    s=58 if key == "MSP" else 44,
                    marker=marker,
                    facecolor=face,
                    edgecolor=primary_colors[metric],
                    linewidth=1.2,
                    zorder=3,
                )

        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("National percentage reduction (%)")
        ax.xaxis.grid(True, color="0.88", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_yticks(y_positions)
    axes[0].set_yticklabels(y_labels)
    axes[0].invert_yaxis()

    x_min = float(plotted_values["pct_reduction"].min())
    x_max = float(plotted_values["pct_reduction"].max())
    for ax in axes:
        ax.set_xlim(max(0.0, x_min - 2.0), x_max + 2.5)

    legend_handles = [
        Line2D([0], [0], marker="D", markersize=6, linestyle="", markerfacecolor="black", markeredgecolor="black"),
        Line2D([0], [0], marker="o", markersize=6, linestyle="", markerfacecolor="white", markeredgecolor="black"),
        Line2D([0], [0], marker="o", markersize=6, linestyle="", markerfacecolor="white", markeredgecolor="#1f78b4"),
        Line2D([0], [0], marker="o", markersize=6, linestyle="", markerfacecolor="white", markeredgecolor="#b15928"),
    ]
    legend_labels = [
        "MSP baseline",
        "Realized-price scenarios",
        "Water-demand reduction",
        "Nitrogen-surplus reduction",
    ]
    axes[1].legend(legend_handles, legend_labels, frameon=False, fontsize=8, loc="lower right")

    fig.savefig(OUT_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_audit(values: pd.DataFrame, summary: pd.DataFrame) -> None:
    lines = [
        "# Revenue-benchmark endpoint sensitivity audit",
        "",
        "This supplementary figure reruns the approved endpoint solves after",
        "rescaling crop-specific MSP benchmarks by the official all-India realized-price/MSP ratios",
        "for 2013-14 to 2017-18. The scaling is applied at the crop-year level only, because the",
        "alternative official price data do not support a like-for-like district-scale benchmark.",
        "",
        "Accordingly, this exercise is interpreted as benchmark sensitivity rather than as a direct",
        "replacement for the district-scale MSP term used in the main optimization.",
        "",
        "Headline ranges across realized-price scenarios:",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"- {row.strategy} | {row.metric}: "
            f"{row.realized_price_min_pct_reduction:.3f}% to {row.realized_price_max_pct_reduction:.3f}%"
        )
    lines.extend(["", "Solver status by scenario and strategy:"])
    for row in values[["scenario_label", "strategy", "solver_status"]].drop_duplicates().itertuples(index=False):
        lines.append(f"- {row.scenario_label} | {row.strategy}: {row.solver_status}")
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    base_contexts = {
        season: build_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    scenarios = load_ratio_scenarios()

    frames = []
    for scenario_key, crop_ratios in scenarios:
        frames.append(solve_scenario_bundle(base_contexts, scenario_key, crop_ratios))
    values = pd.concat(frames, ignore_index=True)
    summary = summarize_ranges(values)

    values.to_csv(OUT_SCENARIOS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(values)
    write_audit(values, summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a supplementary realized-price benchmark sensitivity figure."
    )
    parser.parse_args()
    main()
