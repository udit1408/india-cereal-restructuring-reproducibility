#!/usr/bin/env python3
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec


ROOT = Path(__file__).resolve().parents[1]
AREA_CSV = (
    ROOT
    / "data"
    / "generated"
    / "Figure2_equivalent"
    / "Figure2_equivalent_panel_d_optimized_areas.csv"
)
OUT_DIR = ROOT / "data" / "generated" / "seasonal_substitution_audit_primary_revenue"
FIG_DIR = ROOT / "figures" / "manuscript_final"
HELPER_PATH = ROOT / "scripts" / "generate_figure2d_clean.py"


def load_helper():
    helper = SourceFileLoader("figure2d_clean_helper", str(HELPER_PATH)).load_module()
    helper.FIG_DIR = FIG_DIR
    return helper


def build_pattern_flags(area: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (season, state, district), group in area.groupby(["season", "State", "District"], sort=True):
        frame = group.set_index("Crop")

        def get(crop: str, column: str) -> float:
            if crop not in frame.index:
                return 0.0
            return float(frame.loc[crop, column])

        rice_original = get("rice", "Original Area (Hectare)")
        rice_optimized = get("rice", "Optimized Area (Hectare)")
        wheat_original = get("wheat", "Original Area (Hectare)")
        wheat_optimized = get("wheat", "Optimized Area (Hectare)")

        rice_loss = max(rice_original - rice_optimized, 0.0)
        rice_gain = max(rice_optimized - rice_original, 0.0)
        wheat_loss = max(wheat_original - wheat_optimized, 0.0)
        wheat_gain = max(wheat_optimized - wheat_original, 0.0)

        if rice_loss > 0.0 and wheat_gain > 0.0:
            rows.append(
                {
                    "season": season,
                    "State": state,
                    "District": district,
                    "pattern": "rice_loss_wheat_gain",
                    "source_loss_ha": rice_loss,
                    "target_gain_ha": wheat_gain,
                    "co_occurring_area_ha": min(rice_loss, wheat_gain),
                    "baseline_rice_ha": rice_original,
                    "baseline_wheat_ha": wheat_original,
                }
            )
        if wheat_loss > 0.0 and rice_gain > 0.0:
            rows.append(
                {
                    "season": season,
                    "State": state,
                    "District": district,
                    "pattern": "wheat_loss_rice_gain",
                    "source_loss_ha": wheat_loss,
                    "target_gain_ha": rice_gain,
                    "co_occurring_area_ha": min(wheat_loss, rice_gain),
                    "baseline_rice_ha": rice_original,
                    "baseline_wheat_ha": wheat_original,
                }
            )

    return pd.DataFrame(rows)


def top_states_for_bar(flags: pd.DataFrame) -> pd.DataFrame:
    if flags.empty:
        return pd.DataFrame(columns=["State", "n_districts", "co_occurring_area_ha"])
    summary = (
        flags.groupby("State", as_index=False)
        .agg(
            n_districts=("District", "nunique"),
            co_occurring_area_ha=("co_occurring_area_ha", "sum"),
        )
        .sort_values(["co_occurring_area_ha", "n_districts", "State"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    return summary.head(10)


def write_summary(
    area: pd.DataFrame,
    seasonal_crop_summary: pd.DataFrame,
    seasonal_transition_top: pd.DataFrame,
    pattern_flags: pd.DataFrame,
    top_states: pd.DataFrame,
) -> None:
    kharif_wheat_districts = int(
        len(
            area[
                (area["season"] == "kharif")
                & (area["Crop"] == "wheat")
                & (area["Original Area (Hectare)"] > 0.0)
            ]
        )
    )
    rabi_rice_districts = int(
        len(
            area[
                (area["season"] == "rabi")
                & (area["Crop"] == "rice")
                & (area["Original Area (Hectare)"] > 0.0)
            ]
        )
    )

    lines = [
        "# Seasonal Substitution Audit",
        "",
        "This audit uses the primary nitrogen-focused optimized area table generated under the",
        "hybrid 2017-18 realized-price revenue benchmark. The optimization itself is seasonal:",
        "kharif and rabi are solved",
        "independently, and the annual Figure 2(d) is an aggregation of those two seasonal outputs.",
        "",
        f"- districts with baseline kharif wheat area: {kharif_wheat_districts}",
        f"- districts with baseline rabi rice area: {rabi_rice_districts}",
        "",
        "Key interpretation:",
        "",
        "- There is no baseline kharif wheat in the primary area table, so any apparent annual",
        "  rice-to-wheat crossover in the combined panel is an annual aggregation artifact rather than",
        "  a kharif same-season substitution.",
        "- Same-season rice-loss / wheat-gain co-adjustment is confined to the rabi solution and only",
        "  occurs in districts where rabi rice is already present in the baseline system.",
        "- The wheat-to-coarse-cereal reallocations visible in the rabi solution occur within a seasonal",
        "  crop set that already contains rabi bajra, jowar, maize, and ragi in the observed baseline.",
        "",
        "Top direct seasonal findings from the primary realized-price rebuild:",
        "",
    ]

    for season in ["kharif", "rabi"]:
        sub = seasonal_crop_summary[seasonal_crop_summary["season"] == season].copy()
        lines.append(f"## {season.capitalize()} crop-area totals")
        for record in sub.itertuples(index=False):
            lines.append(
                f"- {record.Crop}: original={record.original_area_ha:.2f} ha, "
                f"optimized={record.optimized_area_ha:.2f} ha, delta={record.delta_ha:.2f} ha "
                f"({record.pct_change:.1f}%)"
            )
        lines.append("")

    for season in ["kharif", "rabi"]:
        top = seasonal_transition_top[seasonal_transition_top["season"] == season].copy()
        lines.append(f"## {season.capitalize()} largest non-diagonal transition-rule flows")
        for record in top.itertuples(index=False):
            lines.append(
                f"- {record.source_crop} -> {record.target_crop}: {record.flow_ha:.1f} ha"
            )
        lines.append("")

    if pattern_flags.empty:
        lines.extend(
            [
                "## Rice/wheat same-season audit",
                "- No district-season co-occurrence of rice loss with wheat gain or wheat loss with rice gain was detected.",
                "",
            ]
        )
    else:
        lines.append("## Rice/wheat same-season audit")
        pattern_summary = (
            pattern_flags.groupby(["season", "pattern"], as_index=False)
            .agg(
                n_districts=("District", "nunique"),
                co_occurring_area_ha=("co_occurring_area_ha", "sum"),
            )
            .sort_values(["season", "co_occurring_area_ha"], ascending=[True, False])
        )
        for record in pattern_summary.itertuples(index=False):
            lines.append(
                f"- {record.season} | {record.pattern}: {record.n_districts} districts, "
                f"{record.co_occurring_area_ha:.1f} ha co-occurring area"
            )
        lines.append("")
        lines.append("Top states for rabi rice-loss / wheat-gain co-adjustment:")
        for record in top_states.itertuples(index=False):
            lines.append(
                f"- {record.State}: {record.co_occurring_area_ha:.1f} ha across {record.n_districts} districts"
            )
        lines.append("")

    (OUT_DIR / "seasonal_substitution_summary.md").write_text("\n".join(lines))


def assemble_candidate_figure(
    kharif_png: Path,
    rabi_png: Path,
    top_states: pd.DataFrame,
) -> tuple[Path, Path]:
    kharif_image = mpimg.imread(kharif_png)
    rabi_image = mpimg.imread(rabi_png)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )

    fig = plt.figure(figsize=(11.0, 9.0), facecolor="white")
    grid = GridSpec(2, 2, figure=fig, height_ratios=[1.0, 0.72], hspace=0.08, wspace=0.05)

    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, :])

    for ax, image, label in [(ax_a, kharif_image, "a"), (ax_b, rabi_image, "b")]:
        ax.imshow(image, aspect="auto")
        ax.axis("off")
        ax.text(
            0.01,
            0.99,
            label,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=13,
            fontweight="bold",
        )

    ax_c.text(
        0.0,
        1.02,
        "c",
        transform=ax_c.transAxes,
        ha="left",
        va="bottom",
        fontsize=13,
        fontweight="bold",
    )

    if top_states.empty:
        ax_c.text(
            0.5,
            0.5,
            "No same-season rabi rice-loss / wheat-gain districts detected",
            ha="center",
            va="center",
            fontsize=11,
        )
        ax_c.axis("off")
    else:
        plot_data = top_states.iloc[::-1].copy()
        label_map = {
            "dadra and nagar haveli": "Dadra & Nagar Haveli",
        }
        plot_data["label"] = plot_data["State"].str.lower().map(label_map).fillna(plot_data["State"].str.title())
        ax_c.barh(
            plot_data["label"],
            plot_data["co_occurring_area_ha"],
            color="#4f81bd",
            edgecolor="black",
            linewidth=0.5,
        )
        ax_c.set_xlabel("Co-occurring rabi rice-loss / wheat-gain area (ha)")
        ax_c.set_title("States concentrating districts with same-season rabi rice reduction and wheat increase")
        ax_c.grid(axis="x", color="#d9d9d9", linewidth=0.6, alpha=0.8)
        ax_c.spines["top"].set_visible(False)
        ax_c.spines["right"].set_visible(False)
        ax_c.set_xlim(0.0, float(plot_data["co_occurring_area_ha"].max()) * 1.08)
        for y, record in enumerate(plot_data.itertuples(index=False)):
            ax_c.text(
                record.co_occurring_area_ha,
                y,
                f"  {record.n_districts} districts",
                va="center",
                ha="left",
                fontsize=8.5,
            )

    fig.subplots_adjust(left=0.20, right=0.985, top=0.985, bottom=0.07)

    out_png = FIG_DIR / "si_s21_seasonal_substitution_audit.png"
    out_pdf = FIG_DIR / "si_s21_seasonal_substitution_audit.pdf"
    fig.savefig(out_png, dpi=400, facecolor="white")
    fig.savefig(out_pdf, dpi=400, facecolor="white")
    plt.close(fig)
    return out_png, out_pdf


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    helper = load_helper()
    area = pd.read_csv(AREA_CSV)

    seasonal_crop_summary = (
        area.groupby(["season", "Crop"], as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_area_ha",
                "Optimized Area (Hectare)": "optimized_area_ha",
            }
        )
    )
    seasonal_crop_summary["delta_ha"] = (
        seasonal_crop_summary["optimized_area_ha"] - seasonal_crop_summary["original_area_ha"]
    )
    seasonal_crop_summary["pct_change"] = (
        100.0 * seasonal_crop_summary["delta_ha"] / seasonal_crop_summary["original_area_ha"]
    )
    seasonal_crop_summary.to_csv(OUT_DIR / "seasonal_crop_area_summary.csv", index=False)

    transition_top_rows: list[dict[str, object]] = []
    panel_pngs: dict[str, Path] = {}
    for season in ["kharif", "rabi"]:
        sub = area[area["season"] == season].copy()
        crop_order = helper._ordered_crops(sub)
        transition_long = helper.build_transition_matrix(sub, crop_order)
        transition_matrix = helper.pivot_transition_matrix(transition_long, crop_order)
        crop_summary = helper.build_crop_summary(sub, crop_order)

        transition_long.to_csv(OUT_DIR / f"{season}_transition_long.csv", index=False)
        transition_matrix.to_csv(OUT_DIR / f"{season}_transition_matrix.csv")
        crop_summary.to_csv(OUT_DIR / f"{season}_crop_summary.csv", index=False)

        top = (
            transition_long[transition_long["source_crop"] != transition_long["target_crop"]]
            .sort_values("flow_ha", ascending=False)
            .head(12)
            .copy()
        )
        top.insert(0, "season", season)
        transition_top_rows.extend(top.to_dict("records"))

        _, out_pdf = helper.plot_alluvial(
            transition_matrix,
            crop_summary,
            title=f"{season.capitalize()} season",
            output_stem=f"primary_revenue_{season}_seasonal_substitution_candidate",
        )
        panel_pngs[season] = out_pdf.with_suffix(".png")

    seasonal_transition_top = pd.DataFrame(transition_top_rows)
    seasonal_transition_top.to_csv(OUT_DIR / "seasonal_top_non_diagonal_transitions.csv", index=False)

    pattern_flags = build_pattern_flags(area)
    pattern_flags.to_csv(OUT_DIR / "district_season_rice_wheat_flags.csv", index=False)

    state_pattern_summary = (
        pattern_flags.groupby(["season", "pattern", "State"], as_index=False)
        .agg(
            n_districts=("District", "nunique"),
            co_occurring_area_ha=("co_occurring_area_ha", "sum"),
        )
        .sort_values(["season", "pattern", "co_occurring_area_ha"], ascending=[True, True, False])
        .reset_index(drop=True)
    )
    state_pattern_summary.to_csv(OUT_DIR / "state_rice_wheat_pattern_summary.csv", index=False)

    top_states = top_states_for_bar(
        pattern_flags[
            (pattern_flags["season"] == "rabi")
            & (pattern_flags["pattern"] == "rice_loss_wheat_gain")
        ].copy()
    )
    top_states.to_csv(OUT_DIR / "rabi_rice_loss_wheat_gain_top_states.csv", index=False)

    candidate_png, candidate_pdf = assemble_candidate_figure(
        panel_pngs["kharif"],
        panel_pngs["rabi"],
        top_states,
    )

    write_summary(
        area=area,
        seasonal_crop_summary=seasonal_crop_summary,
        seasonal_transition_top=seasonal_transition_top,
        pattern_flags=pattern_flags,
        top_states=top_states,
    )

    print(candidate_png)
    print(candidate_pdf)
