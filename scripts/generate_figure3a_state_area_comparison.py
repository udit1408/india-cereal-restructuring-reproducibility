#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated" / "figure3a_state_area_comparison"
INPUT_CSV = (
    ROOT
    / "data"
    / "generated"
    / "figure2d_no_historical_cap_core"
    / "figure2d_no_historical_cap_core_optimized_areas.csv"
)

OUT_PNG = FIG_DIR / "figure3a_state_area_comparison.png"
OUT_PDF = FIG_DIR / "figure3a_state_area_comparison.pdf"
OUT_ALL_STATES = DATA_DIR / "figure3a_state_area_comparison_all_states.csv"
OUT_DISPLAY = DATA_DIR / "figure3a_state_area_comparison_display_states.csv"
OUT_AUDIT = DATA_DIR / "figure3a_state_area_comparison_audit.md"


def _relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


CROP_ORDER = ["bajra", "jowar", "maize", "ragi", "rice", "wheat"]
CROP_COLORS = {
    "bajra": "#d9655d",
    "jowar": "#d4df66",
    "maize": "#67d85d",
    "ragi": "#63cbd3",
    "rice": "#6358d8",
    "wheat": "#d65ad4",
}

STATE_ABBREV = {
    "andhra pradesh": "AP",
    "assam": "AS",
    "bihar": "BR",
    "chhattisgarh": "CH",
    "gujarat": "GJ",
    "haryana": "HR",
    "karnataka": "KA",
    "maharashtra": "MH",
    "madhya pradesh": "MP",
    "odisha": "OD",
    "punjab": "PN",
    "rajasthan": "RJ",
    "tamil nadu": "TN",
    "uttar pradesh": "UP",
    "west bengal": "WB",
}

# The current manuscript panel displays these 15 states. We keep the same set
# and order here so panel-by-panel comparison stays exact while the figure is rebuilt.
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


def load_area_frame() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    return df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")].copy()


def build_state_crop_totals(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["State", "Crop"], as_index=False)[
            ["Original Area (Hectare)", "Optimized Area (Hectare)"]
        ]
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


def state_total_audit(df: pd.DataFrame) -> pd.DataFrame:
    totals = (
        df.groupby("State", as_index=False)[["original_area_ha", "optimized_area_ha"]]
        .sum()
        .rename(columns={"State": "state"})
    )
    totals["delta_ha"] = totals["optimized_area_ha"] - totals["original_area_ha"]
    totals["abs_delta_ha"] = totals["delta_ha"].abs()
    return totals.sort_values("original_area_ha", ascending=False).reset_index(drop=True)


def plot_panel(display: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

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

    fig, ax = plt.subplots(figsize=(10.6, 6.05), dpi=300)
    ax.set_facecolor("white")
    ax.grid(axis="x", linestyle="--", linewidth=0.8, color="#d9dde5", alpha=0.85)
    ax.set_axisbelow(True)

    original_left = [0.0 for _ in states]
    optimized_left = [0.0 for _ in states]

    for crop in CROP_ORDER:
        original = [float(original_pivot.loc[state, crop]) for state in states]
        optimized = [float(optimized_pivot.loc[state, crop]) for state in states]

        ax.barh(
            y_positions,
            [-value for value in original],
            left=original_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.4,
            height=0.55,
            label=crop,
        )
        ax.barh(
            y_positions,
            optimized,
            left=optimized_left,
            color=CROP_COLORS[crop],
            edgecolor="white",
            linewidth=0.4,
            height=0.55,
        )

        original_left = [left - value for left, value in zip(original_left, original)]
        optimized_left = [left + value for left, value in zip(optimized_left, optimized)]

    max_extent = max(max(abs(value) for value in original_left), max(optimized_left))
    ax.axvline(0.0, color="black", linewidth=1.2)
    ax.set_xlim(-max_extent * 1.09, max_extent * 1.09)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(state_labels)
    ax.invert_yaxis()

    ax.set_xlabel("Area (Hectare)")
    ax.text(0.16, 0.08, "Original Area", transform=ax.transAxes, ha="center", va="center", fontsize=10)
    ax.text(0.79, 0.08, "Optimized Area", transform=ax.transAxes, ha="center", va="center", fontsize=10)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=CROP_COLORS[crop], edgecolor="white", linewidth=0.4)
        for crop in CROP_ORDER
    ]
    ax.legend(
        legend_handles,
        CROP_ORDER,
        loc="lower right",
        frameon=True,
        framealpha=0.9,
        edgecolor="#d3d7de",
        fontsize=8.5,
    )

    fig.tight_layout(pad=0.6)
    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)


def build_audit_text(display: pd.DataFrame, totals: pd.DataFrame) -> str:
    display_totals = totals[totals["state"].isin(DISPLAY_STATE_ORDER)].copy()
    max_abs_delta = float(display_totals["abs_delta_ha"].max())
    top15 = totals.head(15)["state"].tolist()
    missing_from_top15 = [state for state in DISPLAY_STATE_ORDER if state not in top15]
    top15_not_shown = [state for state in top15 if state not in DISPLAY_STATE_ORDER]

    lines = [
        "# Figure 3(a) state-area comparison rebuild",
        "",
        "This panel is rebuilt from the approved nitrogen-focused optimization branch already",
        "used for the revised Figure 2(d): fixed district cropped area, substitution among",
        "historically observed cereals, and the shared state calorie and MSP-benchmarked",
        "income floors.",
        "",
        f"Input table: `{_relpath(INPUT_CSV)}`",
        "",
        "The displayed panel follows the state subset and order shown in the current manuscript",
        "Figure 3(a): WB, UP, TN, RJ, PN, OD, MP, MH, KA, HR, GJ, CH, BR, AS, AP.",
        "",
        f"Displayed-state maximum absolute original-versus-optimized total-area residual: {max_abs_delta:.6e} ha",
        "",
        "Top 15 states by baseline cereal area in the clean rebuild:",
        f"- {', '.join(top15)}",
        "",
        "Legacy-display states that are not in that top-15-by-baseline ranking:",
        f"- {', '.join(missing_from_top15) if missing_from_top15 else 'none'}",
        "",
        "Top-15-by-baseline states omitted from the current manuscript panel:",
        f"- {', '.join(top15_not_shown) if top15_not_shown else 'none'}",
        "",
        "This means the current panel should be treated as a displayed-state comparison rather than",
        "as a strict top-15 ranking. The plotted state totals themselves are rebuilt directly from the",
        "clean district-level optimization output.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    area_frame = load_area_frame()
    state_crop = build_state_crop_totals(area_frame)
    display = build_display_frame(state_crop)
    totals = state_total_audit(state_crop)

    state_crop.to_csv(OUT_ALL_STATES, index=False)
    display.to_csv(OUT_DISPLAY, index=False)
    OUT_AUDIT.write_text(build_audit_text(display, totals))
    plot_panel(display)


if __name__ == "__main__":
    main()
