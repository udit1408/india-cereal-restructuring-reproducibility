#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pycirclize import Circos
from pycirclize.parser import Matrix


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated" / "figure3_trade_networks"

sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _build_season_context  # noqa: E402


OPTIMIZED_AREA_PATH = (
    ROOT
    / "data"
    / "generated"
    / "figure2d_no_historical_cap_core"
    / "figure2d_no_historical_cap_core_optimized_areas.csv"
)
TRADE_STAGE_DIR = AUDIT_ROOT / "outputs" / "generated" / "trade_stage"

SEASON_NOTEBOOKS = {
    "kharif": "kharif_nitrogen_min.ipynb",
    "rabi": "rabi__nitrogen_kharif_cop.ipynb",
}

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

STATE_ABBR = {
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
    "WB": "#6b6b6b",
    "AP": "#ff6b6b",
    "AS": "#62d2a2",
    "BR": "#e0b52a",
    "CH": "#aa7c7c",
    "DL": "#9aa4ad",
    "GJ": "#ff5d73",
    "HR": "#4d93ff",
    "JH": "#b78aed",
    "JK": "#e1c24a",
    "KA": "#d8aa2f",
    "KL": "#34c9c7",
    "MP": "#b8bb2b",
    "MH": "#ff9436",
    "MZ": "#9ea345",
    "NL": "#7d8d85",
    "OD": "#3e88e8",
    "PN": "#ca85f5",
    "RJ": "#9c7e7e",
    "TN": "#a37a7a",
    "TE": "#a7b232",
    "TR": "#b2762f",
    "UP": "#8ec2ff",
    "UR": "#9ac638",
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


def build_contexts() -> dict[str, dict[str, object]]:
    layout = default_layout(AUDIT_ROOT)
    contexts: dict[str, dict[str, object]] = {}
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            contexts[season] = _build_season_context(layout, season, notebook_name)
    return contexts


def build_clean_state_crop_production(contexts: dict[str, dict[str, object]]) -> tuple[pd.DataFrame, int]:
    areas = pd.read_csv(OPTIMIZED_AREA_PATH)
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


def select_states(node_flows: pd.DataFrame, max_states: int = 20) -> list[str]:
    chosen = node_flows.loc[node_flows["flow"] > 0, "State"].head(max_states).tolist()
    order_rank = {state: idx for idx, state in enumerate(MASTER_ORDER)}
    return sorted(chosen, key=lambda state: (order_rank.get(state, 999), -float(node_flows.loc[node_flows["State"] == state, "flow"].iloc[0])))


def abbreviate(state: str) -> str:
    return STATE_ABBR.get(state, state[:2].upper())


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


def draw_chord_panel(
    matrix: pd.DataFrame,
    *,
    states: list[str],
    title: str | None,
    out_png: Path,
    out_pdf: Path,
) -> None:
    label_order = [abbreviate(state) for state in states]
    color_map = {abbr: STATE_COLORS.get(abbr, "#999999") for abbr in label_order}
    circos = Circos.chord_diagram(
        matrix,
        start=-90,
        end=270,
        space=4,
        endspace=False,
        cmap=color_map,
        label_kws={"r": 110, "size": 11},
        link_kws={"alpha": 0.42, "ec": "none", "lw": 0.0},
    )
    fig = circos.plotfig(figsize=(8.2, 8.2), dpi=300)
    if title:
        ax = fig.axes[0]
        ax.set_title(title, fontsize=14, pad=12)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def build_audit_text(
    missing_keys: int,
    alt_states: list[str],
    rw_states: list[str],
    alt_summary: pd.DataFrame,
) -> str:
    negative_states = alt_summary.loc[alt_summary["trade_alt_needed_raw"] < 0, "State"].tolist()
    lines = [
        "# Figure 3 trade-network rebuild",
        "",
        "This rebuild aligns Figure 3(b) and Figure 3(c) to the same approved nitrogen-focused",
        "optimization branch used for the revised Figure 2(d): fixed district cropped area,",
        "substitution among historically observed cereals, and the shared state calorie and",
        "MSP-benchmarked income floors.",
        "",
        "District-crop optimized production is reconstructed from the approved optimized-area table",
        "using notebook-derived district yield and calorie coefficients, with historical-but-missing",
        "district-crop options completed from state-crop and crop-level means before reconstruction.",
        "",
        f"District-crop combinations still unresolved after coefficient completion: {missing_keys}",
        "",
        "For Figure 3(c), interstate rice and wheat flows are rebuilt by scaling each source state's",
        "2016-2018 average trade links in proportion to the change in that source state's optimized",
        "versus baseline production for the corresponding crop. Same-state flows are excluded.",
        "",
        "For Figure 3(b), baseline interstate alternate-cereal links (maize, ragi, bajra, jowar)",
        "are preserved as the network topology. Source-wise optimized alternate trade is then scaled",
        "from that baseline using:",
        "",
        "optimized alternate trade = baseline alternate trade + alternate-calorie surplus +",
        "change in rice+wheat interstate trade from the same source state.",
        "",
        "Negative source totals are clipped to zero to avoid implying negative exports. Source states",
        "with no baseline alternate-trade links are not assigned new destinations in this figure,",
        "because the panel is intended as a conservative network rescaling rather than a new trade-allocation model.",
        "",
        f"Figure 3(b) displayed states: {', '.join(alt_states)}.",
        f"Figure 3(c) displayed states: {', '.join(rw_states)}.",
        "",
        f"Alternate-network source states clipped to zero after the raw trade update: {', '.join(negative_states) if negative_states else 'none'}.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    contexts = build_contexts()
    state_crop, missing_keys = build_clean_state_crop_production(contexts)
    rw_crop_edges, rw_edges, rw_source_summary = build_rice_wheat_edges(state_crop)
    alt_baseline_edges, alt_summary, alt_edges = build_alternative_edges(state_crop, rw_source_summary)

    alt_node_flows = node_flow_table(alt_edges.rename(columns={"optimized_trade_kcal": "value"}), "value")
    rw_node_flows = node_flow_table(rw_edges.rename(columns={"optimized_trade_kcal": "value"}), "value")
    alt_states = select_states(alt_node_flows, max_states=18)
    rw_states = select_states(rw_node_flows, max_states=20)

    alt_fromto, alt_matrix = build_matrix(alt_edges, "optimized_trade_kcal", alt_states)
    rw_fromto, rw_matrix = build_matrix(rw_edges, "optimized_trade_kcal", rw_states)

    draw_chord_panel(
        alt_matrix,
        states=alt_states,
        title=None,
        out_png=FIG_DIR / "figure3b_alt_trade_network_clean.png",
        out_pdf=FIG_DIR / "figure3b_alt_trade_network_clean.pdf",
    )
    draw_chord_panel(
        rw_matrix,
        states=rw_states,
        title=None,
        out_png=FIG_DIR / "figure3c_rice_wheat_trade_network_clean.png",
        out_pdf=FIG_DIR / "figure3c_rice_wheat_trade_network_clean.pdf",
    )

    state_crop.to_csv(DATA_DIR / "figure3_trade_state_crop_production_clean.csv", index=False)
    rw_crop_edges.to_csv(DATA_DIR / "figure3c_rice_wheat_trade_edges_by_crop_clean.csv", index=False)
    rw_edges.to_csv(DATA_DIR / "figure3c_rice_wheat_trade_edges_clean.csv", index=False)
    rw_source_summary.to_csv(DATA_DIR / "figure3c_rice_wheat_source_summary_clean.csv", index=False)
    rw_node_flows.to_csv(DATA_DIR / "figure3c_rice_wheat_node_flows_clean.csv", index=False)
    rw_fromto.to_csv(DATA_DIR / "figure3c_rice_wheat_fromto_clean.csv", index=False)
    alt_baseline_edges.to_csv(DATA_DIR / "figure3b_alt_trade_edges_baseline_clean.csv", index=False)
    alt_summary.to_csv(DATA_DIR / "figure3b_alt_trade_source_summary_clean.csv", index=False)
    alt_edges.to_csv(DATA_DIR / "figure3b_alt_trade_edges_clean.csv", index=False)
    alt_node_flows.to_csv(DATA_DIR / "figure3b_alt_node_flows_clean.csv", index=False)
    alt_fromto.to_csv(DATA_DIR / "figure3b_alt_fromto_clean.csv", index=False)
    (DATA_DIR / "figure3_trade_networks_audit.md").write_text(
        build_audit_text(missing_keys, alt_states, rw_states, alt_summary) + "\n"
    )


if __name__ == "__main__":
    main()
