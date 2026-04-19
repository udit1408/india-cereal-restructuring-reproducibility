#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
GENERATED_DIR = AUDIT_ROOT / "generated"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"

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
    ("Nitrogen Emission", "Original N_emission", "Optimized N_emission"),
    ("Nitrogen Leach", "Original N_leach", "Optimized N_leach"),
    ("Greenhouse Gas emission", "Original AGHG", "Optimized AGHG"),
    ("Profit", "Original profit", "Optimized profit"),
    ("Calorie", "Original Calorie", "Optimized Calorie"),
    ("Phosphorus application", "Original Total P Applied", "Optimized Total P Applied"),
    ("Nitrogen application", "Original Total N Applied", "Optimized Total N Applied"),
    ("Phosphorus Surplus", "Original Total P surplus", "Optimized Total P surplus"),
    ("Nitrogen Surplus", "Original Total N surplus", "Optimized Total N surplus"),
    ("Water Demand", "Original water", "Optimized water"),
]

OUT_FIG_PNG = FIG_DIR / "figure2b_regenerated_deterministic.png"
OUT_FIG_PDF = FIG_DIR / "figure2b_regenerated_deterministic.pdf"
OUT_VALUES_CSV = DATA_DIR / "figure2b_regenerated_deterministic_values.csv"
OUT_VALUES_TEX = DATA_DIR / "figure2b_regenerated_deterministic_values.tex"
OUT_AUDIT_MD = DATA_DIR / "figure2b_regenerated_deterministic_audit.md"


def load_scenario_frame(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        if frame.columns[0].startswith("Unnamed") or frame.columns[0] == "":
            frame = frame.drop(columns=frame.columns[0])
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    return combined


def compute_metric_table() -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for scenario, files in SCENARIO_FILES.items():
        frame = load_scenario_frame(files)
        for metric, original_col, optimized_col in METRICS:
            original_total = frame[original_col].sum()
            optimized_total = frame[optimized_col].sum()
            pct_reduction = 100.0 * (original_total - optimized_total) / original_total
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "original_total": original_total,
                    "optimized_total": optimized_total,
                    "pct_reduction": pct_reduction,
                    "display_pct_change": -pct_reduction,
                }
            )
    output = pd.DataFrame(rows)
    output["metric"] = pd.Categorical(
        output["metric"], categories=[metric for metric, _, _ in METRICS], ordered=True
    )
    output = output.sort_values(["metric", "scenario"]).reset_index(drop=True)
    return output


def write_latex_table(table: pd.DataFrame) -> None:
    pivot = table.pivot(index="metric", columns="scenario", values="pct_reduction").loc[
        [metric for metric, _, _ in METRICS]
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
    OUT_VALUES_TEX.write_text("\n".join(lines) + "\n")


def write_audit_note(table: pd.DataFrame) -> None:
    audit_lines = [
        "# Figure 2(b) deterministic regeneration audit",
        "",
        "This table is rebuilt directly from the four endpoint optimization outputs in",
        "`revision_2/_audit/Nitrogen-Surplus-restructuring/generated/`.",
        "",
        "For each scenario, kharif and rabi outputs are concatenated, annual totals are summed",
        "across all district-crop rows, and the plotted percentage change is computed as",
        "`100 * (Original - Optimized) / Original`.",
        "",
        "The rendered panel uses `display_pct_change = -pct_reduction`, so reductions plot to the",
        "left of zero and gains in calorie or profit plot to the right.",
        "",
        "This script intentionally does not add uncertainty whiskers because the current workspace",
        "does not contain a single reproducible bootstrap pipeline covering both the water-based and",
        "nitrogen-based scenarios end to end. Deterministic bar centers are therefore regenerated",
        "cleanly first; uncertainty should only be added back after a traceable bootstrap rebuild.",
        "",
        "Key combined annual percentage reductions:",
        "",
    ]
    for scenario in ["Water based", "Nitrogen based"]:
        subset = table[table["scenario"] == scenario]
        audit_lines.append(f"## {scenario}")
        for row in subset.itertuples(index=False):
            audit_lines.append(f"- {row.metric}: {row.pct_reduction:.3f}%")
        audit_lines.append("")
    OUT_AUDIT_MD.write_text("\n".join(audit_lines).rstrip() + "\n")


def build_figure(table: pd.DataFrame) -> None:
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

    metric_order = [metric for metric, _, _ in METRICS]
    water = (
        table[table["scenario"] == "Water based"]
        .set_index("metric")
        .loc[metric_order, "display_pct_change"]
        .to_list()
    )
    nitrogen = (
        table[table["scenario"] == "Nitrogen based"]
        .set_index("metric")
        .loc[metric_order, "display_pct_change"]
        .to_list()
    )

    fig, ax = plt.subplots(figsize=(7.0, 4.6), constrained_layout=True)
    positions = list(range(len(metric_order)))
    offset = 0.18
    bar_height = 0.32

    ax.barh(
        [p - offset for p in positions],
        water,
        height=bar_height,
        color="#7f3fbf",
        edgecolor="black",
        linewidth=0.5,
        label="Water based",
        zorder=3,
    )
    ax.barh(
        [p + offset for p in positions],
        nitrogen,
        height=bar_height,
        color="#f0b323",
        edgecolor="black",
        linewidth=0.5,
        label="Nitrogen based",
        zorder=3,
    )

    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("% Change")
    ax.set_title("Percentage Change in Socio-Environmental Objectives", fontweight="bold", pad=8)
    ax.text(
        -0.12,
        1.02,
        "b",
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="bottom",
    )
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    min_x = min(min(water), min(nitrogen))
    max_x = max(max(water), max(nitrogen))
    left = min(-50, min_x - 5)
    right = max(30, max_x + 5)
    ax.set_xlim(left, right)

    ax.legend(loc="upper right", frameon=False, fontsize=8)

    fig.savefig(OUT_FIG_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_FIG_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    table = compute_metric_table()
    table.to_csv(OUT_VALUES_CSV, index=False)
    write_latex_table(table)
    write_audit_note(table)
    build_figure(table)


if __name__ == "__main__":
    main()
