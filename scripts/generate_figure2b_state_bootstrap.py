#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from generate_figure2b_state_heterogeneity import (
    AUDIT_ROOT,
    DATA_DIR,
    FIG_DIR,
    METRICS,
    SEASON_NOTEBOOKS,
    build_context,
    default_layout,
    solve_scenario,
)


OUT_DIR = DATA_DIR / "figure2b_no_historical_cap_core_state_bootstrap"
OUT_PNG = FIG_DIR / "figure2b_no_historical_cap_core_state_bootstrap.png"
OUT_PDF = FIG_DIR / "figure2b_no_historical_cap_core_state_bootstrap.pdf"
OUT_NATIONAL = OUT_DIR / "figure2b_no_historical_cap_core_state_bootstrap_national.csv"
OUT_STATE = OUT_DIR / "figure2b_no_historical_cap_core_state_bootstrap_state_values.csv"
OUT_SUMMARY = OUT_DIR / "figure2b_no_historical_cap_core_state_bootstrap_summary.csv"
OUT_AUDIT = OUT_DIR / "figure2b_no_historical_cap_core_state_bootstrap_audit.md"


def summarize_state_bootstrap(
    state_values: pd.DataFrame,
    *,
    n_boot: int = 5000,
    seed: int = 42,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    metric_order = [metric for metric, _ in METRICS]

    for scenario, scenario_df in state_values.groupby("scenario", observed=False, sort=False):
        states = sorted(scenario_df["state"].unique())
        samples = rng.integers(0, len(states), size=(n_boot, len(states)))

        for metric in metric_order:
            metric_df = (
                scenario_df[scenario_df["metric"] == metric]
                .set_index("state")[["baseline_total", "optimized_total"]]
                .loc[states]
            )
            baseline = metric_df["baseline_total"].to_numpy(dtype=float)
            optimized = metric_df["optimized_total"].to_numpy(dtype=float)

            if np.allclose(baseline.sum(), 0.0):
                continue

            sampled_baseline = baseline[samples].sum(axis=1)
            sampled_optimized = optimized[samples].sum(axis=1)
            pct_reduction = 100.0 * (sampled_baseline - sampled_optimized) / sampled_baseline
            national_pct_reduction = 100.0 * (baseline.sum() - optimized.sum()) / baseline.sum()

            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "n_states": len(states),
                    "n_boot": n_boot,
                    "national_pct_reduction": float(national_pct_reduction),
                    "bootstrap_mean_pct_reduction": float(np.mean(pct_reduction)),
                    "bootstrap_median_pct_reduction": float(np.median(pct_reduction)),
                    "bootstrap_p2_5_pct_reduction": float(np.percentile(pct_reduction, 2.5)),
                    "bootstrap_p10_pct_reduction": float(np.percentile(pct_reduction, 10)),
                    "bootstrap_p90_pct_reduction": float(np.percentile(pct_reduction, 90)),
                    "bootstrap_p97_5_pct_reduction": float(np.percentile(pct_reduction, 97.5)),
                    "national_display_pct_change": float(-national_pct_reduction),
                    "bootstrap_p2_5_display_pct_change": float(-np.percentile(pct_reduction, 97.5)),
                    "bootstrap_p97_5_display_pct_change": float(-np.percentile(pct_reduction, 2.5)),
                }
            )

    summary = pd.DataFrame(rows)
    summary["metric"] = pd.Categorical(summary["metric"], categories=metric_order, ordered=True)
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
    bootstrap_water = summary[summary["scenario"] == "Water based"].set_index("metric")
    bootstrap_n = summary[summary["scenario"] == "Nitrogen based"].set_index("metric")
    whisker_metrics = ["Nitrogen Surplus", "Water Demand"]

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
        label="Water-based",
        zorder=2,
    )
    ax.barh(
        positions + offset,
        nitrogen["display_pct_change"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        label="Nitrogen-based",
        zorder=2,
    )

    for scenario_name, scenario_summary, y_shift in [
        ("Water based", bootstrap_water, -offset),
        ("Nitrogen based", bootstrap_n, offset),
    ]:
        for metric in whisker_metrics:
            row = scenario_summary.loc[metric]
            idx = metric_order.index(metric)
            x = float(row["national_display_pct_change"])
            left = x - float(row["bootstrap_p2_5_display_pct_change"])
            right = float(row["bootstrap_p97_5_display_pct_change"]) - x
            ax.errorbar(
                x,
                positions[idx] + y_shift,
                xerr=[[left], [right]],
                fmt="o",
                color="black",
                markerfacecolor="white",
                markeredgecolor="black",
                ecolor="black",
                elinewidth=1.0,
                capsize=2.8,
                markersize=3.8,
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
        bootstrap_water.loc[whisker_metrics, "bootstrap_p2_5_display_pct_change"].min(),
        bootstrap_n.loc[whisker_metrics, "bootstrap_p2_5_display_pct_change"].min(),
    )
    max_x = max(
        water["display_pct_change"].max(),
        nitrogen["display_pct_change"].max(),
        bootstrap_water.loc[whisker_metrics, "bootstrap_p97_5_display_pct_change"].max(),
        bootstrap_n.loc[whisker_metrics, "bootstrap_p97_5_display_pct_change"].max(),
    )
    ax.set_xlim(min(-65.0, float(min_x) - 4.0), max(30.0, float(max_x) + 4.0))

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#2a9d8f", edgecolor="black", linewidth=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        Line2D(
            [0],
            [0],
            color="black",
            marker="o",
            markerfacecolor="white",
            markeredgecolor="black",
            linestyle="-",
            linewidth=1.0,
            markersize=4.0,
        ),
    ]
    labels = [
        "Water-based",
        "Nitrogen-based",
        "95% state-bootstrap interval",
    ]
    ax.legend(handles, labels, loc="upper right", frameon=False, fontsize=7.5)

    fig.savefig(OUT_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_audit(national: pd.DataFrame, summary: pd.DataFrame, statuses: list[str]) -> None:
    lines = [
        "# Figure 2(b) state-bootstrap audit",
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
        "the national endpoint value together with a 95% interval from resampling states with",
        "replacement from the paired baseline and optimized state totals. These whiskers therefore",
        "sit on the national bars they summarize, rather than representing state medians.",
        "",
        "Season-level solve status:",
    ]
    for status in statuses:
        lines.append(f"- {status}")

    lines.extend(["", "Headline national reductions and 95% state-bootstrap intervals:"])
    for scenario in ["Water based", "Nitrogen based"]:
        lines.append(f"## {scenario}")
        subset = summary[summary["scenario"] == scenario]
        for metric in ["Nitrogen Surplus", "Water Demand"]:
            row = subset[subset["metric"] == metric].iloc[0]
            lines.append(
                f"- {metric}: {row.national_pct_reduction:.3f}% "
                f"(bootstrap 95% interval {row.bootstrap_p2_5_pct_reduction:.3f}% to "
                f"{row.bootstrap_p97_5_pct_reduction:.3f}%)"
            )
        lines.append("")

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
    summary = summarize_state_bootstrap(state_values)

    national.to_csv(OUT_NATIONAL, index=False)
    state_values.to_csv(OUT_STATE, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(national, summary)
    write_audit(national, summary, statuses)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build Figure 2(b) with national bars and state-bootstrap whiskers."
    )
    parser.parse_args()
    main()
