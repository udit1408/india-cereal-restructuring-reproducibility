#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_si_s5_original_trade_network import (  # noqa: E402
    FIG_DIR,
    MASTER_ORDER,
    STATE_ABBREV,
    build_matrix,
    crop_white_margins,
    draw_chord_panel,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "submission_assets" / "source_data" / "csv"
OUT_DIR = ROOT / "data" / "generated" / "si_s18_msp_benchmark_figure3_clean"

PANEL_A_PNG = FIG_DIR / "si_s18_msp_benchmark_figure3a_clean.png"
PANEL_A_PDF = FIG_DIR / "si_s18_msp_benchmark_figure3a_clean.pdf"
PANEL_B_PNG = FIG_DIR / "si_s18_msp_benchmark_figure3b_clean.png"
PANEL_B_PDF = FIG_DIR / "si_s18_msp_benchmark_figure3b_clean.pdf"
PANEL_C_PNG = FIG_DIR / "si_s18_msp_benchmark_figure3c_clean.png"
PANEL_C_PDF = FIG_DIR / "si_s18_msp_benchmark_figure3c_clean.pdf"
COMPOSITE_PNG = FIG_DIR / "si_msp_benchmark_figure3.png"
COMPOSITE_PDF = FIG_DIR / "si_msp_benchmark_figure3.pdf"

CROP_ORDER = ["bajra", "jowar", "maize", "ragi", "rice", "wheat"]
CROP_COLORS = {
    "bajra": "#c54b3c",
    "jowar": "#b3be39",
    "maize": "#39ad39",
    "ragi": "#2e99a3",
    "rice": "#4d47c1",
    "wheat": "#b846b2",
}


def plot_panel_a(display: pd.DataFrame) -> None:
    states = (
        display[["State", "state_order"]]
        .drop_duplicates()
        .sort_values("state_order")["State"]
        .tolist()
    )
    state_labels = [STATE_ABBREV[state] for state in states]
    y_positions = list(range(len(states)))
    original = (
        display.pivot_table(index="State", columns="Crop", values="original_area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=states, columns=CROP_ORDER, fill_value=0.0)
        / 1_000_000.0
    )
    optimized = (
        display.pivot_table(index="State", columns="Crop", values="optimized_area_ha", aggfunc="sum", fill_value=0.0)
        .reindex(index=states, columns=CROP_ORDER, fill_value=0.0)
        / 1_000_000.0
    )

    fig, ax = plt.subplots(figsize=(11.2, 5.0), dpi=320)
    original_left = np.zeros(len(states))
    optimized_left = np.zeros(len(states))
    for crop in CROP_ORDER:
        original_width = -original[crop].to_numpy(dtype=float)
        optimized_width = optimized[crop].to_numpy(dtype=float)
        ax.barh(
            y_positions,
            original_width,
            left=original_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.25,
            height=0.56,
        )
        ax.barh(
            y_positions,
            optimized_width,
            left=optimized_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.25,
            height=0.56,
            label=crop,
        )
        original_left += original_width
        optimized_left += optimized_width

    ax.axvline(0, color="#111111", linewidth=1.1)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(state_labels, fontsize=9, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlabel("Area (Mha)", fontsize=10, fontweight="bold")
    ax.text(0.25, 0.10, "Original Area", transform=ax.transAxes, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(0.74, 0.10, "Optimized Area", transform=ax.transAxes, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.grid(axis="x", color="#d8dee9", linestyle="--", linewidth=0.65, alpha=0.9)
    ax.set_axisbelow(True)
    max_abs = max(abs(original_left.min()), optimized_left.max())
    ax.set_xlim(-max_abs * 1.08, max_abs * 1.08)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[: len(CROP_ORDER)], labels[: len(CROP_ORDER)], loc="lower right", frameon=True, fontsize=8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
    fig.savefig(PANEL_A_PNG, dpi=320, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(PANEL_A_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def load_display_panel_a() -> pd.DataFrame:
    df = pd.read_csv(SOURCE_DIR / "FigS18a_state_cmp.csv")
    return df.loc[df["State"].isin(STATE_ABBREV)].copy()


def load_edges(filename: str, value_col: str) -> pd.DataFrame:
    df = pd.read_csv(SOURCE_DIR / filename)
    edges = df[["source_state", "target_state", value_col]].rename(columns={value_col: "trade_kcal"}).copy()
    edges = edges.loc[(edges["source_state"] != edges["target_state"]) & (edges["trade_kcal"] > 0)]
    return edges.reset_index(drop=True)


def select_states(edges: pd.DataFrame, max_states: int) -> list[str]:
    flow = pd.concat(
        [
            edges.groupby("source_state", as_index=False)["trade_kcal"]
            .sum()
            .rename(columns={"source_state": "State", "trade_kcal": "flow"}),
            edges.groupby("target_state", as_index=False)["trade_kcal"]
            .sum()
            .rename(columns={"target_state": "State", "trade_kcal": "flow"}),
        ],
        ignore_index=True,
    )
    flow = (
        flow.groupby("State", as_index=False)["flow"]
        .sum()
        .loc[lambda df: df["State"].isin(STATE_ABBREV)]
        .sort_values("flow", ascending=False)
        .reset_index(drop=True)
    )
    chosen = flow["State"].head(max_states).tolist()
    order_rank = {state: idx for idx, state in enumerate(MASTER_ORDER)}
    return sorted(
        chosen,
        key=lambda state: (order_rank.get(state, 999), -float(flow.loc[flow["State"] == state, "flow"].iloc[0])),
    )


def assemble_composite() -> None:
    fig = plt.figure(figsize=(13.0, 10.0), dpi=320, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[0.92, 1.0], wspace=0.015, hspace=0.015)
    axes = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    images = [
        crop_white_margins(mpimg.imread(PANEL_A_PNG), pad_px=6),
        crop_white_margins(mpimg.imread(PANEL_B_PNG), pad_px=8),
        crop_white_margins(mpimg.imread(PANEL_C_PNG), pad_px=8),
    ]
    for ax, image, label in zip(axes, images, ["a", "b", "c"]):
        ax.imshow(image)
        ax.set_axis_off()
        ax.text(0.0, 1.01, label, transform=ax.transAxes, ha="left", va="bottom", fontsize=14, fontweight="bold")
    fig.savefig(COMPOSITE_PNG, dpi=320, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(COMPOSITE_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    display = load_display_panel_a()
    plot_panel_a(display)

    alt_edges = load_edges("FigS18b_edges_cmp.csv", "optimized_trade_kcal")
    rw_edges = load_edges("FigS18c_edges_cmp.csv", "optimized_trade_kcal")
    alt_states = select_states(alt_edges, max_states=18)
    rw_states = select_states(rw_edges, max_states=20)
    alt_fromto, alt_matrix = build_matrix(alt_edges, alt_states)
    rw_fromto, rw_matrix = build_matrix(rw_edges, rw_states)
    draw_chord_panel(alt_matrix, states=alt_states, out_png=PANEL_B_PNG, out_pdf=PANEL_B_PDF)
    draw_chord_panel(rw_matrix, states=rw_states, out_png=PANEL_C_PNG, out_pdf=PANEL_C_PDF)
    assemble_composite()

    display.to_csv(OUT_DIR / "si_s18_msp_panel_a_state_area.csv", index=False)
    alt_fromto.to_csv(OUT_DIR / "si_s18_msp_panel_b_fromto_displayed.csv", index=False)
    rw_fromto.to_csv(OUT_DIR / "si_s18_msp_panel_c_fromto_displayed.csv", index=False)
    (OUT_DIR / "si_s18_msp_benchmark_figure3_manifest.md").write_text(
        "\n".join(
            [
                "# Supplementary Figure S18 clean rebuild",
                "",
                "Rebuilt from the submitted source-data CSVs for the district-MSP comparison.",
                "Chord panels use the same directional-link styling as the revised Figure 3 panels.",
                f"Panel b displayed states: {', '.join(alt_states)}.",
                f"Panel c displayed states: {', '.join(rw_states)}.",
            ]
        )
        + "\n"
    )
    print(f"figure_pdf: {COMPOSITE_PDF}")
    print(f"figure_png: {COMPOSITE_PNG}")


if __name__ == "__main__":
    main()
