#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from generate_figure2b_clean import METRICS


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"
WHISKER_DIR = DATA_DIR / "figure2b_no_historical_cap_core_whiskers"
SUMMARY_CSV = WHISKER_DIR / "figure2b_no_historical_cap_core_whiskers_summary.csv"
OUT_PNG = FIG_DIR / "figure2b_no_historical_cap_core_all_metric_bootstrap.png"
OUT_PDF = FIG_DIR / "figure2b_no_historical_cap_core_all_metric_bootstrap.pdf"
OUT_AUDIT = WHISKER_DIR / "figure2b_no_historical_cap_core_all_metric_bootstrap_audit.md"


DISPLAY_INTERVALS = {
    (scenario, metric_label)
    for scenario in ("Water based", "Nitrogen based")
    for metric_label, _ in METRICS
}


def load_summary() -> pd.DataFrame:
    summary = pd.read_csv(SUMMARY_CSV)
    metric_order = [label for label, _ in METRICS]
    summary["metric"] = pd.Categorical(summary["metric"], categories=metric_order, ordered=True)
    return summary.sort_values(["metric", "scenario"]).reset_index(drop=True)


def build_figure(summary: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 10.5,
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

    fig, ax = plt.subplots(figsize=(7.6, 5.0), constrained_layout=True)
    ax.barh(
        positions - offset,
        water["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#2a9d8f",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )
    ax.barh(
        positions + offset,
        nitrogen["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )

    for scenario_name, scenario_frame, y_shift in [
        ("Water based", water, -offset),
        ("Nitrogen based", nitrogen, offset),
    ]:
        for metric in metric_order:
            if (scenario_name, metric) not in DISPLAY_INTERVALS:
                continue
            row = scenario_frame.loc[metric]
            x = float(row["center_display_pct"])
            ax.errorbar(
                x,
                positions[metric_order.index(metric)] + y_shift,
                xerr=np.array([[float(row["lower_err_display"])], [float(row["upper_err_display"])]]),
                fmt="none",
                ecolor="#303030",
                elinewidth=1.0,
                capsize=2.6,
                zorder=4,
            )

    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("Beneficial change relative to baseline (%)")
    ax.text(-0.12, 1.02, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    x_min = min(float(water["center_display_pct"].min()), float(nitrogen["center_display_pct"].min()))
    x_max = max(float(water["center_display_pct"].max()), float(nitrogen["center_display_pct"].max()))
    for scenario_name, metric in DISPLAY_INTERVALS:
        frame = water if scenario_name == "Water based" else nitrogen
        row = frame.loc[metric]
        x_min = min(x_min, float(row["center_display_pct"]) - float(row["lower_err_display"]))
        x_max = max(x_max, float(row["center_display_pct"]) + float(row["upper_err_display"]))
    ax.set_xlim(min(-5.0, x_min - 4.0), max(30.0, x_max + 4.0))

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#2a9d8f", edgecolor="black", linewidth=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        Line2D([0], [0], color="#303030", linestyle="-", linewidth=1.0),
    ]
    labels = [
        "Water-based",
        "Nitrogen-based",
        "95% bootstrap interval",
    ]
    ax.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.53, 1.015),
        ncol=3,
        frameon=False,
        fontsize=7.2,
        handlelength=1.8,
        borderaxespad=0.0,
        columnspacing=1.0,
    )

    fig.savefig(OUT_PNG, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def write_audit(summary: pd.DataFrame) -> None:
    lines = [
        "# Figure 2(b) all-metric bootstrap overlay audit",
        "",
        "This panel uses the propagated district-input bootstrap from the approved",
        "Figure 2(b) branch and displays whiskers for all",
        "ten socio-environmental metrics under both endpoint strategies.",
        "",
        "Displayed intervals:",
    ]

    for scenario_name in ("Water based", "Nitrogen based"):
        for metric_label, _ in METRICS:
            row = summary[(summary["scenario"] == scenario_name) & (summary["metric"] == metric_label)].iloc[0]
            lines.append(
                f"- {scenario_name} | {metric_label}: center {row.center_pct_reduction:.3f}% ; "
                f"95% CI [{row.bootstrap_p2_5_pct_reduction:.3f}, {row.bootstrap_p97_5_pct_reduction:.3f}]%"
            )

    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    summary = load_summary()
    build_figure(summary)
    write_audit(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render Figure 2(b) with district-input bootstrap whiskers for all metrics."
    )
    parser.parse_args()
    main()
