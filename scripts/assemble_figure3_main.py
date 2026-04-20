#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "manuscript_final"

PANEL_A = FIG_DIR / "figure3a_state_area_comparison.png"
PANEL_B = FIG_DIR / "figure3b_alt_trade_network_clean.png"
PANEL_C = FIG_DIR / "figure3c_rice_wheat_trade_network_clean.png"

OUT_PNG = FIG_DIR / "fig3_main_revision2.png"
OUT_PDF = FIG_DIR / "fig3_main_revision2.pdf"


def add_panel_label(ax, label: str) -> None:
    ax.text(
        0.0,
        1.02,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=14,
        fontweight="bold",
        color="black",
    )


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13.2, 10.2), dpi=300, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[0.95, 1.05], wspace=0.02, hspace=0.02)

    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])

    for ax, path, label in (
        (ax_a, PANEL_A, "a"),
        (ax_b, PANEL_B, "b"),
        (ax_c, PANEL_C, "c"),
    ):
        ax.imshow(mpimg.imread(path))
        ax.set_axis_off()
        add_panel_label(ax, label)

    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
