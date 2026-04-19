#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
CANONICAL_FIG_DIR = FIG_DIR / "manuscript_final"
WORKING_FIG_DIR = FIG_DIR / "working_variants"
ARTICLE_DIR = ROOT / "R_2_sources" / "article"
PDF_DIR = ROOT / "R_2_PDFs"

PANELS = {
    "a": CANONICAL_FIG_DIR / "figure2a_no_historical_cap_core.png",
    "b": CANONICAL_FIG_DIR / "figure2b_no_historical_cap_core_all_metric_bootstrap.png",
    "c": CANONICAL_FIG_DIR / "figure2c_regenerated_state_retention.png",
    "d": CANONICAL_FIG_DIR / "figure2d_no_historical_cap_core.png",
}

LABEL_BOX_WIDTH = {
    "a": 0.09,
    "b": 0.20,
    "c": 0.09,
    "d": 0.09,
}
LABEL_FONT_SIZE = 15
PANEL_LABEL_AXES_POSITIONS = {
    "a": (0.012, 0.988),
    "b": (0.012, 0.988),
    "c": (0.012, 0.988),
    "d": (0.012, 0.988),
}
PANEL_LABEL_ERASE_BOXES = {
    "b": (360, 0, 760, 235),
    "c": (0, 0, 130, 125),
    "d": (0, 0, 150, 125),
}
PANEL_CROP_PAD_PX = {
    "a": 6,
    "b": 12,
    "c": 38,
    "d": 10,
}

OUT_PNG = CANONICAL_FIG_DIR / "fig2_main_revision2.png"
OUT_PDF = CANONICAL_FIG_DIR / "fig2_main_revision2.pdf"
OUT_WORKING_PNG = WORKING_FIG_DIR / "fig2_revised_r2_regenerated_working.png"
OUT_WORKING_PDF = WORKING_FIG_DIR / "fig2_revised_r2_regenerated_working.pdf"
OUT_ARTICLE_PDF = ARTICLE_DIR / "fig2_revised_r2_regenerated_working.pdf"
OUT_ARTICLE_FIG2T = ARTICLE_DIR / "fig2_t_r2_regenerated_working.pdf"
OUT_ARTICLE_MAIN = ARTICLE_DIR / "fig2_main_revision2.pdf"
OUT_PDF_ARCHIVE = PDF_DIR / "fig2_main_revision2.pdf"


def crop_white_margins(image: np.ndarray, *, threshold: float = 0.985, pad_px: int = 6) -> np.ndarray:
    rgb = image[..., :3]
    mask = np.any(rgb < threshold, axis=2)
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return image

    x0 = max(int(xs.min()) - pad_px, 0)
    x1 = min(int(xs.max()) + pad_px + 1, image.shape[1])
    y0 = max(int(ys.min()) - pad_px, 0)
    y1 = min(int(ys.max()) + pad_px + 1, image.shape[0])
    return image[y0:y1, x0:x1]


def prepare_panel_image(key: str) -> np.ndarray:
    image = mpimg.imread(PANELS[key]).copy()
    erase_box = PANEL_LABEL_ERASE_BOXES.get(key)
    if erase_box is not None:
        x0, y0, x1, y1 = erase_box
        image[y0:y1, x0:x1, :3] = 1.0
        if image.shape[2] == 4:
            image[y0:y1, x0:x1, 3] = 1.0
    return crop_white_margins(image, pad_px=PANEL_CROP_PAD_PX.get(key, 6))


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    CANONICAL_FIG_DIR.mkdir(parents=True, exist_ok=True)
    WORKING_FIG_DIR.mkdir(parents=True, exist_ok=True)
    if not ARTICLE_DIR.exists() and not ARTICLE_DIR.is_symlink():
        ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(10.7, 7.1), facecolor="white")
    grid = GridSpec(2, 2, figure=fig, wspace=0.05, hspace=0.012)

    axes_by_key = {}

    for idx, key in enumerate(["a", "b", "c", "d"]):
        ax = fig.add_subplot(grid[idx // 2, idx % 2])
        axes_by_key[key] = ax
        image = prepare_panel_image(key)
        ax.imshow(image, aspect="auto")
        ax.axis("off")
        label_x, label_y = PANEL_LABEL_AXES_POSITIONS[key]
        ax.text(
            label_x,
            label_y,
            key,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=LABEL_FONT_SIZE,
            fontweight="bold",
            color="black",
            clip_on=False,
        )

    fig.subplots_adjust(left=0.03, right=0.972, top=0.975, bottom=0.035)

    fig.savefig(OUT_PNG, dpi=400, facecolor="white")
    fig.savefig(OUT_PDF, dpi=400, facecolor="white")
    fig.savefig(OUT_WORKING_PNG, dpi=400, facecolor="white")
    fig.savefig(OUT_WORKING_PDF, dpi=400, facecolor="white")
    fig.savefig(OUT_ARTICLE_PDF, dpi=400, facecolor="white")
    fig.savefig(OUT_ARTICLE_FIG2T, dpi=400, facecolor="white")
    fig.savefig(OUT_ARTICLE_MAIN, dpi=400, facecolor="white")
    fig.savefig(OUT_PDF_ARCHIVE, dpi=400, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
