#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "si_revenue_endpoint_equivalent"

OUT_PNG = FIG_DIR / "si_revenue_endpoint_equivalent.png"
OUT_PDF = FIG_DIR / "si_revenue_endpoint_equivalent.pdf"
OUT_VALUES = OUT_DIR / "si_revenue_endpoint_equivalent_values.csv"
OUT_SUMMARY = OUT_DIR / "si_revenue_endpoint_equivalent_summary.csv"
OUT_AUDIT = OUT_DIR / "si_revenue_endpoint_equivalent_audit.md"

DISPLAY_SCENARIO = "2017-18"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from generate_figure2b_clean import METRICS, SEASON_NOTEBOOKS, build_context  # noqa: E402
from generate_si_revenue_profit_sensitivity import (  # noqa: E402
    SCENARIO_YEARS,
    load_crop_year_coverage,
    load_ratio_scenarios,
    load_state_price_lookup,
    solve_scenario_bundle,
)
from repro.config import default_layout  # noqa: E402


METRIC_ORDER = [metric for metric, _ in METRICS]
DISPLAY_LABELS = {
    "N_emission": "Nitrogen emission",
    "N_leach": "Nitrogen leach",
    "AGHG": "AGHG",
    "profit": "Profit",
    "Calorie": "Calorie",
    "P_applied": "Phosphorus application",
    "N_applied": "Nitrogen application",
    "P_surplus": "Phosphorus surplus",
    "N_surplus": "Nitrogen surplus",
    "water": "Water demand",
}
STRATEGIES = ["Water based", "Nitrogen based"]
STRATEGY_COLORS = {
    "Water based": "#1b9e77",
    "Nitrogen based": "#c77c00",
}


def prepare_display_values() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    base_contexts = {
        season: build_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    ratio_scenarios = load_ratio_scenarios()
    state_price_lookup = load_state_price_lookup()
    crop_year_coverage = load_crop_year_coverage()

    all_values = []
    all_coverage = []
    msp_values, msp_coverage = solve_scenario_bundle(base_contexts, "MSP", state_price_lookup)
    all_values.append(msp_values)
    all_coverage.append(msp_coverage)
    for year in SCENARIO_YEARS:
        values, coverage = solve_scenario_bundle(
            base_contexts,
            year,
            state_price_lookup,
            crop_ratios=ratio_scenarios[year],
        )
        all_values.append(values)
        all_coverage.append(coverage)

    all_values_df = pd.concat(all_values, ignore_index=True)
    all_coverage_df = pd.concat(all_coverage, ignore_index=True)
    display = all_values_df[all_values_df["scenario_key"].isin(["MSP", DISPLAY_SCENARIO])].copy()
    display["metric_key"] = display["metric"].map(dict(METRICS))
    display["metric"] = pd.Categorical(display["metric"], categories=METRIC_ORDER, ordered=True)
    display = display.sort_values(["strategy", "metric", "scenario_key"]).reset_index(drop=True)
    return display, all_values_df, all_coverage_df


def summarize_display(display: pd.DataFrame, all_coverage: pd.DataFrame) -> pd.DataFrame:
    coverage = (
        all_coverage.groupby("scenario_key", as_index=False)[
            ["direct_key_share", "fallback_key_share", "direct_area_share", "fallback_area_share"]
        ]
        .mean()
        .copy()
    )
    coverage["scenario_key"] = coverage["scenario_key"].astype(str)
    summary = display.merge(coverage, on="scenario_key", how="left")
    summary["benchmark"] = summary["scenario_key"].map(
        {"MSP": "MSP benchmark", DISPLAY_SCENARIO: f"Realized-price {DISPLAY_SCENARIO} benchmark"}
    )
    return summary


def build_figure(summary: pd.DataFrame, crop_year_coverage: pd.DataFrame) -> None:
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

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.8), sharey=True, constrained_layout=True)
    plot_values = summary.copy()
    x_min = float(plot_values["display_pct_change"].min())
    x_max = float(plot_values["display_pct_change"].max())
    x_pad_left = 4.0
    x_pad_right = 4.0

    for ax, strategy, panel_label in zip(
        axes,
        STRATEGIES,
        ["a  Water-based endpoint", "b  Nitrogen-based endpoint"],
    ):
        subset = summary[summary["strategy"] == strategy].copy()
        subset = subset.set_index(["metric", "scenario_key"]).sort_index()
        color = STRATEGY_COLORS[strategy]
        y_positions = list(range(len(METRIC_ORDER)))

        for idx, metric in enumerate(METRIC_ORDER):
            msp = float(subset.loc[(metric, "MSP"), "display_pct_change"])
            realized = float(subset.loc[(metric, DISPLAY_SCENARIO), "display_pct_change"])
            ax.plot([msp, realized], [idx, idx], color="0.75", linewidth=1.4, zorder=1)
            ax.scatter(
                msp,
                idx,
                s=50,
                marker="D",
                facecolor="black",
                edgecolor="black",
                linewidth=0.9,
                zorder=3,
            )
            ax.scatter(
                realized,
                idx,
                s=54,
                marker="o",
                facecolor=color,
                edgecolor="black",
                linewidth=0.6,
                zorder=4,
            )

        ax.axvline(0.0, color="0.4", linewidth=0.8, zorder=0)
        ax.set_title(panel_label, loc="left", fontweight="bold")
        ax.set_xlim(x_min - x_pad_left, x_max + x_pad_right)
        ax.set_xlabel("Change relative to scenario-specific baseline (%)")
        ax.xaxis.grid(True, color="0.9", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("0.35")
        ax.spines["bottom"].set_color("0.35")
        ax.tick_params(axis="y", length=0)
        ax.invert_yaxis()
        ax.set_yticks(y_positions)
        ax.set_yticklabels([DISPLAY_LABELS[dict(METRICS)[metric]] for metric in METRIC_ORDER])

    axes[1].tick_params(labelleft=True)

    legend_handles = [
        Line2D([0], [0], marker="D", linestyle="", markersize=6.2, markerfacecolor="black", markeredgecolor="black"),
        Line2D([0], [0], marker="o", linestyle="", markersize=6.2, markerfacecolor="white", markeredgecolor="black"),
    ]
    axes[1].legend(
        legend_handles,
        ["MSP benchmark", f"Realized-price {DISPLAY_SCENARIO} benchmark"],
        frameon=False,
        fontsize=8.5,
        loc="lower right",
    )

    display_cov = summary[summary["scenario_key"] == DISPLAY_SCENARIO].iloc[0]
    crop_cov_min_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmin()]
    crop_cov_max_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmax()]
    fig.text(
        0.5,
        0.012,
        (
            "Negative values denote reductions and positive values denote increases. "
            f"The realized-price {DISPLAY_SCENARIO} benchmark uses matched official state-year realized prices where available "
            "and crop-year realized-price/MSP multipliers elsewhere. "
            f"Direct realized-price coverage for {DISPLAY_SCENARIO} is {100.0 * float(display_cov['direct_key_share']):.2f}% of decision keys "
            f"and {100.0 * float(display_cov['direct_area_share']):.2f}% of baseline cereal area. "
            f"Crop-year row coverage across 2013-14 to 2017-18 ranges from {100.0 * float(crop_cov_min_row['match_rate']):.1f}% "
            f"({crop_cov_min_row['crop_name']}, {crop_cov_min_row['year']}) to {100.0 * float(crop_cov_max_row['match_rate']):.1f}% "
            f"({crop_cov_max_row['crop_name']}, {crop_cov_max_row['year']})."
        ),
        ha="center",
        va="bottom",
        fontsize=8.2,
        color="0.25",
    )

    fig.savefig(OUT_PNG, dpi=450, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def write_audit(summary: pd.DataFrame, all_values: pd.DataFrame, crop_year_coverage: pd.DataFrame) -> None:
    display_cov = summary[summary["scenario_key"] == DISPLAY_SCENARIO].iloc[0]
    ordering_rows = []
    for year in SCENARIO_YEARS:
        subset = all_values[all_values["scenario_key"] == year].copy()
        w_water = float(subset[(subset["strategy"] == "Water based") & (subset["metric"] == "Water Demand")]["pct_reduction"].iloc[0])
        n_water = float(subset[(subset["strategy"] == "Nitrogen based") & (subset["metric"] == "Water Demand")]["pct_reduction"].iloc[0])
        w_nsurp = float(subset[(subset["strategy"] == "Water based") & (subset["metric"] == "Nitrogen Surplus")]["pct_reduction"].iloc[0])
        n_nsurp = float(subset[(subset["strategy"] == "Nitrogen based") & (subset["metric"] == "Nitrogen Surplus")]["pct_reduction"].iloc[0])
        ordering_rows.append(
            {
                "scenario_key": year,
                "water_endpoint_has_larger_water_reduction": w_water > n_water,
                "nitrogen_endpoint_has_larger_nsurplus_reduction": n_nsurp > w_nsurp,
            }
        )
    ordering = pd.DataFrame(ordering_rows)

    crop_cov_min_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmin()]
    crop_cov_max_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmax()]
    lines = [
        "# Revenue endpoint equivalent audit",
        "",
        f"This SI-only figure is the Figure 2(b)-equivalent endpoint comparison built from the {DISPLAY_SCENARIO} realized-price benchmark.",
        "Matched official state-year realized prices are used where available, and the district MSP term is",
        "scaled by the corresponding all-India realized-price/MSP multiplier only for unmatched state-crop combinations.",
        "",
        f"For {DISPLAY_SCENARIO}, direct realized-price coverage is {100.0 * float(display_cov['direct_key_share']):.2f}% of decision keys",
        f"and {100.0 * float(display_cov['direct_area_share']):.2f}% of baseline cereal area.",
        f"Crop-year row coverage across 2013-14 to 2017-18 ranges from {100.0 * float(crop_cov_min_row['match_rate']):.1f}% ",
        f"({crop_cov_min_row['crop_name']}, {crop_cov_min_row['year']}) to {100.0 * float(crop_cov_max_row['match_rate']):.1f}% ",
        f"({crop_cov_max_row['crop_name']}, {crop_cov_max_row['year']}).",
        "",
        "Headline 2017-18 endpoint reductions:",
    ]
    for strategy in STRATEGIES:
        subset = summary[(summary["strategy"] == strategy) & (summary["scenario_key"] == DISPLAY_SCENARIO)]
        lines.append(f"## {strategy}")
        for metric in ["Water Demand", "Nitrogen Surplus", "Profit", "Calorie"]:
            row = subset[subset["metric"] == metric].iloc[0]
            lines.append(f"- {metric}: {row['pct_reduction']:.3f}%")
        lines.append("")
    lines.append("Ordering checks across realized-price year scenarios:")
    for row in ordering.itertuples(index=False):
        lines.append(
            f"- {row.scenario_key}: water endpoint larger water reduction={row.water_endpoint_has_larger_water_reduction}; "
            f"nitrogen endpoint larger nitrogen-surplus reduction={row.nitrogen_endpoint_has_larger_nsurplus_reduction}"
        )
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    display, all_values, all_coverage = prepare_display_values()
    crop_year_coverage = load_crop_year_coverage()
    summary = summarize_display(display, all_coverage)

    display.to_csv(OUT_VALUES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(summary, crop_year_coverage)
    write_audit(summary, all_values, crop_year_coverage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the standalone Figure 2(b)-equivalent endpoint comparison using the realized-price benchmark."
    )
    parser.parse_args()
    main()
