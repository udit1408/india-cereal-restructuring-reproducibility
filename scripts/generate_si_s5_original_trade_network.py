#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_hex, to_rgb
from pycirclize import Circos
from pycirclize.parser import Matrix


ROOT = Path(__file__).resolve().parents[1]
TRADE_STAGE_DIR = ROOT / "_audit" / "Nitrogen-Surplus-restructuring" / "outputs" / "generated" / "trade_stage"
FIG_DIR = ROOT / "figures" / "manuscript_final"
OUT_DIR = ROOT / "data" / "generated" / "si_s5_original_trade_network"

PANEL_A_PNG = FIG_DIR / "si_s5_original_alt_trade_network_clean.png"
PANEL_A_PDF = FIG_DIR / "si_s5_original_alt_trade_network_clean.pdf"
PANEL_B_PNG = FIG_DIR / "si_s5_original_rice_wheat_trade_network_clean.png"
PANEL_B_PDF = FIG_DIR / "si_s5_original_rice_wheat_trade_network_clean.pdf"
COMPOSITE_PNG = FIG_DIR / "si_s5_original_trade_network_clean.png"
COMPOSITE_PDF = FIG_DIR / "si_s5_original_trade_network_clean.pdf"

MASTER_ORDER = [
    "west bengal",
    "andhra pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "delhi",
    "gujarat",
    "haryana",
    "jharkhand",
    "jammu and kashmir",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
]

STATE_ABBREV = {
    "andhra pradesh": "AP",
    "assam": "AS",
    "bihar": "BR",
    "chhattisgarh": "CH",
    "delhi": "DL",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "jammu and kashmir": "JK",
    "jharkhand": "JH",
    "karnataka": "KA",
    "kerala": "KL",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "mizoram": "MZ",
    "nagaland": "NL",
    "odisha": "OD",
    "punjab": "PN",
    "rajasthan": "RJ",
    "tamil nadu": "TN",
    "telangana": "TE",
    "tripura": "TR",
    "uttar pradesh": "UP",
    "uttarakhand": "UR",
    "west bengal": "WB",
}

STATE_COLORS = {
    "WB": "#555555",
    "AP": "#d94b4b",
    "AS": "#33b680",
    "BR": "#c89a12",
    "CH": "#8e6969",
    "DL": "#6f7b86",
    "GJ": "#d73f58",
    "HR": "#2f74da",
    "JH": "#8f66c7",
    "JK": "#b5992b",
    "KA": "#bf8d17",
    "KL": "#1fa8a6",
    "MP": "#9aa317",
    "MH": "#d97a18",
    "MZ": "#6e7f2d",
    "NL": "#5d6a63",
    "OD": "#2f76cf",
    "PN": "#a85ad4",
    "RJ": "#7a5f5f",
    "TN": "#8b6767",
    "TE": "#869420",
    "TR": "#9a6420",
    "UP": "#70aef2",
    "UR": "#7fb221",
}

RICE_KCAL_PER_QTL = 356000.0
WHEAT_KCAL_PER_QTL = 322000.0


def normalize_state(name: str) -> str:
    value = str(name).strip().lower()
    mapping = {
        "andaman & nicobar islands": "andaman and nicobar",
        "chattisgarh": "chhattisgarh",
        "dadra & nagar haveli": "dadra and nagar haveli",
        "daman & diu": "daman and diu",
        "jammu & kashmir": "jammu and kashmir",
        "jammu and kasmir": "jammu and kashmir",
        "orissa": "odisha",
        "pondicherry": "puducherry",
        "rajashthan": "rajasthan",
        "rajashtan": "rajasthan",
        "uttaranchal": "uttarakhand",
    }
    return mapping.get(value, value)


def abbreviate(state: str) -> str:
    return STATE_ABBREV.get(state, state[:2].upper())


def darken_hex(color: str, factor: float = 0.88) -> str:
    rgb = np.array(to_rgb(color), dtype=float)
    return to_hex(np.clip(rgb * factor, 0.0, 1.0))


def load_alt_edges() -> pd.DataFrame:
    frames = [
        pd.read_csv(TRADE_STAGE_DIR / "jowar_bajra_mean_kcal_2016_2018.csv"),
        pd.read_csv(TRADE_STAGE_DIR / "millet_maize_mean_kcal_2016_2018.csv"),
    ]
    raw = pd.concat(frames, ignore_index=True)
    raw["source_state"] = raw["Source"].map(normalize_state)
    raw["target_state"] = raw["Target"].map(normalize_state)
    edges = (
        raw.loc[raw["source_state"] != raw["target_state"]]
        .groupby(["source_state", "target_state"], as_index=False)["quantity_kcal"]
        .sum()
        .rename(columns={"quantity_kcal": "trade_kcal"})
    )
    return edges.loc[edges["trade_kcal"] > 0].reset_index(drop=True)


def load_rice_wheat_edges() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for crop, filename, kcal_per_qtl in (
        ("rice", "rice_trade_normalized.csv", RICE_KCAL_PER_QTL),
        ("wheat", "wheat_trade_normalized.csv", WHEAT_KCAL_PER_QTL),
    ):
        trade = pd.read_csv(TRADE_STAGE_DIR / filename)
        trade["source_state"] = trade["source"].map(normalize_state)
        trade["target_state"] = trade["target"].map(normalize_state)
        trade = trade.loc[trade["source_state"] != trade["target_state"]].copy()
        trade["crop"] = crop
        trade["trade_kcal"] = trade["avg_trade_qt_2017"].astype(float) * kcal_per_qtl
        frames.append(trade[["crop", "source_state", "target_state", "trade_kcal"]])
    crop_edges = pd.concat(frames, ignore_index=True)
    return (
        crop_edges.groupby(["source_state", "target_state"], as_index=False)["trade_kcal"]
        .sum()
        .loc[lambda df: df["trade_kcal"] > 0]
        .reset_index(drop=True)
    )


def node_flow_table(edges: pd.DataFrame) -> pd.DataFrame:
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
    return flow.groupby("State", as_index=False)["flow"].sum().sort_values("flow", ascending=False).reset_index(drop=True)


def select_states(edges: pd.DataFrame, max_states: int) -> list[str]:
    flows = node_flow_table(edges)
    chosen = flows.loc[flows["flow"] > 0, "State"].head(max_states).tolist()
    order_rank = {state: idx for idx, state in enumerate(MASTER_ORDER)}
    return sorted(
        chosen,
        key=lambda state: (order_rank.get(state, 999), -float(flows.loc[flows["State"] == state, "flow"].iloc[0])),
    )


def build_matrix(edges: pd.DataFrame, states: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered = edges.loc[edges["source_state"].isin(states) & edges["target_state"].isin(states)].copy()
    filtered["from"] = filtered["source_state"].map(abbreviate)
    filtered["to"] = filtered["target_state"].map(abbreviate)
    filtered = filtered[["from", "to", "trade_kcal"]].rename(columns={"trade_kcal": "value"})
    ordered_labels = [abbreviate(state) for state in states]
    matrix = Matrix.parse_fromto_table(filtered, order=ordered_labels).dataframe
    return filtered, matrix


def draw_chord_panel(matrix: pd.DataFrame, *, states: list[str], out_png: Path, out_pdf: Path) -> None:
    label_order = [abbreviate(state) for state in states]
    color_map = {abbr: darken_hex(STATE_COLORS.get(abbr, "#888888"), 0.88) for abbr in label_order}
    circos = Circos.chord_diagram(
        matrix,
        start=-90,
        end=270,
        space=4,
        endspace=False,
        cmap=color_map,
        label_kws={"r": 102, "size": 10.3, "color": "#111111"},
        link_kws={
            "alpha": 0.62,
            "direction": 1,
            "arrow_length_ratio": 0.11,
            "ec": "#ffffff",
            "lw": 0.18,
        },
    )
    fig = circos.plotfig(figsize=(8.8, 8.8), dpi=320)
    for ax in fig.axes:
        for text in ax.texts:
            text.set_fontweight("bold")
            text.set_fontsize(11)
            text.set_color("#111111")
    fig.savefig(out_png, dpi=320, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def crop_white_margins(image: np.ndarray, *, threshold: float = 0.985, pad_px: int = 8) -> np.ndarray:
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


def assemble_composite() -> None:
    panel_a = crop_white_margins(mpimg.imread(PANEL_A_PNG), pad_px=12)
    panel_b = crop_white_margins(mpimg.imread(PANEL_B_PNG), pad_px=12)
    fig, axes = plt.subplots(1, 2, figsize=(14.8, 7.0), dpi=320)
    for ax, image, label, title in (
        (axes[0], panel_a, "a", "Alternative cereals"),
        (axes[1], panel_b, "b", "Rice and wheat"),
    ):
        ax.imshow(image)
        ax.axis("off")
        ax.text(0.01, 0.99, label, transform=ax.transAxes, fontsize=15, fontweight="bold", va="top", ha="left")
        ax.set_title(title, fontsize=12.5, fontweight="bold", pad=4)
    fig.subplots_adjust(left=0.015, right=0.99, top=0.94, bottom=0.02, wspace=0.03)
    fig.savefig(COMPOSITE_PNG, dpi=320, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(COMPOSITE_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    alt_edges = load_alt_edges()
    rw_edges = load_rice_wheat_edges()
    alt_states = select_states(alt_edges, max_states=18)
    rw_states = select_states(rw_edges, max_states=20)
    alt_fromto, alt_matrix = build_matrix(alt_edges, alt_states)
    rw_fromto, rw_matrix = build_matrix(rw_edges, rw_states)

    draw_chord_panel(alt_matrix, states=alt_states, out_png=PANEL_A_PNG, out_pdf=PANEL_A_PDF)
    draw_chord_panel(rw_matrix, states=rw_states, out_png=PANEL_B_PNG, out_pdf=PANEL_B_PDF)
    assemble_composite()

    alt_edges.to_csv(OUT_DIR / "si_s5_original_alt_trade_edges.csv", index=False)
    rw_edges.to_csv(OUT_DIR / "si_s5_original_rice_wheat_trade_edges.csv", index=False)
    alt_fromto.to_csv(OUT_DIR / "si_s5_original_alt_trade_fromto_displayed.csv", index=False)
    rw_fromto.to_csv(OUT_DIR / "si_s5_original_rice_wheat_trade_fromto_displayed.csv", index=False)
    (OUT_DIR / "si_s5_original_trade_network_manifest.md").write_text(
        "\n".join(
            [
                "# Supplementary Figure S5 original trade network",
                "",
                "Generated from DGCIS interstate cereal trade inputs averaged over 2016-2018.",
                "Panel a combines jowar, bajra, maize, and ragi in kilocalories.",
                "Panel b combines rice and wheat in kilocalories.",
                f"Panel a displayed states: {', '.join(alt_states)}.",
                f"Panel b displayed states: {', '.join(rw_states)}.",
            ]
        )
        + "\n"
    )
    print(f"figure_pdf: {COMPOSITE_PDF}")
    print(f"figure_png: {COMPOSITE_PNG}")


if __name__ == "__main__":
    main()
