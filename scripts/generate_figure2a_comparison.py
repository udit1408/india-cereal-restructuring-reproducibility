#!/usr/bin/env python3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"

OLD_FRONTIER = AUDIT_ROOT / "outputs" / "generated" / "figure2a" / "figure2a_combined_frontier.csv"
NEW_FRONTIER = (
    AUDIT_ROOT
    / "outputs"
    / "generated"
    / "figure2a_clean_profit_highs_histmax_raw_full"
    / "combined_by_alpha.csv"
)
LEGACY_KHARIF = AUDIT_ROOT / "generated" / "kharif_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv"
LEGACY_RABI = AUDIT_ROOT / "generated" / "rabi_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv"

OUT_FIG_PNG = FIG_DIR / "figure2a_old_new_comparison.png"
OUT_FIG_PDF = FIG_DIR / "figure2a_old_new_comparison.pdf"
OUT_TABLE_SELECTED = DATA_DIR / "figure2a_old_new_selected_alphas.tex"
OUT_TABLE_ENDPOINTS = DATA_DIR / "figure2a_endpoint_decomposition.tex"


def load_frontiers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    old = pd.read_csv(OLD_FRONTIER).rename(
        columns={
            "Objective Nitrogen": "objective_nitrogen",
            "Objective Water": "objective_water",
        }
    )
    new = pd.read_csv(NEW_FRONTIER)[
        ["Alpha", "objective_nitrogen", "objective_water", "nitrogen_mt", "water_bcm"]
    ].copy()

    kharif = pd.read_csv(LEGACY_KHARIF).groupby("Alpha", as_index=False)[["Objective Nitrogen", "Objective Water"]].mean()
    rabi = pd.read_csv(LEGACY_RABI).groupby("Alpha", as_index=False)[["Objective Nitrogen", "Objective Water"]].mean()
    legacy_sum = kharif.merge(rabi, on="Alpha", suffixes=("_kharif", "_rabi"))
    legacy_sum["nitrogen_mt"] = (
        legacy_sum["Objective Nitrogen_kharif"] + legacy_sum["Objective Nitrogen_rabi"]
    ) / 1e9
    legacy_sum["water_bcm"] = (
        legacy_sum["Objective Water_kharif"] + legacy_sum["Objective Water_rabi"]
    ) / 1e9

    return old.sort_values("Alpha").reset_index(drop=True), new.sort_values("Alpha").reset_index(drop=True), legacy_sum


def _format_value(value: float) -> str:
    return f"{value:.3f}"


def write_selected_alpha_table(old: pd.DataFrame, new: pd.DataFrame) -> None:
    selected = (
        old.rename(columns={"nitrogen_mt": "nitrogen_mt_old", "water_bcm": "water_bcm_old"})
        .merge(
            new[["Alpha", "nitrogen_mt", "water_bcm"]].rename(
                columns={"nitrogen_mt": "nitrogen_mt_new", "water_bcm": "water_bcm_new"}
            ),
            on="Alpha",
        )
        .loc[lambda df: df["Alpha"].isin([0.0, 0.25, 0.5, 0.75, 1.0])]
        .copy()
    )
    selected["delta_n"] = selected["nitrogen_mt_new"] - selected["nitrogen_mt_old"]
    selected["delta_w"] = selected["water_bcm_new"] - selected["water_bcm_old"]

    lines = [
        r"\begin{tabular}{rrrrrrr}",
        r"\toprule",
        r"$\alpha$ & Legacy $N$ & Updated $N$ & $\Delta N$ & Legacy $W$ & Updated $W$ & $\Delta W$ \\",
        r"& (Tg N) & (Tg N) & (Tg N) & (BCM) & (BCM) & (BCM) \\",
        r"\midrule",
    ]
    for row in selected.itertuples(index=False):
        lines.append(
            f"{row.Alpha:.2f} & "
            f"{_format_value(row.nitrogen_mt_old)} & "
            f"{_format_value(row.nitrogen_mt_new)} & "
            f"{_format_value(row.delta_n)} & "
            f"{_format_value(row.water_bcm_old)} & "
            f"{_format_value(row.water_bcm_new)} & "
            f"{_format_value(row.delta_w)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    OUT_TABLE_SELECTED.write_text("\n".join(lines) + "\n")


def write_endpoint_decomposition_table(old: pd.DataFrame, new: pd.DataFrame, legacy_sum: pd.DataFrame) -> None:
    old_end = old.loc[old["Alpha"].isin([0.0, 1.0]), ["Alpha", "nitrogen_mt", "water_bcm"]].rename(
        columns={"nitrogen_mt": "legacy_plot_n", "water_bcm": "legacy_plot_w"}
    )
    legacy_end = legacy_sum.loc[legacy_sum["Alpha"].isin([0.0, 1.0]), ["Alpha", "nitrogen_mt", "water_bcm"]].rename(
        columns={"nitrogen_mt": "legacy_sum_n", "water_bcm": "legacy_sum_w"}
    )
    new_end = new.loc[new["Alpha"].isin([0.0, 1.0]), ["Alpha", "nitrogen_mt", "water_bcm"]].rename(
        columns={"nitrogen_mt": "updated_n", "water_bcm": "updated_w"}
    )
    merged = old_end.merge(legacy_end, on="Alpha").merge(new_end, on="Alpha")

    lines = [
        r"\begin{tabular}{rrrrrrr}",
        r"\toprule",
        r"$\alpha$ & Legacy plot $N$ & Legacy sum $N$ & Updated $N$ & Legacy plot $W$ & Legacy sum $W$ & Updated $W$ \\",
        r"& (Tg N) & (Tg N) & (Tg N) & (BCM) & (BCM) & (BCM) \\",
        r"\midrule",
    ]
    for row in merged.itertuples(index=False):
        lines.append(
            f"{row.Alpha:.2f} & "
            f"{_format_value(row.legacy_plot_n)} & "
            f"{_format_value(row.legacy_sum_n)} & "
            f"{_format_value(row.updated_n)} & "
            f"{_format_value(row.legacy_plot_w)} & "
            f"{_format_value(row.legacy_sum_w)} & "
            f"{_format_value(row.updated_w)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    OUT_TABLE_ENDPOINTS.write_text("\n".join(lines) + "\n")


def _add_endpoint_markers(ax: plt.Axes, frame: pd.DataFrame) -> None:
    water = frame.loc[frame["Alpha"] == 0.0].iloc[0]
    nitrogen = frame.loc[frame["Alpha"] == 1.0].iloc[0]
    ax.scatter(
        water["nitrogen_mt"],
        water["water_bcm"],
        color="#5b2a86",
        edgecolors="black",
        linewidths=0.8,
        marker="*",
        s=260,
        zorder=4,
    )
    ax.scatter(
        nitrogen["nitrogen_mt"],
        nitrogen["water_bcm"],
        color="#d89216",
        edgecolors="black",
        linewidths=0.8,
        marker="*",
        s=260,
        zorder=4,
    )


def _plot_panel(ax: plt.Axes, frame: pd.DataFrame, panel_letter: str, panel_title: str, add_legend: bool) -> None:
    interior = frame[(frame["Alpha"] > 0.0) & (frame["Alpha"] < 1.0)].copy()
    ax.scatter(
        interior["nitrogen_mt"],
        interior["water_bcm"],
        c=interior["Alpha"],
        cmap="viridis",
        edgecolors="white",
        linewidths=0.35,
        s=46,
        zorder=2,
    )
    _add_endpoint_markers(ax, frame)
    ax.set_title(panel_title, fontweight="bold", pad=10)
    ax.text(
        -0.12,
        1.02,
        panel_letter,
        transform=ax.transAxes,
        fontsize=12.5,
        fontweight="bold",
        va="top",
    )
    ax.set_xlabel("Optimal Nitrogen surplus generation (Mt)", fontweight="bold")
    ax.set_ylabel("Optimal Water demand (BCM)", fontweight="bold")
    ax.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if add_legend:
        handles = [
            Line2D(
                [0],
                [0],
                marker="*",
                color="w",
                markerfacecolor="#5b2a86",
                markeredgecolor="black",
                markersize=12,
                label="Water optimization",
            ),
            Line2D(
                [0],
                [0],
                marker="*",
                color="w",
                markerfacecolor="#d89216",
                markeredgecolor="black",
                markersize=12,
                label="Nitrogen surplus optimization",
            ),
        ]
        ax.legend(handles=handles, loc="upper right", frameon=True, facecolor="white")


def build_figure(old: pd.DataFrame, new: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 10.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), constrained_layout=True)
    _plot_panel(axes[0], old, "a", "Legacy plotted frontier", add_legend=False)
    _plot_panel(axes[1], new, "b", "Updated Methods-faithful frontier", add_legend=True)
    fig.savefig(OUT_FIG_PNG, dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_FIG_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    old, new, legacy_sum = load_frontiers()
    build_figure(old, new)
    write_selected_alpha_table(old, new)
    write_endpoint_decomposition_table(old, new, legacy_sum)
    print(OUT_FIG_PDF)
    print(OUT_TABLE_SELECTED)
    print(OUT_TABLE_ENDPOINTS)


if __name__ == "__main__":
    main()
