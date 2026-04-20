#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
import types
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
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "working_variants"
OUT_DIR = ROOT / "data" / "generated" / "figure3_main"
TRADE_STAGE_DIR = AUDIT_ROOT / "outputs" / "generated" / "trade_stage"
OPTIMIZED_AREA_PATH = (
    ROOT
    / "data"
    / "generated"
    / "figure2_main"
    / "figure2_main_panel_d_optimized_areas.csv"
)


def _relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _ensure_geopandas_stub() -> None:
    if "geopandas" not in sys.modules:
        sys.modules["geopandas"] = types.ModuleType("geopandas")


_ensure_geopandas_stub()
sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _build_season_context  # noqa: E402


SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}

PANEL_A_PNG = FIG_DIR / "figure3_main_panel_a.png"
PANEL_A_PDF = FIG_DIR / "figure3_main_panel_a.pdf"
PANEL_B_PNG = FIG_DIR / "figure3_main_panel_b.png"
PANEL_B_PDF = FIG_DIR / "figure3_main_panel_b.pdf"
PANEL_C_PNG = FIG_DIR / "figure3_main_panel_c.png"
PANEL_C_PDF = FIG_DIR / "figure3_main_panel_c.pdf"
COMPOSITE_PNG = FIG_DIR / "figure3_main.png"
COMPOSITE_PDF = FIG_DIR / "figure3_main.pdf"
MANIFEST_MD = OUT_DIR / "figure3_main_manifest.md"
AUDIT_MD = OUT_DIR / "figure3_main_audit.md"

CROP_ORDER = ["bajra", "jowar", "maize", "ragi", "rice", "wheat"]
CROP_COLORS = {
    "bajra": "#c54b3c",
    "jowar": "#b3be39",
    "maize": "#39ad39",
    "ragi": "#2e99a3",
    "rice": "#4d47c1",
    "wheat": "#b846b2",
}

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

DISPLAY_STATE_ORDER = [
    "west bengal",
    "uttar pradesh",
    "tamil nadu",
    "rajasthan",
    "punjab",
    "odisha",
    "madhya pradesh",
    "maharashtra",
    "karnataka",
    "haryana",
    "gujarat",
    "chhattisgarh",
    "bihar",
    "assam",
    "andhra pradesh",
]

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


def darken_hex(color: str, factor: float = 0.82) -> str:
    rgb = np.array(to_rgb(color), dtype=float)
    return to_hex(np.clip(rgb * factor, 0.0, 1.0))


def build_contexts() -> dict[str, dict[str, object]]:
    layout = default_layout(AUDIT_ROOT)
    contexts: dict[str, dict[str, object]] = {}
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            contexts[season] = _build_season_context(layout, season, notebook_name)
    return contexts


def load_area_frame() -> pd.DataFrame:
    df = pd.read_csv(OPTIMIZED_AREA_PATH)
    return df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")].copy()


def build_state_crop_totals(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["State", "Crop"], as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_area_ha",
                "Optimized Area (Hectare)": "optimized_area_ha",
            }
        )
    )
    grouped["state_abbrev"] = grouped["State"].map(STATE_ABBREV)
    grouped["crop_order"] = grouped["Crop"].map({crop: idx for idx, crop in enumerate(CROP_ORDER)})
    return grouped.sort_values(["State", "crop_order"]).reset_index(drop=True)


def build_display_frame(state_crop: pd.DataFrame) -> pd.DataFrame:
    display = state_crop[state_crop["State"].isin(DISPLAY_STATE_ORDER)].copy()
    display["state_order"] = display["State"].map({state: idx for idx, state in enumerate(DISPLAY_STATE_ORDER)})
    return display.sort_values(["state_order", "crop_order"]).reset_index(drop=True)


def plot_panel_a(display: pd.DataFrame) -> None:
    states = DISPLAY_STATE_ORDER
    state_labels = [STATE_ABBREV[state] for state in states]
    y_positions = list(range(len(states)))
    original_pivot = (
        display.pivot_table(
            index="State",
            columns="Crop",
            values="original_area_ha",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(index=states, columns=CROP_ORDER, fill_value=0.0)
    )
    optimized_pivot = (
        display.pivot_table(
            index="State",
            columns="Crop",
            values="optimized_area_ha",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(index=states, columns=CROP_ORDER, fill_value=0.0)
    )

    fig, ax = plt.subplots(figsize=(10.7, 6.0), dpi=320)
    ax.set_facecolor("white")
    ax.grid(axis="x", linestyle="--", linewidth=0.75, color="#d5dae4", alpha=0.9)
    ax.set_axisbelow(True)

    original_left = [0.0 for _ in states]
    optimized_left = [0.0 for _ in states]
    for crop in CROP_ORDER:
        original = [float(original_pivot.loc[state, crop]) / 1e6 for state in states]
        optimized = [float(optimized_pivot.loc[state, crop]) / 1e6 for state in states]
        ax.barh(
            y_positions,
            [-value for value in original],
            left=original_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.4,
            height=0.56,
        )
        ax.barh(
            y_positions,
            optimized,
            left=optimized_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.4,
            height=0.56,
        )
        original_left = [left - value for left, value in zip(original_left, original)]
        optimized_left = [left + value for left, value in zip(optimized_left, optimized)]

    max_extent = max(max(abs(value) for value in original_left), max(optimized_left))
    ax.axvline(0.0, color="black", linewidth=1.2)
    ax.set_xlim(-max_extent * 1.08, max_extent * 1.08)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(state_labels, fontsize=9, fontweight="bold")
    ax.invert_yaxis()
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("Area (Mha)", fontsize=10, fontweight="bold")
    ax.text(0.17, 0.08, "Original Area", transform=ax.transAxes, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(0.79, 0.08, "Optimized Area", transform=ax.transAxes, ha="center", va="center", fontsize=10, fontweight="bold")

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=CROP_COLORS[crop], edgecolor="white", linewidth=0.4)
        for crop in CROP_ORDER
    ]
    ax.legend(
        legend_handles,
        CROP_ORDER,
        loc="lower right",
        frameon=True,
        framealpha=0.96,
        edgecolor="#d3d7de",
        fontsize=10.0,
        handlelength=1.85,
        borderpad=0.5,
        labelspacing=0.42,
    )

    fig.tight_layout(pad=0.45)
    fig.savefig(PANEL_A_PNG, bbox_inches="tight", facecolor="white")
    fig.savefig(PANEL_A_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_clean_state_crop_production(
    contexts: dict[str, dict[str, object]],
) -> tuple[pd.DataFrame, int]:
    areas = load_area_frame()
    rows: list[dict[str, float | str]] = []
    missing_keys = 0
    for _, row in areas.iterrows():
        season = str(row["season"])
        state = str(row["State"])
        district = str(row["District"])
        crop = str(row["Crop"])
        key = (state, district, crop)
        yield_kg_ha = float(contexts[season]["yield_data"].get(key, 0.0))
        kcal_per_kg = float(contexts[season]["calories_per_prod"].get(key, 0.0))
        if yield_kg_ha == 0.0 or kcal_per_kg == 0.0:
            missing_keys += 1
        original_area = float(row["Original Area (Hectare)"])
        optimized_area = float(row["Optimized Area (Hectare)"])
        rows.append(
            {
                "season": season,
                "State": state,
                "District": district,
                "Crop": crop,
                "yield_kg_ha": yield_kg_ha,
                "kcal_per_kg": kcal_per_kg,
                "Original Area (Hectare)": original_area,
                "Optimized Area (Hectare)": optimized_area,
                "Original production kg": original_area * yield_kg_ha,
                "Optimized production kg": optimized_area * yield_kg_ha,
                "Original calorie": original_area * yield_kg_ha * kcal_per_kg,
                "Optimized calorie": optimized_area * yield_kg_ha * kcal_per_kg,
            }
        )
    district_crop = pd.DataFrame(rows)
    state_crop = (
        district_crop.groupby(["State", "Crop"], as_index=False)[
            [
                "Original Area (Hectare)",
                "Optimized Area (Hectare)",
                "Original production kg",
                "Optimized production kg",
                "Original calorie",
                "Optimized calorie",
            ]
        ]
        .sum()
        .sort_values(["State", "Crop"])
        .reset_index(drop=True)
    )
    return state_crop, missing_keys


def build_rice_wheat_edges(state_crop: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lookup = state_crop.set_index(["State", "Crop"])
    edge_frames: list[pd.DataFrame] = []
    for crop, filename, kcal_per_qtl in (
        ("rice", "rice_trade_normalized.csv", RICE_KCAL_PER_QTL),
        ("wheat", "wheat_trade_normalized.csv", WHEAT_KCAL_PER_QTL),
    ):
        trade = pd.read_csv(TRADE_STAGE_DIR / filename)
        trade["source_state"] = trade["source"].map(normalize_state)
        trade["target_state"] = trade["target"].map(normalize_state)
        trade = trade.loc[trade["source_state"] != trade["target_state"]].copy()
        original_prod = trade["source_state"].map(
            lambda state: float(lookup["Original production kg"].get((state, crop), 0.0))
        )
        optimized_prod = trade["source_state"].map(
            lambda state: float(lookup["Optimized production kg"].get((state, crop), 0.0))
        )
        ratio = (optimized_prod / original_prod.replace(0, pd.NA)).fillna(0.0)
        trade["crop"] = crop
        trade["original_trade_qtl"] = trade["avg_trade_qt_2017"].astype(float)
        trade["optimized_trade_qtl"] = trade["original_trade_qtl"] * ratio
        trade["original_trade_kcal"] = trade["original_trade_qtl"] * kcal_per_qtl
        trade["optimized_trade_kcal"] = trade["optimized_trade_qtl"] * kcal_per_qtl
        trade["diff_trade_kcal"] = trade["optimized_trade_kcal"] - trade["original_trade_kcal"]
        edge_frames.append(
            trade[
                [
                    "crop",
                    "source_state",
                    "target_state",
                    "original_trade_qtl",
                    "optimized_trade_qtl",
                    "original_trade_kcal",
                    "optimized_trade_kcal",
                    "diff_trade_kcal",
                ]
            ]
        )
    crop_level = pd.concat(edge_frames, ignore_index=True)
    combined = (
        crop_level.groupby(["source_state", "target_state"], as_index=False)[
            ["original_trade_kcal", "optimized_trade_kcal", "diff_trade_kcal"]
        ]
        .sum()
        .sort_values(["source_state", "target_state"])
        .reset_index(drop=True)
    )
    source_summary = (
        crop_level.groupby("source_state", as_index=False)[
            ["original_trade_kcal", "optimized_trade_kcal", "diff_trade_kcal"]
        ]
        .sum()
        .rename(
            columns={
                "source_state": "State",
                "original_trade_kcal": "original_rw_trade_kcal",
                "optimized_trade_kcal": "optimized_rw_trade_kcal",
                "diff_trade_kcal": "diff_rw_trade_kcal",
            }
        )
        .sort_values("optimized_rw_trade_kcal", ascending=False)
        .reset_index(drop=True)
    )
    return crop_level, combined, source_summary


def build_alternative_edges(
    state_crop: pd.DataFrame,
    rw_source_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    alt_raw = pd.concat(
        [
            pd.read_csv(TRADE_STAGE_DIR / "jowar_bajra_mean_kcal_2016_2018.csv"),
            pd.read_csv(TRADE_STAGE_DIR / "millet_maize_mean_kcal_2016_2018.csv"),
        ],
        ignore_index=True,
    )
    alt_raw["source_state"] = alt_raw["Source"].map(normalize_state)
    alt_raw["target_state"] = alt_raw["Target"].map(normalize_state)
    alt_raw = alt_raw.loc[alt_raw["source_state"] != alt_raw["target_state"]].copy()
    baseline_edges = (
        alt_raw.groupby(["source_state", "target_state"], as_index=False)["quantity_kcal"]
        .sum()
        .sort_values(["source_state", "target_state"])
        .reset_index(drop=True)
    )
    baseline_source = (
        baseline_edges.groupby("source_state", as_index=False)["quantity_kcal"]
        .sum()
        .rename(columns={"source_state": "State", "quantity_kcal": "original_alt_trade_kcal"})
    )
    alt_prod = (
        state_crop.loc[state_crop["Crop"].isin(["bajra", "jowar", "maize", "ragi"])]
        .groupby("State", as_index=False)[["Original calorie", "Optimized calorie"]]
        .sum()
        .rename(
            columns={
                "Original calorie": "original_alt_prod_kcal",
                "Optimized calorie": "optimized_alt_prod_kcal",
            }
        )
    )
    summary = (
        alt_prod.merge(baseline_source, on="State", how="outer")
        .merge(rw_source_summary[["State", "diff_rw_trade_kcal"]], on="State", how="outer")
        .fillna(0.0)
    )
    summary["surplus_alt_kcal"] = summary["optimized_alt_prod_kcal"] - summary["original_alt_prod_kcal"]
    summary["trade_alt_needed_raw"] = (
        summary["original_alt_trade_kcal"] + summary["surplus_alt_kcal"] + summary["diff_rw_trade_kcal"]
    )
    summary["trade_alt_needed_clipped"] = summary["trade_alt_needed_raw"].clip(lower=0.0)

    scaled_edges = baseline_edges.merge(
        summary[["State", "original_alt_trade_kcal", "trade_alt_needed_clipped"]],
        left_on="source_state",
        right_on="State",
        how="left",
    ).fillna(0.0)
    denom = scaled_edges["original_alt_trade_kcal"].to_numpy(dtype=float)
    numer = scaled_edges["trade_alt_needed_clipped"].to_numpy(dtype=float)
    scaled_edges["scale_factor"] = np.divide(
        numer,
        denom,
        out=np.zeros(len(scaled_edges), dtype=float),
        where=denom > 0,
    )
    scaled_edges["optimized_trade_kcal"] = scaled_edges["quantity_kcal"] * scaled_edges["scale_factor"]
    scaled_edges = scaled_edges.sort_values(["source_state", "target_state"]).reset_index(drop=True)
    return baseline_edges, summary.sort_values("trade_alt_needed_clipped", ascending=False), scaled_edges


def node_flow_table(edges: pd.DataFrame, value_col: str) -> pd.DataFrame:
    flow = pd.concat(
        [
            edges.groupby("source_state", as_index=False)[value_col]
            .sum()
            .rename(columns={"source_state": "State", value_col: "flow"}),
            edges.groupby("target_state", as_index=False)[value_col]
            .sum()
            .rename(columns={"target_state": "State", value_col: "flow"}),
        ],
        ignore_index=True,
    )
    return flow.groupby("State", as_index=False)["flow"].sum().sort_values("flow", ascending=False).reset_index(drop=True)


def select_states(node_flows: pd.DataFrame, max_states: int) -> list[str]:
    chosen = node_flows.loc[node_flows["flow"] > 0, "State"].head(max_states).tolist()
    order_rank = {state: idx for idx, state in enumerate(MASTER_ORDER)}
    return sorted(
        chosen,
        key=lambda state: (order_rank.get(state, 999), -float(node_flows.loc[node_flows["State"] == state, "flow"].iloc[0])),
    )


def abbreviate(state: str) -> str:
    return STATE_ABBREV.get(state, state[:2].upper())


def build_matrix(edges: pd.DataFrame, value_col: str, states: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered = edges.loc[
        edges["source_state"].isin(states) & edges["target_state"].isin(states) & (edges[value_col] > 0)
    ].copy()
    filtered["from"] = filtered["source_state"].map(abbreviate)
    filtered["to"] = filtered["target_state"].map(abbreviate)
    filtered = filtered[["from", "to", value_col]].rename(columns={value_col: "value"})
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
    fig = plt.figure(figsize=(13.0, 10.0), dpi=320, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[0.92, 1.0], wspace=0.015, hspace=0.015)
    axes = [
        fig.add_subplot(gs[0, :]),
        fig.add_subplot(gs[1, 0]),
        fig.add_subplot(gs[1, 1]),
    ]
    images = [
        crop_white_margins(mpimg.imread(PANEL_A_PNG), pad_px=6),
        crop_white_margins(mpimg.imread(PANEL_B_PNG), pad_px=8),
        crop_white_margins(mpimg.imread(PANEL_C_PNG), pad_px=8),
    ]
    for ax, image, label in zip(axes, images, ["a", "b", "c"]):
        ax.imshow(image)
        ax.set_axis_off()
        ax.text(
            0.0,
            1.01,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color="black",
        )
    fig.savefig(COMPOSITE_PNG, dpi=320, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(COMPOSITE_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def write_audit(
    display_a: pd.DataFrame,
    alt_states: list[str],
    rw_states: list[str],
    alt_summary: pd.DataFrame,
    missing_keys: int,
) -> None:
    negative_states = alt_summary.loc[alt_summary["trade_alt_needed_raw"] < 0, "State"].tolist()
    lines = [
        "# figure3_main audit",
        "",
        "This standalone Figure 3 rebuild is generated from the primary official price-and-cost",
        "nitrogen-focused optimized area table exported by the final figure2_main workflow.",
        f"Input optimized area table: {_relpath(OPTIMIZED_AREA_PATH)}",
        "",
        "Figure 3(a) keeps the manuscript display-state set and order for panel comparability,",
        "but the stacked original-versus-optimized totals are recomputed from the primary benchmark",
        "optimized district areas.",
        "",
        "Figure 3(b) and Figure 3(c) rebuild optimized state-crop production from those same",
        "district areas using the notebook-derived yield and calorie coefficients, then rescale",
        "the baseline trade links using the same trade-network logic as the clean manuscript rebuild.",
        "",
        f"Unresolved district-crop production keys after coefficient reconstruction: {missing_keys}",
        f"Figure 3(b) displayed states: {', '.join(alt_states)}.",
        f"Figure 3(c) displayed states: {', '.join(rw_states)}.",
        f"Alternate-network source states clipped to zero after the raw trade update: {', '.join(negative_states) if negative_states else 'none'}.",
        "",
        f"Figure 3(a) displayed-state rows: {len(display_a)}.",
    ]
    AUDIT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_manifest() -> None:
    lines = [
        "# figure3_main manifest",
        "",
        "Composite outputs:",
        f"- {_relpath(COMPOSITE_PNG)}",
        f"- {_relpath(COMPOSITE_PDF)}",
        "",
        "Panel outputs:",
        f"- {_relpath(PANEL_A_PNG)}",
        f"- {_relpath(PANEL_A_PDF)}",
        f"- {_relpath(PANEL_B_PNG)}",
        f"- {_relpath(PANEL_B_PDF)}",
        f"- {_relpath(PANEL_C_PNG)}",
        f"- {_relpath(PANEL_C_PDF)}",
        "",
        "Tabular outputs:",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_a_all_states.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_a_display_states.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_state_crop_production.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_b_alt_trade_edges.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_b_alt_node_flows.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_c_rw_trade_edges.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_c_rw_node_flows.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_b_fromto.csv')}",
        f"- {_relpath(OUT_DIR / 'figure3_main_panel_c_fromto.csv')}",
        "",
        "Notes:",
        f"- {_relpath(AUDIT_MD)}",
    ]
    MANIFEST_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    area_frame = load_area_frame()
    state_crop_area = build_state_crop_totals(area_frame)
    display_a = build_display_frame(state_crop_area)
    state_crop_area.to_csv(OUT_DIR / "figure3_main_panel_a_all_states.csv", index=False)
    display_a.to_csv(OUT_DIR / "figure3_main_panel_a_display_states.csv", index=False)
    plot_panel_a(display_a)

    contexts = build_contexts()
    state_crop_production, missing_keys = build_clean_state_crop_production(contexts)
    state_crop_production.to_csv(OUT_DIR / "figure3_main_state_crop_production.csv", index=False)

    rw_crop_edges, rw_edges, rw_source_summary = build_rice_wheat_edges(state_crop_production)
    alt_baseline_edges, alt_summary, alt_edges = build_alternative_edges(state_crop_production, rw_source_summary)

    alt_node_flows = node_flow_table(alt_edges.rename(columns={"optimized_trade_kcal": "value"}), "value")
    rw_node_flows = node_flow_table(rw_edges.rename(columns={"optimized_trade_kcal": "value"}), "value")
    alt_states = select_states(alt_node_flows, max_states=18)
    rw_states = select_states(rw_node_flows, max_states=20)

    alt_fromto, alt_matrix = build_matrix(alt_edges, "optimized_trade_kcal", alt_states)
    rw_fromto, rw_matrix = build_matrix(rw_edges, "optimized_trade_kcal", rw_states)

    draw_chord_panel(alt_matrix, states=alt_states, out_png=PANEL_B_PNG, out_pdf=PANEL_B_PDF)
    draw_chord_panel(rw_matrix, states=rw_states, out_png=PANEL_C_PNG, out_pdf=PANEL_C_PDF)
    assemble_composite()

    rw_crop_edges.to_csv(OUT_DIR / "figure3_main_panel_c_rw_trade_edges_by_crop.csv", index=False)
    rw_edges.to_csv(OUT_DIR / "figure3_main_panel_c_rw_trade_edges.csv", index=False)
    rw_source_summary.to_csv(OUT_DIR / "figure3_main_panel_c_rw_source_summary.csv", index=False)
    rw_node_flows.to_csv(OUT_DIR / "figure3_main_panel_c_rw_node_flows.csv", index=False)
    rw_fromto.to_csv(OUT_DIR / "figure3_main_panel_c_fromto.csv", index=False)
    alt_baseline_edges.to_csv(OUT_DIR / "figure3_main_panel_b_alt_trade_edges_baseline.csv", index=False)
    alt_summary.to_csv(OUT_DIR / "figure3_main_panel_b_alt_source_summary.csv", index=False)
    alt_edges.to_csv(OUT_DIR / "figure3_main_panel_b_alt_trade_edges.csv", index=False)
    alt_node_flows.to_csv(OUT_DIR / "figure3_main_panel_b_alt_node_flows.csv", index=False)
    alt_fromto.to_csv(OUT_DIR / "figure3_main_panel_b_fromto.csv", index=False)

    write_audit(display_a, alt_states, rw_states, alt_summary, missing_keys)
    write_manifest()

    print(f"figure_png: {COMPOSITE_PNG}")
    print(f"figure_pdf: {COMPOSITE_PDF}")
    print(f"audit_md: {AUDIT_MD}")


if __name__ == "__main__":
    main()
