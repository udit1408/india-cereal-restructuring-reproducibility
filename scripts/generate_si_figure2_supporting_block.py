#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated" / "si_figure2_block"
PRIMARY_EQ_DIR = ROOT / "data" / "generated" / "Figure2_equivalent"
PRIMARY_SCENARIO_YEAR = "2017-18"

sys.path.insert(0, str(ROOT / "scripts"))

import generate_figure2b_clean as figure2b  # noqa: E402
import generate_Figure2_equivalent as figure2eq  # noqa: E402
from generate_si_hybrid_revenue_profit_sensitivity import (  # noqa: E402
    load_ratio_scenarios,
    load_state_price_lookup,
)


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_figure(fig: plt.Figure, stem: str) -> tuple[Path, Path]:
    png_path = FIG_DIR / f"{stem}.png"
    pdf_path = FIG_DIR / f"{stem}.pdf"
    fig.savefig(png_path, dpi=400, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path


def load_seasonal_frontiers() -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for season in ("rabi", "kharif"):
        frame = pd.read_csv(PRIMARY_EQ_DIR / f"Figure2_equivalent_panel_a_{season}_by_alpha.csv").rename(
            columns={"Alpha": "alpha"}
        )
        frames[season] = frame.sort_values("alpha").reset_index(drop=True)
    return frames


def decile_frontier_points(frame: pd.DataFrame) -> pd.DataFrame:
    wanted = [round(i / 10, 1) for i in range(11)]
    rows = []
    for alpha in wanted:
        idx = (frame["alpha"] - alpha).abs().idxmin()
        rows.append(frame.loc[idx, ["alpha", "nitrogen_mt", "water_bcm"]].to_dict())
    return pd.DataFrame(rows)


def build_s2(frontiers: dict[str, pd.DataFrame]) -> pd.DataFrame:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, axes = plt.subplots(2, 1, figsize=(8.1, 7.9), constrained_layout=True)
    panel_rows: list[pd.DataFrame] = []
    for ax, season, panel in zip(axes, ("rabi", "kharif"), ("a", "b"), strict=True):
        frame = decile_frontier_points(frontiers[season]).copy()
        frame["season"] = season
        panel_rows.append(frame)

        ax.plot(
            frame["nitrogen_mt"],
            frame["water_bcm"],
            color="#74a9cf",
            linewidth=1.5,
            zorder=2,
        )
        ax.scatter(
            frame["nitrogen_mt"].iloc[1:-1],
            frame["water_bcm"].iloc[1:-1],
            s=22,
            color="#2b8cbe",
            edgecolor="white",
            linewidth=0.4,
            zorder=3,
        )
        ax.scatter(
            frame["nitrogen_mt"].iloc[0],
            frame["water_bcm"].iloc[0],
            marker="*",
            s=140,
            color="#6a3d9a",
            edgecolor="black",
            linewidth=0.4,
            label="Water-focused end",
            zorder=4,
        )
        ax.scatter(
            frame["nitrogen_mt"].iloc[-1],
            frame["water_bcm"].iloc[-1],
            marker="*",
            s=140,
            color="#d18f00",
            edgecolor="black",
            linewidth=0.4,
            label="Nitrogen-focused end",
            zorder=4,
        )
        ax.grid(True, axis="both", color="#d9d9d9", linewidth=0.6, alpha=0.7)
        ax.set_title(
            f"Pareto front {season.capitalize()} season: nitrogen surplus vs. consumptive water demand",
            pad=8,
        )
        ax.set_xlabel("Nitrogen surplus (Mt)")
        ax.set_ylabel("Consumptive water demand (BCM)")
        ax.legend(loc="upper right", frameon=False, fontsize=9, handletextpad=0.6)
        ax.text(-0.12, 1.04, panel, transform=ax.transAxes, fontsize=18, fontweight="bold", va="top")
        x_pad = 0.02 * (frame["nitrogen_mt"].max() - frame["nitrogen_mt"].min())
        y_pad = 0.05 * (frame["water_bcm"].max() - frame["water_bcm"].min())
        ax.set_xlim(frame["nitrogen_mt"].min() - x_pad, frame["nitrogen_mt"].max() + x_pad)
        ax.set_ylim(frame["water_bcm"].min() - y_pad, frame["water_bcm"].max() + y_pad)

    save_figure(fig, "si_s2_seasonal_pareto")
    return pd.concat(panel_rows, ignore_index=True)


def build_contexts() -> dict[str, dict[str, object]]:
    layout = figure2b.default_layout(figure2b.AUDIT_ROOT)
    crop_ratios = load_ratio_scenarios()[PRIMARY_SCENARIO_YEAR]
    state_price_lookup = load_state_price_lookup()
    return {
        season: figure2eq._apply_hybrid_price_to_dict_context(
            figure2b.build_context(layout, season, notebook_name),
            scenario_year=PRIMARY_SCENARIO_YEAR,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            panel_key="s3",
        )[0]
        for season, notebook_name in figure2b.SEASON_NOTEBOOKS.items()
    }


def build_s3(contexts: dict[str, dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for season, context in contexts.items():
        baseline = figure2b.metric_totals(context["current_cereal_area"], context)
        for scenario in ("nitrogen", "water"):
            status, area_map = figure2b.solve_endpoint(context, scenario, use_historical_caps=False)
            if status != "Optimal":
                raise RuntimeError(f"{season} {scenario} endpoint solve returned {status}")
            optimized = figure2b.metric_totals(area_map, context)
            for metric_label, metric_key in figure2b.METRICS:
                original_total = baseline[metric_key]
                optimized_total = optimized[metric_key]
                pct_change = 100.0 * (optimized_total - original_total) / original_total
                rows.append(
                    {
                        "season": season,
                        "scenario": scenario,
                        "metric": metric_label,
                        "original_total": original_total,
                        "optimized_total": optimized_total,
                        "pct_change": pct_change,
                    }
                )

    table = pd.DataFrame(rows)
    table["metric"] = pd.Categorical(
        table["metric"],
        categories=[metric for metric, _ in figure2b.METRICS],
        ordered=True,
    )
    table = table.sort_values(["season", "scenario", "metric"]).reset_index(drop=True)
    table.to_csv(DATA_DIR / "si_s3_seasonal_tradeoffs.csv", index=False)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )
    display_labels = {
        "Nitrogen Emission": "N emission",
        "Nitrogen Leach": "N leach",
        "Greenhouse Gas emission": "AGHG",
        "Profit": "Profit",
        "Calorie": "Calorie",
        "Phosphorus application": "P applied",
        "Nitrogen application": "N applied",
        "Phosphorus Surplus": "P surplus",
        "Nitrogen Surplus": "N surplus",
        "Water Demand": "Water",
    }
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.7), constrained_layout=True)
    panel_specs = [
        ("kharif", "nitrogen", "a", "Kharif nitrogen-focused endpoint"),
        ("rabi", "nitrogen", "b", "Rabi nitrogen-focused endpoint"),
        ("kharif", "water", "c", "Kharif water-focused endpoint"),
        ("rabi", "water", "d", "Rabi water-focused endpoint"),
    ]
    for ax, (season, scenario, panel, title) in zip(axes.flat, panel_specs, strict=True):
        subset = table[(table["season"] == season) & (table["scenario"] == scenario)].copy()
        subset = subset.sort_values("metric")
        values = subset["pct_change"].to_numpy()
        y = np.arange(len(subset))
        colors = ["#cf3b2f" if value > 0 else "#1b9e77" for value in values]
        ax.barh(y, values, color=colors, edgecolor="black", linewidth=0.4, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels([display_labels[str(metric)] for metric in subset["metric"]])
        ax.axvline(0.0, color="#666666", linewidth=0.8, zorder=2)
        ax.grid(True, axis="x", color="#d9d9d9", linewidth=0.6, alpha=0.75)
        max_abs = max(abs(values.min()), abs(values.max()))
        pad = max(3.0, 0.12 * max_abs)
        ax.set_xlim(values.min() - pad, values.max() + pad)
        ax.set_xlabel("Change relative to baseline (%)")
        ax.set_title(title, pad=8)
        ax.invert_yaxis()
        ax.text(-0.16, 1.04, panel, transform=ax.transAxes, fontsize=18, fontweight="bold", va="top")

    save_figure(fig, "si_s3_seasonal_tradeoffs")
    return table


def build_s4() -> pd.DataFrame:
    kharif = pd.read_csv(PRIMARY_EQ_DIR / "Figure2_equivalent_panel_c_kharif.csv")
    rabi = pd.read_csv(PRIMARY_EQ_DIR / "Figure2_equivalent_panel_c_rabi.csv")
    for frame, season in ((kharif, "kharif"), (rabi, "rabi")):
        frame["season"] = season
    table = pd.concat([kharif, rabi], ignore_index=True)
    table = table.sort_values(["season", "nominal_substitution_pct"]).reset_index(drop=True)
    table.to_csv(DATA_DIR / "si_s4_cultural_retention.csv", index=False)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(10.7, 4.1), constrained_layout=True)
    panel_specs = [
        ("kharif", "a", "State-level rice retention (Kharif)"),
        ("rabi", "b", "State-level wheat retention (Rabi)"),
    ]
    for ax, (season, panel, title) in zip(axes, panel_specs, strict=True):
        subset = table[table["season"] == season].copy()
        x = subset["nominal_substitution_pct"].to_numpy()
        y = subset["pct_reduction_n_surplus"].to_numpy()
        ax.plot(x, y, color="#2b8cbe", linewidth=1.6, zorder=2)
        ax.scatter(x, y, s=24, color="#2b8cbe", edgecolor="white", linewidth=0.4, zorder=3)
        ax.scatter(x[0], y[0], s=46, color="#238b45", edgecolor="white", linewidth=0.5, label="Full retention", zorder=4)
        ax.scatter(x[-1], y[-1], s=46, color="#cf3b2f", edgecolor="white", linewidth=0.5, label="Full relaxation", zorder=4)
        for ref in (25, 50, 75):
            ax.axvline(ref, color="#9e9e9e", linestyle="--", linewidth=0.8, zorder=1)
        ax.grid(True, axis="both", color="#d9d9d9", linewidth=0.6, alpha=0.7)
        ax.set_title(title, pad=8)
        ax.set_xlabel("Allowed staple-area substitution (%)")
        ax.set_ylabel("Nitrogen-surplus reduction (%)")
        ax.set_xlim(-2, 102)
        y_pad = max(0.4, 0.07 * (y.max() - y.min()))
        ax.set_ylim(y.min() - y_pad, y.max() + y_pad)
        ax.legend(loc="lower right", frameon=False, fontsize=8)
        ax.text(-0.12, 1.04, panel, transform=ax.transAxes, fontsize=18, fontweight="bold", va="top")

    save_figure(fig, "si_s4_cultural_retention")
    return table


def write_audit(
    frontier_points: pd.DataFrame,
    seasonal_tradeoffs: pd.DataFrame,
    cultural_table: pd.DataFrame,
) -> None:
    lines = [
        "# SI figure-2 supporting block regeneration audit",
        "",
        "This audit documents the rebuilt assets for Supplementary Figures S2, S3, and S4.",
        f"All three figures are now generated from the primary hybrid {PRIMARY_SCENARIO_YEAR} revenue benchmark",
        "used in the revised main text, rather than from the older district-MSP figure branch.",
        "Archived district-MSP versions of these seasonal figures have been preserved separately in",
        "`figures/manuscript_final/si_msp_s2_seasonal_pareto.*`,",
        "`figures/manuscript_final/si_msp_s3_seasonal_tradeoffs.*`, and",
        "`figures/manuscript_final/si_msp_s4_cultural_retention.*`, while the main MSP comparison block",
        "remains documented later in Supplementary Figures S18-S19.",
        "",
        "## Figure S2",
        "- Source files: `data/generated/Figure2_equivalent/Figure2_equivalent_panel_a_rabi_by_alpha.csv` and",
        "  `data/generated/Figure2_equivalent/Figure2_equivalent_panel_a_kharif_by_alpha.csv`.",
        "- Plot content: decile alpha points from the primary kharif and rabi Pareto frontiers, with water-focused",
        "  and nitrogen-focused endpoints highlighted explicitly.",
    ]
    for season in ("rabi", "kharif"):
        subset = frontier_points[frontier_points["season"] == season]
        lines.append(
            f"- {season}: nitrogen surplus {subset['nitrogen_mt'].min():.3f} to {subset['nitrogen_mt'].max():.3f} Mt; "
            f"water demand {subset['water_bcm'].min():.3f} to {subset['water_bcm'].max():.3f} BCM."
        )

    lines.extend(
        [
            "",
            "## Figure S3",
            "- Source logic: season-specific endpoint solves from `generate_figure2b_clean.py` with",
            "  fixed district cropped area, substitution among historically observed cereals, no district-crop",
            f"  historical area caps, and the primary hybrid {PRIMARY_SCENARIO_YEAR} revenue benchmark",
            "  applied to the state price term before solving.",
            "- Values below are changes relative to the baseline cereal allocation.",
        ]
    )
    for season in ("kharif", "rabi"):
        for scenario in ("water", "nitrogen"):
            subset = seasonal_tradeoffs[
                (seasonal_tradeoffs["season"] == season) & (seasonal_tradeoffs["scenario"] == scenario)
            ]
            key_metrics = subset[subset["metric"].isin(["Water Demand", "Nitrogen Surplus", "Profit", "Calorie"])]
            lines.append(f"- {season} {scenario}:")
            for row in key_metrics.itertuples(index=False):
                lines.append(f"  - {row.metric}: {row.pct_change:+.3f}%")

    lines.extend(
        [
            "",
            "## Figure S4",
            "- Source files: `data/generated/Figure2_equivalent/Figure2_equivalent_panel_c_kharif.csv` and",
            "  `data/generated/Figure2_equivalent/Figure2_equivalent_panel_c_rabi.csv`.",
            "- Plot content: nitrogen-surplus reduction as the state-level retained rice or wheat floor is relaxed.",
        ]
    )
    for season in ("kharif", "rabi"):
        subset = cultural_table[cultural_table["season"] == season]
        min_row = subset.loc[subset["nominal_substitution_pct"].idxmin()]
        max_row = subset.loc[subset["nominal_substitution_pct"].idxmax()]
        lines.append(
            f"- {season}: {min_row['pct_reduction_n_surplus']:.3f}% reduction at full retention "
            f"({min_row['nominal_substitution_pct']:.0f}% substitution allowed) and "
            f"{max_row['pct_reduction_n_surplus']:.3f}% at full relaxation "
            f"({max_row['nominal_substitution_pct']:.0f}% substitution allowed)."
        )

    (DATA_DIR / "si_figure2_block_audit.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ensure_dirs()
    frontiers = load_seasonal_frontiers()
    frontier_points = build_s2(frontiers)
    frontier_points.to_csv(DATA_DIR / "si_s2_seasonal_pareto_points.csv", index=False)
    contexts = build_contexts()
    seasonal_tradeoffs = build_s3(contexts)
    cultural_table = build_s4()
    write_audit(frontier_points, seasonal_tradeoffs, cultural_table)
    print(FIG_DIR / "si_s2_seasonal_pareto.pdf")
    print(FIG_DIR / "si_s3_seasonal_tradeoffs.pdf")
    print(FIG_DIR / "si_s4_cultural_retention.pdf")


if __name__ == "__main__":
    main()
