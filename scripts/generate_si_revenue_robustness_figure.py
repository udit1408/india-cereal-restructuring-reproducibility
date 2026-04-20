#!/usr/bin/env python3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"
FIG_DIR = ROOT / "figures"
MANUSCRIPT_FIG_DIR = FIG_DIR / "manuscript_final"
OUT_PNG = FIG_DIR / "si_revenue_benchmark_robustness.png"
OUT_PDF = FIG_DIR / "si_revenue_benchmark_robustness.pdf"
MIRROR_OUT_PNG = MANUSCRIPT_FIG_DIR / "si_revenue_benchmark_robustness.png"
MIRROR_OUT_PDF = MANUSCRIPT_FIG_DIR / "si_revenue_benchmark_robustness.pdf"


def load_data():
    ratio = pd.read_csv(DATA_DIR / "state_median_unit_price_to_msp_ratio_2014_15_to_2018_19.csv")
    terms = pd.read_csv(DATA_DIR / "terms_of_trade_summary_2013_14_to_2017_18.csv")
    return ratio, terms


def format_year_label(value: str) -> str:
    return value.replace("-", "\u2013")


def build_figure(ratio: pd.DataFrame, terms: pd.DataFrame):
    crop_order = ["Rice", "Wheat", "Jowar", "Bajra", "Maize", "Ragi"]
    alt_crop_order = ["Jowar", "Bajra", "Maize", "Ragi"]

    ratio = ratio.set_index("crop_name").loc[crop_order]
    years = list(ratio.columns)
    heatmap = ratio.to_numpy(dtype=float)

    terms = terms.set_index("crop_name").loc[alt_crop_order].reset_index()

    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )

    fig = plt.figure(figsize=(12.0, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0])

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    norm = TwoSlopeNorm(vmin=0.50, vcenter=1.0, vmax=1.05)
    im = ax1.imshow(heatmap, cmap="RdBu_r", norm=norm, aspect="auto")
    ax1.set_xticks(np.arange(len(years)))
    ax1.set_xticklabels([format_year_label(y) for y in years], rotation=30, ha="right")
    ax1.set_yticks(np.arange(len(crop_order)))
    ax1.set_yticklabels(crop_order)
    ax1.set_title("a  Realized price relative to MSP", loc="left", fontweight="bold")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Crop")
    for i in range(heatmap.shape[0]):
        for j in range(heatmap.shape[1]):
            ax1.text(
                j,
                i,
                f"{heatmap[i, j]:.2f}",
                ha="center",
                va="center",
                color=(
                    "white"
                    if (0.2126 * im.cmap(norm(heatmap[i, j]))[0] + 0.7152 * im.cmap(norm(heatmap[i, j]))[1] + 0.0722 * im.cmap(norm(heatmap[i, j]))[2]) < 0.52
                    else "black"
                ),
                fontsize=8.4,
                fontweight="bold",
            )
    cbar = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("Realized price / MSP")
    cbar.ax.tick_params(labelsize=8.5)

    y = np.arange(len(alt_crop_order))
    offset = 0.12
    rice_color = "#0072B2"
    wheat_color = "#D55E00"
    ax2.hlines(y - offset, terms["min_ratio_to_rice"], terms["max_ratio_to_rice"], color=rice_color, lw=2.2, alpha=0.45)
    ax2.hlines(y + offset, terms["min_ratio_to_wheat"], terms["max_ratio_to_wheat"], color=wheat_color, lw=2.2, alpha=0.45)
    ax2.scatter(terms["mean_ratio_to_rice"], y - offset, color=rice_color, s=48, label="Relative to rice", zorder=3)
    ax2.scatter(terms["mean_ratio_to_wheat"], y + offset, color=wheat_color, s=48, label="Relative to wheat", zorder=3)
    ax2.axvline(1.0, color="0.35", lw=1.1, ls="--")
    ax2.set_yticks(y)
    ax2.set_yticklabels(alt_crop_order)
    ax2.set_xlim(0.45, 2.35)
    ax2.set_xlabel("Realized-price ratio")
    ax2.set_title("b  Indicative terms of trade", loc="left", fontweight="bold")
    ax2.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax2.xaxis.grid(True, color="0.9", lw=0.8)

    fig.suptitle("Revenue benchmark robustness to official realized-price data", fontsize=12.5, fontweight="bold")
    return fig


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    ratio, terms = load_data()
    fig = build_figure(ratio, terms)
    for png_path, pdf_path in [(OUT_PNG, OUT_PDF), (MIRROR_OUT_PNG, MIRROR_OUT_PDF)]:
        fig.savefig(png_path, dpi=400, bbox_inches="tight", facecolor="white")
        fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT_PDF)


if __name__ == "__main__":
    main()
