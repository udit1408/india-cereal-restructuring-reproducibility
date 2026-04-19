#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "si_hybrid_revenue_profit_sensitivity"
INPUT_DIR = ROOT / "data" / "input"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context,
    metric_totals,
    solve_endpoint,
)
from repro.config import default_layout  # noqa: E402


RATIO_CSV = DATA_DIR / "all_india_unit_price_to_msp_ratio_2013_14_to_2017_18.csv"
STATE_PRICE_CSV = INPUT_DIR / "reviewer_unit_price_state_year_inputs_2011_12_to_2017_18.csv"
JOIN_AUDIT_CSV = INPUT_DIR / "reviewer_unit_price_join_audit_2011_12_to_2017_18.csv"
OUT_PNG = FIG_DIR / "si_hybrid_revenue_profit_sensitivity.png"
OUT_PDF = FIG_DIR / "si_hybrid_revenue_profit_sensitivity.pdf"
OUT_SCENARIOS = OUT_DIR / "si_hybrid_revenue_profit_sensitivity_values.csv"
OUT_SUMMARY = OUT_DIR / "si_hybrid_revenue_profit_sensitivity_summary.csv"
OUT_AUDIT = OUT_DIR / "si_hybrid_revenue_profit_sensitivity_audit.md"

SCENARIO_YEARS = ["2013-14", "2014-15", "2015-16", "2016-17", "2017-18"]

CROP_MAP = {
    "Rice": "rice",
    "Wheat": "wheat",
    "Jowar": "jowar",
    "Bajra": "bajra",
    "Maize": "maize",
    "Ragi": "ragi",
}
CROP_ORDER = ["Rice", "Wheat", "Maize", "Jowar", "Bajra", "Ragi"]

SCENARIO_LABELS = {
    "MSP": "MSP baseline",
    "2013-14": "Hybrid 2013-14",
    "2014-15": "Hybrid 2014-15",
    "2015-16": "Hybrid 2015-16",
    "2016-17": "Hybrid 2016-17",
    "2017-18": "Hybrid 2017-18",
}

CANON_RE = re.compile(r"[^a-z0-9]+")
STATE_ALIASES = {
    "andaman and nicobar islands": "andaman and nicobar",
    "nct of delhi": "delhi",
}


def canon(text: object) -> str:
    value = "" if pd.isna(text) else str(text).strip().lower()
    value = value.replace("&", "and")
    value = STATE_ALIASES.get(value, value)
    value = CANON_RE.sub(" ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return STATE_ALIASES.get(value, value)


def zero_metrics() -> dict[str, float]:
    return {metric_key: 0.0 for _, metric_key in METRICS}


def load_ratio_scenarios() -> dict[str, dict[str, float]]:
    ratio = pd.read_csv(RATIO_CSV)
    scenarios: dict[str, dict[str, float]] = {}
    for year in SCENARIO_YEARS:
        crop_ratios = {}
        for _, row in ratio.iterrows():
            crop_key = CROP_MAP.get(row["crop_name"])
            if crop_key is None:
                continue
            value = row[year]
            crop_ratios[crop_key] = float(value) if pd.notna(value) else 1.0
        scenarios[year] = crop_ratios
    return scenarios


def load_state_price_bundle() -> tuple[
    dict[tuple[str, str, str], float],
    dict[tuple[str, str], float],
    set[tuple[str, str, str]],
]:
    state_price = pd.read_csv(STATE_PRICE_CSV)
    state_price = state_price[state_price["year"].isin(SCENARIO_YEARS)].copy()
    state_price["crop_key"] = state_price["crop_name"].map(CROP_MAP)
    state_price["state_key"] = state_price["des_state_name"].map(canon)
    state_price["production_tonnes_total"] = pd.to_numeric(
        state_price["production_tonnes_total"], errors="coerce"
    )
    state_price["value_output_inr"] = pd.to_numeric(state_price["value_output_inr"], errors="coerce")
    state_price["unit_price_inr_per_tonne"] = pd.to_numeric(
        state_price["unit_price_inr_per_tonne"], errors="coerce"
    )
    state_price["unit_price_inr_per_tonne"] = state_price["unit_price_inr_per_tonne"].where(
        np.isfinite(state_price["unit_price_inr_per_tonne"]),
        np.nan,
    )

    usable_direct = state_price[
        (state_price["join_status"] == "matched")
        & state_price["crop_key"].notna()
        & state_price["state_key"].notna()
        & state_price["state_key"].ne("")
        & state_price["unit_price_inr_per_tonne"].gt(0)
    ].copy()

    direct_grouped = (
        usable_direct.groupby(["year", "state_key", "crop_key"], as_index=False)
        .agg(
            value_output_inr=("value_output_inr", "sum"),
            production_tonnes_total=("production_tonnes_total", "sum"),
            mean_unit_price_inr_per_tonne=("unit_price_inr_per_tonne", "mean"),
        )
        .reset_index(drop=True)
    )
    direct_lookup: dict[tuple[str, str, str], float] = {}
    for row in direct_grouped.itertuples(index=False):
        if pd.notna(row.value_output_inr) and pd.notna(row.production_tonnes_total) and row.production_tonnes_total > 0 and row.value_output_inr > 0:
            price_qtl = float(row.value_output_inr) / float(row.production_tonnes_total) / 10.0
        else:
            price_qtl = float(row.mean_unit_price_inr_per_tonne) / 10.0
        direct_lookup[(str(row.year), str(row.state_key), str(row.crop_key))] = price_qtl

    usable_national = state_price[
        state_price["crop_key"].notna()
        & state_price["value_output_inr"].gt(0)
        & state_price["production_tonnes_total"].gt(0)
    ].copy()
    national_grouped = (
        usable_national.groupby(["year", "crop_key"], as_index=False)[
            ["value_output_inr", "production_tonnes_total"]
        ]
        .sum()
        .reset_index(drop=True)
    )
    national_lookup: dict[tuple[str, str], float] = {}
    for row in national_grouped.itertuples(index=False):
        national_lookup[(str(row.year), str(row.crop_key))] = (
            float(row.value_output_inr) / float(row.production_tonnes_total) / 10.0
        )

    unusable_direct = state_price[
        (state_price["join_status"] == "matched")
        & state_price["crop_key"].notna()
        & state_price["state_key"].notna()
        & state_price["state_key"].ne("")
        & (
            state_price["unit_price_inr_per_tonne"].isna()
            | state_price["unit_price_inr_per_tonne"].le(0)
        )
    ].copy()
    unusable_direct_keys = {
        (str(row.year), str(row.state_key), str(row.crop_key))
        for row in unusable_direct.itertuples(index=False)
    }

    return direct_lookup, national_lookup, unusable_direct_keys


def load_state_price_lookup() -> dict[tuple[str, str, str], float]:
    return load_state_price_bundle()[0]


def load_national_price_lookup() -> dict[tuple[str, str], float]:
    return load_state_price_bundle()[1]


def load_unusable_direct_price_keys() -> set[tuple[str, str, str]]:
    return load_state_price_bundle()[2]


def load_crop_year_coverage() -> pd.DataFrame:
    coverage = pd.read_csv(JOIN_AUDIT_CSV)
    coverage = coverage[
        coverage["year"].isin(SCENARIO_YEARS) & coverage["crop_name"].isin(CROP_ORDER)
    ].copy()
    coverage["crop_name"] = pd.Categorical(coverage["crop_name"], categories=CROP_ORDER, ordered=True)
    coverage["year"] = pd.Categorical(coverage["year"], categories=SCENARIO_YEARS, ordered=True)
    return coverage.sort_values(["crop_name", "year"]).reset_index(drop=True)


def annual_area_by_key(base_contexts: dict[str, dict[str, object]]) -> dict[tuple[str, str, str], float]:
    area: dict[tuple[str, str, str], float] = {}
    for context in base_contexts.values():
        for key, value in context["current_cereal_area"].items():
            area[key] = area.get(key, 0.0) + float(value)
    return area


def apply_hybrid_price_context(
    base_context: dict[str, object],
    year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
) -> tuple[dict[str, object], dict[str, float]]:
    context = copy.deepcopy(base_context)
    hybrid_msp = {}
    direct_keys = 0
    national_mean_keys = 0
    fallback_keys = 0
    national_price_lookup = national_price_lookup or {}
    unusable_direct_keys = unusable_direct_keys or set()

    for key, value in context["msp_per_prod"].items():
        state, _, crop = key
        key_lookup = (year, canon(state), canon(crop))
        direct_price = state_price_lookup.get(key_lookup)
        if direct_price is not None:
            hybrid_msp[key] = direct_price
            direct_keys += 1
        elif key_lookup in unusable_direct_keys:
            national_price = national_price_lookup.get((year, canon(crop)))
            if national_price is not None:
                hybrid_msp[key] = float(national_price)
                national_mean_keys += 1
            else:
                hybrid_msp[key] = float(value) * float(crop_ratios.get(crop, 1.0))
                fallback_keys += 1
        else:
            hybrid_msp[key] = float(value) * float(crop_ratios.get(crop, 1.0))
            fallback_keys += 1

    context["msp_per_prod"] = hybrid_msp
    initial_state_profit = {}
    for state in context["states"]:
        total = 0.0
        for district in context["districts_by_state"].get(state, []):
            for crop in context["crops_by_pair"].get((state, district), []):
                key = (state, district, crop)
                total += (
                    context["current_cereal_area"].get(key, 0.0)
                    * context["yield_data"].get(key, 0.0)
                    * 0.01
                    * (context["msp_per_prod"].get(key, 0.0) - context["cost_per_prod"].get(key, 0.0))
                )
        initial_state_profit[state] = total
    context["initial_state_profit"] = initial_state_profit
    return context, {
        "direct_keys": float(direct_keys),
        "national_mean_keys": float(national_mean_keys),
        "fallback_keys": float(fallback_keys),
    }


def solve_scenario_bundle(
    base_contexts: dict[str, dict[str, object]],
    scenario_key: str,
    state_price_lookup: dict[tuple[str, str, str], float],
    crop_ratios: dict[str, float] | None = None,
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    crop_ratios = crop_ratios or {crop: 1.0 for crop in CROP_MAP.values()}
    if scenario_key != "MSP" and (national_price_lookup is None or unusable_direct_keys is None):
        _, national_price_lookup, unusable_direct_keys = load_state_price_bundle()
    contexts = {}
    coverage_rows = []
    annual_area = annual_area_by_key(base_contexts)

    for season, context in base_contexts.items():
        if scenario_key == "MSP":
            contexts[season] = copy.deepcopy(context)
            total_keys = len(context["msp_per_prod"])
            coverage_rows.append(
                {
                    "scenario_key": scenario_key,
                    "season": season,
                    "direct_key_share": 1.0,
                    "fallback_key_share": 0.0,
                    "direct_area_share": 1.0,
                    "fallback_area_share": 0.0,
                    "total_keys": total_keys,
                }
            )
            continue

        hybrid_context, counts = apply_hybrid_price_context(
            context,
            scenario_key,
            crop_ratios,
            state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
        )
        contexts[season] = hybrid_context
        direct_area = 0.0
        national_mean_area = 0.0
        fallback_area = 0.0
        for key in context["msp_per_prod"]:
            state_key = canon(key[0])
            crop_key = canon(key[2])
            area_value = annual_area.get(key, 0.0)
            if (scenario_key, state_key, crop_key) in state_price_lookup:
                direct_area += area_value
            elif (
                unusable_direct_keys is not None
                and (scenario_key, state_key, crop_key) in unusable_direct_keys
                and national_price_lookup is not None
                and (scenario_key, crop_key) in national_price_lookup
            ):
                national_mean_area += area_value
            else:
                fallback_area += area_value
        total_area = direct_area + national_mean_area + fallback_area
        total_keys = counts["direct_keys"] + counts["national_mean_keys"] + counts["fallback_keys"]
        coverage_rows.append(
            {
                "scenario_key": scenario_key,
                "season": season,
                "direct_key_share": counts["direct_keys"] / total_keys if total_keys else 0.0,
                "national_mean_key_share": counts["national_mean_keys"] / total_keys if total_keys else 0.0,
                "fallback_key_share": counts["fallback_keys"] / total_keys if total_keys else 0.0,
                "direct_area_share": direct_area / total_area if total_area else 0.0,
                "national_mean_area_share": national_mean_area / total_area if total_area else 0.0,
                "fallback_area_share": fallback_area / total_area if total_area else 0.0,
                "total_keys": total_keys,
            }
        )

    rows: list[dict[str, object]] = []
    baseline_totals = {
        season: metric_totals(context["current_cereal_area"], context)
        for season, context in contexts.items()
    }

    for strategy in ["Water based", "Nitrogen based"]:
        objective = "water" if strategy == "Water based" else "nitrogen"
        optimized = zero_metrics()
        baseline = zero_metrics()
        statuses = []

        for season, context in contexts.items():
            status, area_map = solve_endpoint(context, objective, use_historical_caps=False)
            statuses.append(f"{season}:{status}")
            if status != "Optimal":
                raise RuntimeError(f"{scenario_key} | {strategy} | {season} returned {status}")
            season_totals = metric_totals(area_map, context)
            for metric_key in baseline:
                baseline[metric_key] += baseline_totals[season][metric_key]
                optimized[metric_key] += season_totals[metric_key]

        for metric_label, metric_key in METRICS:
            baseline_total = baseline[metric_key]
            optimized_total = optimized[metric_key]
            pct_reduction = 100.0 * (baseline_total - optimized_total) / baseline_total
            rows.append(
                {
                    "scenario_key": scenario_key,
                    "scenario_label": SCENARIO_LABELS[scenario_key],
                    "strategy": strategy,
                    "metric": metric_label,
                    "baseline_total": baseline_total,
                    "optimized_total": optimized_total,
                    "pct_reduction": pct_reduction,
                    "display_pct_change": -pct_reduction,
                    "solver_status": ";".join(statuses),
                }
            )

    return pd.DataFrame(rows), pd.DataFrame(coverage_rows)


def summarize(values: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    profit_rows = values[values["metric"] == "Profit"].copy()
    coverage_summary = (
        coverage.groupby("scenario_key", as_index=False)[["direct_key_share", "fallback_key_share", "direct_area_share", "fallback_area_share"]]
        .mean()
    )
    out = profit_rows.merge(coverage_summary, on="scenario_key", how="left")
    scenario_order = ["MSP"] + SCENARIO_YEARS
    out["scenario_key"] = pd.Categorical(out["scenario_key"], categories=scenario_order, ordered=True)
    return out.sort_values(["strategy", "scenario_key"]).reset_index(drop=True)


def build_figure(summary: pd.DataFrame, crop_year_coverage: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "font.family": "DejaVu Sans",
        }
    )

    display_order = ["MSP", "2017-18"]
    endpoint_order = ["Water based", "Nitrogen based"]
    endpoint_labels = {
        "Water based": "Water-based endpoint",
        "Nitrogen based": "Nitrogen-based endpoint",
    }
    endpoint_colors = {
        "Water based": "#1b9e77",
        "Nitrogen based": "#c77c00",
    }
    fig = plt.figure(figsize=(10.4, 7.0))
    grid = fig.add_gridspec(2, 1, height_ratios=[0.78, 1.0], hspace=0.42)
    main_ax = fig.add_subplot(grid[0, 0])
    heat_ax = fig.add_subplot(grid[1, 0])

    plotted = summary[summary["scenario_key"].isin(display_order)].copy()
    x_max = float(plotted["display_pct_change"].max())
    y_map = {"Water based": 1, "Nitrogen based": 0}

    for strategy in endpoint_order:
        subset = plotted[plotted["strategy"] == strategy].copy()
        subset["scenario_key"] = pd.Categorical(subset["scenario_key"].astype(str), categories=display_order, ordered=True)
        subset = subset.sort_values("scenario_key").reset_index(drop=True)
        msp_row = subset[subset["scenario_key"] == "MSP"].iloc[0]
        hybrid_row = subset[subset["scenario_key"] == "2017-18"].iloc[0]
        y = y_map[strategy]
        color = endpoint_colors[strategy]

        main_ax.plot(
            [float(hybrid_row["display_pct_change"]), float(msp_row["display_pct_change"])],
            [y, y],
            color="0.65",
            linewidth=1.6,
            zorder=1,
        )
        main_ax.scatter(
            float(msp_row["display_pct_change"]),
            y,
            s=74,
            marker="D",
            facecolor="black",
            edgecolor="black",
            linewidth=1.0,
            zorder=3,
        )
        main_ax.scatter(
            float(hybrid_row["display_pct_change"]),
            y,
            s=64,
            marker="o",
            facecolor=color,
            edgecolor=color,
            linewidth=1.0,
            zorder=3,
        )
        main_ax.text(
            float(msp_row["display_pct_change"]) + 0.45,
            y + 0.10,
            f"{float(msp_row['display_pct_change']):.2f}%",
            ha="left",
            va="bottom",
            fontsize=8.5,
            color="0.25",
        )
        main_ax.text(
            float(hybrid_row["display_pct_change"]) + 0.45,
            y - 0.10,
            f"{float(hybrid_row['display_pct_change']):.2f}%",
            ha="left",
            va="top",
            fontsize=8.5,
            color=color,
        )

    main_ax.set_title("a  Endpoint profit sensitivity under the hybrid revenue benchmark", loc="left", fontweight="bold")
    main_ax.set_xlabel("Profit change relative to scenario-specific baseline (%)")
    main_ax.set_yticks([y_map[key] for key in endpoint_order])
    main_ax.set_yticklabels([endpoint_labels[key] for key in endpoint_order])
    main_ax.set_xlim(0.0, x_max + 2.6)
    main_ax.set_ylim(-0.55, 1.55)
    main_ax.xaxis.grid(True, color="0.88", linewidth=0.8)
    main_ax.set_axisbelow(True)
    main_ax.spines["top"].set_visible(False)
    main_ax.spines["right"].set_visible(False)
    main_ax.spines["left"].set_color("0.35")
    main_ax.spines["bottom"].set_color("0.35")
    legend_handles = [
        Line2D([0], [0], marker="D", linestyle="", markersize=6.2, markerfacecolor="black", markeredgecolor="black"),
        Line2D([0], [0], marker="o", linestyle="", markersize=6.2, markerfacecolor="white", markeredgecolor="0.25"),
    ]
    main_ax.legend(
        legend_handles,
        ["MSP benchmark", "Hybrid 2017-18 benchmark"],
        frameon=False,
        fontsize=8.3,
        loc="lower right",
    )

    heatmap = (
        crop_year_coverage.pivot(index="crop_name", columns="year", values="match_rate")
        .reindex(index=CROP_ORDER, columns=SCENARIO_YEARS)
        * 100.0
    )
    im = heat_ax.imshow(heatmap.to_numpy(), aspect="auto", cmap="cividis", vmin=25.0, vmax=100.0)
    heat_ax.set_title("b  Realized-price row coverage by crop and year", loc="left", fontweight="bold")
    heat_ax.set_xticks(range(len(SCENARIO_YEARS)))
    heat_ax.set_xticklabels(SCENARIO_YEARS)
    heat_ax.set_yticks(range(len(CROP_ORDER)))
    heat_ax.set_yticklabels(CROP_ORDER)
    heat_ax.tick_params(length=0)
    for spine in heat_ax.spines.values():
        spine.set_color("0.35")
    for row_idx, crop_name in enumerate(CROP_ORDER):
        for col_idx, year in enumerate(SCENARIO_YEARS):
            value = float(heatmap.loc[crop_name, year])
            text_color = "white" if value < 62.0 else "black"
            heat_ax.text(
                col_idx,
                row_idx,
                f"{value:.0f}%",
                ha="center",
                va="center",
                fontsize=8.4,
                color=text_color,
            )
    colorbar = fig.colorbar(im, ax=heat_ax, fraction=0.024, pad=0.015)
    colorbar.set_label("Matched state-year observations (%)")
    colorbar.outline.set_edgecolor("0.35")

    hybrid_2017 = summary[summary["scenario_key"] == "2017-18"].iloc[0]
    hybrid_summary = summary[summary["scenario_key"] != "MSP"].copy()
    direct_key_min = 100.0 * float(hybrid_summary["direct_key_share"].min())
    direct_key_max = 100.0 * float(hybrid_summary["direct_key_share"].max())
    direct_area_min = 100.0 * float(hybrid_summary["direct_area_share"].min())
    direct_area_max = 100.0 * float(hybrid_summary["direct_area_share"].max())
    fig.text(
        0.5,
        0.012,
        (
            "Panel a shows the 2017-18 hybrid benchmark, aligned to the 2017 baseline optimization. "
            "Matched realized state-year prices are used where available and an all-India realized/MSP multiplier elsewhere.\n"
            f"For 2017-18, direct realized-price coverage is {100.0 * float(hybrid_2017['direct_key_share']):.2f}% of decision keys "
            f"and {100.0 * float(hybrid_2017['direct_area_share']):.2f}% of baseline cereal area. "
            f"Across 2013-14 to 2017-18, direct coverage spans {direct_key_min:.2f}-{direct_key_max:.2f}% of decision keys "
            f"and {direct_area_min:.2f}-{direct_area_max:.2f}% of baseline cereal area."
        ),
        ha="center",
        va="bottom",
        fontsize=8.4,
        color="0.25",
    )

    fig.savefig(OUT_PNG, dpi=450, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def write_audit(values: pd.DataFrame, summary: pd.DataFrame, crop_year_coverage: pd.DataFrame) -> None:
    hybrid_2017 = summary[summary["scenario_key"] == "2017-18"].iloc[0]
    hybrid_summary = summary[summary["scenario_key"] != "MSP"].copy()
    direct_key_min = 100.0 * float(hybrid_summary["direct_key_share"].min())
    direct_key_max = 100.0 * float(hybrid_summary["direct_key_share"].max())
    direct_area_min = 100.0 * float(hybrid_summary["direct_area_share"].min())
    direct_area_max = 100.0 * float(hybrid_summary["direct_area_share"].max())
    crop_cov_min_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmin()]
    crop_cov_max_row = crop_year_coverage.loc[crop_year_coverage["match_rate"].idxmax()]

    lines = [
        "# Hybrid revenue profit sensitivity audit",
        "",
        "This SI-only figure reruns the primary endpoint solves under a hybrid",
        "revenue benchmark. For each year scenario, official realized state-year unit prices",
        "are used where matched state-level data exist. For state-crop combinations without matched",
        "realized-price data, the original district MSP benchmark is scaled by the corresponding",
        "all-India realized-price/MSP multiplier for that crop and year.",
        "",
        "Panel a displays only the 2017-18 hybrid benchmark because this is the realized-price year",
        "most closely aligned with the 2017 baseline optimization used in the manuscript.",
        f"For 2017-18, direct realized-price coverage is {100.0 * float(hybrid_2017['direct_key_share']):.2f}% of decision keys",
        f"and {100.0 * float(hybrid_2017['direct_area_share']):.2f}% of baseline cereal area.",
        f"Across hybrid scenarios, direct realized-price coverage spans {direct_key_min:.2f}-{direct_key_max:.2f}% of decision keys",
        f"and {direct_area_min:.2f}-{direct_area_max:.2f}% of baseline cereal area. Crop-year row coverage ranges from",
        f"{100.0 * float(crop_cov_min_row['match_rate']):.1f}% ({crop_cov_min_row['crop_name']}, {crop_cov_min_row['year']})",
        f"to {100.0 * float(crop_cov_max_row['match_rate']):.1f}% ({crop_cov_max_row['crop_name']}, {crop_cov_max_row['year']}).",
        "",
        "Profit outcomes by scenario and strategy:",
    ]
    for row in summary.itertuples(index=False):
        if row.scenario_key == "MSP":
            lines.append(
                f"- {row.scenario_label} | {row.strategy}: profit change {row.display_pct_change:.3f}% ; "
                "coverage not applicable (pure MSP benchmark)"
            )
        else:
            lines.append(
                f"- {row.scenario_label} | {row.strategy}: profit change {row.display_pct_change:.3f}% ; "
                f"direct key share {100 * row.direct_key_share:.2f}% ; fallback key share {100 * row.fallback_key_share:.2f}% ; "
                f"direct area share {100 * row.direct_area_share:.2f}% ; fallback area share {100 * row.fallback_area_share:.2f}%"
            )
    lines.extend(["", "Solver status by scenario and strategy:"])
    for row in values[["scenario_label", "strategy", "solver_status"]].drop_duplicates().itertuples(index=False):
        lines.append(f"- {row.scenario_label} | {row.strategy}: {row.solver_status}")
    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    base_contexts = {
        season: build_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    ratio_scenarios = load_ratio_scenarios()
    state_price_lookup = load_state_price_lookup()
    crop_year_coverage = load_crop_year_coverage()

    value_frames = []
    coverage_frames = []

    msp_values, msp_coverage = solve_scenario_bundle(base_contexts, "MSP", state_price_lookup)
    value_frames.append(msp_values)
    coverage_frames.append(msp_coverage)

    for year in SCENARIO_YEARS:
        values, coverage = solve_scenario_bundle(base_contexts, year, state_price_lookup, ratio_scenarios[year])
        value_frames.append(values)
        coverage_frames.append(coverage)

    values = pd.concat(value_frames, ignore_index=True)
    coverage = pd.concat(coverage_frames, ignore_index=True)
    summary = summarize(values, coverage)

    values.to_csv(OUT_SCENARIOS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(summary, crop_year_coverage)
    write_audit(values, summary, crop_year_coverage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a supplementary hybrid realized-price/MSP-fallback profit sensitivity figure."
    )
    parser.parse_args()
    main()
