#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRICE_CSV = (
    ROOT / "data" / "input" / "statewise_realized_price_vs_msp_2014_15_to_2018_19.csv"
)
DEFAULT_SCENARIO_YEAR = "2017-18"
DEFAULT_SANDBOX_NAME = "figure2_stateprice_csv_sandbox_2017_18"
CANON_RE = re.compile(r"[^a-z0-9]+")


sys.path.insert(0, str(ROOT / "scripts"))
import generate_figure2_main as base  # noqa: E402


STATE_ALIASES = {
    "andaman and nicobar islands": "andaman and nicobar",
    "a and n islands": "andaman and nicobar",
    "a n islands": "andaman and nicobar",
    "nct of delhi": "delhi",
    "pondicherry": "puducherry",
}

UNION_TERRITORY_KEYS = {
    "andaman and nicobar",
    "chandigarh",
    "dadra and nagar haveli",
    "daman and diu",
    "delhi",
    "lakshadweep",
    "puducherry",
}

CROP_MAP = {
    "Rice": "rice",
    "Wheat": "wheat",
    "Jowar": "jowar",
    "Bajra": "bajra",
    "Maize": "maize",
    "Ragi": "ragi",
}


def canon(text: object) -> str:
    value = "" if pd.isna(text) else str(text).strip().lower()
    value = value.replace("&", "and")
    value = STATE_ALIASES.get(value, value)
    value = CANON_RE.sub(" ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return STATE_ALIASES.get(value, value)


def configure_base_paths(sandbox_root: Path) -> tuple[Path, Path]:
    fig_dir = sandbox_root / "figures"
    out_dir = sandbox_root / "data"
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    base.FIG_DIR = fig_dir
    base.OUT_DIR = out_dir
    base.PANEL_FILES = {
        "a": fig_dir / "figure2_main_panel_a.png",
        "b": fig_dir / "figure2_main_panel_b.png",
        "c": fig_dir / "figure2_main_panel_c.png",
        "d": fig_dir / "figure2_main_panel_d.png",
    }
    base.COMPOSITE_PNG = fig_dir / "Figure2_stateprice_csv_sandbox.png"
    base.COMPOSITE_PDF = fig_dir / "Figure2_stateprice_csv_sandbox.pdf"
    base.SUMMARY_CSV = out_dir / "Figure2_stateprice_csv_sandbox_summary.csv"
    base.AUDIT_MD = out_dir / "Figure2_stateprice_csv_sandbox_audit.md"
    base.COVERAGE_CSV = out_dir / "Figure2_stateprice_csv_sandbox_price_coverage.csv"
    base.MANIFEST_MD = out_dir / "Figure2_stateprice_csv_sandbox_manifest.md"
    base.PANEL_B_BOOTSTRAP_DIR = out_dir / "panel_b_bootstrap"
    base.canon = canon
    return fig_dir, out_dir


def load_stateprice_csv(price_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(price_csv)
    df["Year"] = df["Year"].astype(str).str.strip()
    df["Crop"] = df["Crop"].astype(str).str.strip()
    df["State"] = df["State"].astype(str).str.strip()
    df["crop_key"] = df["Crop"].map(CROP_MAP)
    df["state_key"] = df["State"].map(canon)
    for col in ["Output_lakh", "Production_tonne", "rupee_per_kg", "MSP_rs_per_kg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].where(np.isfinite(df[col]), np.nan)
    df["ratio_to_msp"] = df["rupee_per_kg"] / df["MSP_rs_per_kg"]
    df["is_modeled_state"] = (
        df["state_key"].ne("") & ~df["state_key"].isin(UNION_TERRITORY_KEYS)
    )
    df = df[df["crop_key"].notna() & df["is_modeled_state"]].copy()
    return df


def build_ratio_scenarios_from_stateprice(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    usable = df[
        df["Output_lakh"].gt(0)
        & df["Production_tonne"].gt(0)
        & df["MSP_rs_per_kg"].gt(0)
        & df["Year"].notna()
        & df["crop_key"].notna()
    ].copy()
    year_crop = (
        usable.groupby(["Year", "crop_key"], as_index=False)
        .agg(
            output_lakh_sum=("Output_lakh", "sum"),
            production_tonne_sum=("Production_tonne", "sum"),
            mean_msp_rs_per_kg=("MSP_rs_per_kg", "mean"),
        )
        .reset_index(drop=True)
    )
    year_crop["national_price_rs_per_kg"] = (
        year_crop["output_lakh_sum"] * 100.0 / year_crop["production_tonne_sum"]
    )
    year_crop["ratio_to_msp"] = (
        year_crop["national_price_rs_per_kg"] / year_crop["mean_msp_rs_per_kg"]
    )
    overall_crop_ratio = year_crop.groupby("crop_key")["ratio_to_msp"].mean().to_dict()
    scenarios: dict[str, dict[str, float]] = {}
    for year, year_df in year_crop.groupby("Year"):
        crop_ratios = {crop_key: float(overall_crop_ratio.get(crop_key, 1.0)) for crop_key in CROP_MAP.values()}
        year_means = year_df.set_index("crop_key")["ratio_to_msp"].to_dict()
        for crop_key, value in year_means.items():
            crop_ratios[crop_key] = float(value)
        scenarios[str(year)] = crop_ratios
    return scenarios


def build_stateprice_inputs(
    df: pd.DataFrame,
) -> tuple[
    dict[tuple[str, str, str], float],
    dict[tuple[str, str], float],
    set[tuple[str, str, str]],
]:
    grouped = (
        df[df["state_key"].ne("") & df["crop_key"].notna()]
        .groupby(["Year", "state_key", "crop_key"], as_index=False)
        .agg(
            output_lakh_sum=("Output_lakh", "sum"),
            production_tonne_sum=("Production_tonne", "sum"),
            mean_rupee_per_kg=("rupee_per_kg", "mean"),
        )
        .reset_index(drop=True)
    )
    state_lookup: dict[tuple[str, str, str], float] = {}
    unusable_state_keys: set[tuple[str, str, str]] = set()
    for row in grouped.itertuples(index=False):
        key = (str(row.Year), str(row.state_key), str(row.crop_key))
        if pd.notna(row.output_lakh_sum) and pd.notna(row.production_tonne_sum) and row.output_lakh_sum > 0 and row.production_tonne_sum > 0:
            state_lookup[key] = float(row.output_lakh_sum) * 100.0 / float(row.production_tonne_sum)
        elif pd.notna(row.mean_rupee_per_kg) and row.mean_rupee_per_kg > 0:
            state_lookup[key] = float(row.mean_rupee_per_kg)
        else:
            unusable_state_keys.add(key)

    national_grouped = (
        df[df["crop_key"].notna()]
        .groupby(["Year", "crop_key"], as_index=False)
        .agg(
            output_lakh_sum=("Output_lakh", "sum"),
            production_tonne_sum=("Production_tonne", "sum"),
        )
        .reset_index(drop=True)
    )
    national_lookup: dict[tuple[str, str], float] = {}
    for row in national_grouped.itertuples(index=False):
        if pd.notna(row.output_lakh_sum) and pd.notna(row.production_tonne_sum) and row.output_lakh_sum > 0 and row.production_tonne_sum > 0:
            national_lookup[(str(row.Year), str(row.crop_key))] = (
                float(row.output_lakh_sum) * 100.0 / float(row.production_tonne_sum)
            )

    return state_lookup, national_lookup, unusable_state_keys


def patch_base_price_application(
    *,
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float],
    zero_state_keys: set[tuple[str, str, str]],
) -> None:
    default_national_price_lookup = national_price_lookup
    default_zero_state_keys = zero_state_keys

    def apply_to_dict_context(
        base_context: dict[str, object],
        *,
        scenario_year: str,
        crop_ratios: dict[str, float],
        state_price_lookup: dict[tuple[str, str, str], float],
        national_price_lookup: dict[tuple[str, str], float] | None = None,
        unusable_direct_keys: set[tuple[str, str, str]] | None = None,
        panel_key: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        effective_national_lookup = (
            default_national_price_lookup if national_price_lookup is None else national_price_lookup
        )
        effective_unusable_keys = (
            default_zero_state_keys if unusable_direct_keys is None else unusable_direct_keys
        )
        context = copy.deepcopy(base_context)
        hybrid_prices: dict[tuple[str, str, str], float] = {}
        direct_keys = 0
        zero_fill_keys = 0
        ratio_fallback_keys = 0
        direct_area = 0.0
        zero_fill_area = 0.0
        ratio_fallback_area = 0.0

        current_cereal_area = base._current_cereal_area_from_dict_context(context)
        context["current_cereal_area"] = current_cereal_area

        for key, value in context["msp_per_prod"].items():
            state, _, crop = key
            state_key = canon(state)
            crop_key = canon(crop)
            area = float(current_cereal_area.get(key, 0.0))
            direct_price = state_price_lookup.get((scenario_year, state_key, crop_key))
            if direct_price is not None:
                hybrid_prices[key] = float(direct_price)
                direct_keys += 1
                direct_area += area
                continue

            national_price = effective_national_lookup.get((scenario_year, crop_key))
            if national_price is not None:
                hybrid_prices[key] = float(national_price)
                zero_fill_keys += 1
                zero_fill_area += area
                continue

            hybrid_prices[key] = float(value) * float(crop_ratios.get(crop_key, 1.0))
            ratio_fallback_keys += 1
            ratio_fallback_area += area

        context["msp_per_prod"] = hybrid_prices
        context["initial_state_profit"] = base._recompute_initial_state_profit(
            states=context["states"],
            districts_by_state=context["districts_by_state"],
            crops_by_pair=context["crops_by_pair"],
            current_cereal_area=context["current_cereal_area"],
            yield_data=context["yield_data"],
            price_map=hybrid_prices,
            cost_per_prod=context["cost_per_prod"],
        )

        total_keys = direct_keys + zero_fill_keys + ratio_fallback_keys
        total_area = direct_area + zero_fill_area + ratio_fallback_area
        coverage = {
            "panel": panel_key,
            "season": str(context["season"]),
            "scenario_year": scenario_year,
            "direct_keys": direct_keys,
            "zero_fill_keys": zero_fill_keys,
            "ratio_fallback_keys": ratio_fallback_keys,
            "direct_key_share": direct_keys / total_keys if total_keys else 0.0,
            "zero_fill_key_share": zero_fill_keys / total_keys if total_keys else 0.0,
            "ratio_fallback_key_share": ratio_fallback_keys / total_keys if total_keys else 0.0,
            "fallback_keys": ratio_fallback_keys,
            "direct_area_share": direct_area / total_area if total_area else 0.0,
            "zero_fill_area_share": zero_fill_area / total_area if total_area else 0.0,
            "ratio_fallback_area_share": ratio_fallback_area / total_area if total_area else 0.0,
            "fallback_area_share": ratio_fallback_area / total_area if total_area else 0.0,
        }
        return context, coverage

    def apply_to_season_context(
        base_context,
        *,
        scenario_year: str,
        crop_ratios: dict[str, float],
        state_price_lookup: dict[tuple[str, str, str], float],
        national_price_lookup: dict[tuple[str, str], float] | None = None,
        unusable_direct_keys: set[tuple[str, str, str]] | None = None,
        panel_key: str,
    ):
        effective_national_lookup = (
            default_national_price_lookup if national_price_lookup is None else national_price_lookup
        )
        effective_unusable_keys = (
            default_zero_state_keys if unusable_direct_keys is None else unusable_direct_keys
        )
        context = copy.deepcopy(base_context)
        hybrid_prices: dict[tuple[str, str, str], float] = {}
        direct_keys = 0
        zero_fill_keys = 0
        ratio_fallback_keys = 0
        direct_area = 0.0
        zero_fill_area = 0.0
        ratio_fallback_area = 0.0

        for key, value in context.msp_per_prod.items():
            state, _, crop = key
            state_key = canon(state)
            crop_key = canon(crop)
            area = float(context.current_cereal_area.get(key, 0.0))
            direct_price = state_price_lookup.get((scenario_year, state_key, crop_key))
            if direct_price is not None:
                hybrid_prices[key] = float(direct_price)
                direct_keys += 1
                direct_area += area
                continue

            national_price = effective_national_lookup.get((scenario_year, crop_key))
            if national_price is not None:
                hybrid_prices[key] = float(national_price)
                zero_fill_keys += 1
                zero_fill_area += area
                continue

            hybrid_prices[key] = float(value) * float(crop_ratios.get(crop_key, 1.0))
            ratio_fallback_keys += 1
            ratio_fallback_area += area

        context.msp_per_prod = hybrid_prices
        context.initial_state_profit = base._recompute_initial_state_profit(
            states=context.states,
            districts_by_state=context.districts_by_state,
            crops_by_pair=context.crops_by_pair,
            current_cereal_area=context.current_cereal_area,
            yield_data=context.yield_data,
            price_map=hybrid_prices,
            cost_per_prod=context.cost_per_prod,
        )

        total_keys = direct_keys + zero_fill_keys + ratio_fallback_keys
        total_area = direct_area + zero_fill_area + ratio_fallback_area
        coverage = {
            "panel": panel_key,
            "season": str(context.season),
            "scenario_year": scenario_year,
            "direct_keys": direct_keys,
            "zero_fill_keys": zero_fill_keys,
            "ratio_fallback_keys": ratio_fallback_keys,
            "direct_key_share": direct_keys / total_keys if total_keys else 0.0,
            "zero_fill_key_share": zero_fill_keys / total_keys if total_keys else 0.0,
            "ratio_fallback_key_share": ratio_fallback_keys / total_keys if total_keys else 0.0,
            "fallback_keys": ratio_fallback_keys,
            "direct_area_share": direct_area / total_area if total_area else 0.0,
            "zero_fill_area_share": zero_fill_area / total_area if total_area else 0.0,
            "ratio_fallback_area_share": ratio_fallback_area / total_area if total_area else 0.0,
            "fallback_area_share": ratio_fallback_area / total_area if total_area else 0.0,
        }
        return context, coverage

    base._apply_hybrid_price_to_dict_context = apply_to_dict_context
    base._apply_hybrid_price_to_season_context = apply_to_season_context


def write_supporting_tables(df: pd.DataFrame, out_dir: Path, scenario_year: str) -> None:
    ratio_summary = (
        df.groupby(["Year", "Crop"], as_index=False)
        .agg(
            n_states=("State", "nunique"),
            mean_rupee_per_kg=("rupee_per_kg", "mean"),
            mean_msp_rs_per_kg=("MSP_rs_per_kg", "mean"),
            mean_ratio_to_msp=("ratio_to_msp", "mean"),
            min_ratio_to_msp=("ratio_to_msp", "min"),
            max_ratio_to_msp=("ratio_to_msp", "max"),
        )
        .sort_values(["Year", "Crop"])
        .reset_index(drop=True)
    )
    source_breakdown = (
        df.assign(
            price_source=df["rupee_per_kg"].apply(
                lambda x: "state_positive"
                if pd.notna(x) and float(x) > 0
                else "zero_or_nonpositive"
            )
        )
        .groupby(["Year", "Crop", "price_source"], as_index=False)
        .agg(n_states=("State", "nunique"))
        .sort_values(["Year", "Crop", "price_source"])
        .reset_index(drop=True)
    )
    direct_prices = (
        df[df["Year"] == scenario_year]
        .assign(
            price_source=df.loc[df["Year"] == scenario_year, "rupee_per_kg"].apply(
                lambda x: "state_positive"
                if pd.notna(x) and float(x) > 0
                else "zero_or_nonpositive"
            )
        )
        .sort_values(["Crop", "State"])
        .reset_index(drop=True)
    )
    coverage_summary = (
        df.groupby(["Year", "Crop"], as_index=False)
        .agg(n_states=("State", "nunique"))
        .sort_values(["Year", "Crop"])
        .reset_index(drop=True)
    )
    ratio_summary.to_csv(out_dir / "stateprice_csv_ratio_summary.csv", index=False)
    direct_prices.to_csv(out_dir / f"stateprice_csv_direct_prices_{scenario_year}.csv", index=False)
    coverage_summary.to_csv(out_dir / "stateprice_csv_crop_year_coverage.csv", index=False)
    source_breakdown.to_csv(out_dir / "stateprice_csv_source_breakdown.csv", index=False)


def write_run_note(
    *,
    price_csv: Path,
    out_dir: Path,
    fig_dir: Path,
    scenario_year: str,
    bootstrap_iterations: int,
    scenarios: dict[str, dict[str, float]],
) -> None:
    run_note = {
        "price_csv": str(price_csv),
        "scenario_year": scenario_year,
        "bootstrap_iterations": bootstrap_iterations,
        "figure_dir": str(fig_dir),
        "data_dir": str(out_dir),
        "available_years": sorted(scenarios.keys()),
        "crop_ratios_for_selected_year": scenarios.get(scenario_year, {}),
    }
    (out_dir / "sandbox_run_config.json").write_text(
        json.dumps(run_note, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _panel_b_display_change(metric: str, pct_reduction: float, original_total: float) -> float:
    del metric
    pct = float(pct_reduction)
    if pd.notna(original_total) and float(original_total) < 0:
        return pct
    return -pct


def _build_signed_panel_b(summary: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    base.plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "font.family": "DejaVu Sans",
        }
    )

    metric_order = [label for label, _ in base.METRICS]
    water = summary[summary["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    nitrogen = summary[summary["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]
    positions = base.np.arange(len(metric_order))
    offset = 0.18
    bar_height = 0.32

    fig, ax = base.plt.subplots(figsize=(7.6, 5.0), constrained_layout=True)
    ax.barh(
        positions - offset,
        water["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#2a9d8f",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )
    ax.barh(
        positions + offset,
        nitrogen["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )

    for frame, y_shift in ((water, -offset), (nitrogen, offset)):
        ax.errorbar(
            frame["center_display_pct"].to_numpy(),
            positions + y_shift,
            xerr=base.np.vstack(
                [
                    frame["lower_err_display"].to_numpy(dtype=float),
                    frame["upper_err_display"].to_numpy(dtype=float),
                ]
            ),
            fmt="none",
            ecolor="#303030",
            elinewidth=1.0,
            capsize=2.6,
            zorder=4,
        )

    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.set_yticks(positions)
    ax.set_yticklabels(metric_order)
    ax.invert_yaxis()
    ax.set_xlabel("Change relative to baseline (%)")
    ax.text(-0.12, 1.02, "b", transform=ax.transAxes, fontsize=12, fontweight="bold", va="bottom")
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    handles = [
        base.plt.Rectangle((0, 0), 1, 1, facecolor="#2a9d8f", edgecolor="black", linewidth=0.5),
        base.plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        base.Line2D([0], [0], color="#303030", linestyle="-", linewidth=1.0),
    ]
    labels = ["Water-based", "Nitrogen-based", "95% bootstrap interval"]
    ax.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.53, 1.015),
        ncol=3,
        frameon=False,
        fontsize=7.2,
        handlelength=1.8,
        borderaxespad=0.0,
        columnspacing=1.0,
    )

    x_min = min(
        float((water["center_display_pct"] - water["lower_err_display"]).min()),
        float((nitrogen["center_display_pct"] - nitrogen["lower_err_display"]).min()),
    )
    x_max = max(
        float((water["center_display_pct"] + water["upper_err_display"]).max()),
        float((nitrogen["center_display_pct"] + nitrogen["upper_err_display"]).max()),
    )
    left = min(-52.0, x_min - 4.0)
    right = max(30.0, x_max + 4.0)
    ax.set_xlim(left, right)

    fig.savefig(out_png, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    base.plt.close(fig)


def postprocess_panel_b_outputs() -> None:
    values_csv = base.OUT_DIR / "figure2_main_panel_b_values.csv"
    if not values_csv.exists():
        return

    table = pd.read_csv(values_csv)
    table["display_pct_change"] = table.apply(
        lambda row: _panel_b_display_change(row["metric"], row["pct_reduction"], row["original_total"]),
        axis=1,
    )
    table.to_csv(values_csv, index=False)

    bootstrap_dir = base.OUT_DIR / "panel_b_bootstrap"
    summary_csv = bootstrap_dir / "figure2_main_panel_b_bootstrap_summary.csv"
    iterations_csv = bootstrap_dir / "figure2_main_panel_b_bootstrap_iterations.csv"
    if iterations_csv.exists():
        iterations = pd.read_csv(iterations_csv)
        original_lookup = {
            (row["scenario"], row["metric"]): float(row["original_total"])
            for _, row in table.iterrows()
        }
        iterations["display_pct_change"] = iterations.apply(
            lambda row: _panel_b_display_change(
                row["metric"],
                row["pct_reduction"],
                original_lookup.get((row["scenario"], row["metric"]), float("nan")),
            ),
            axis=1,
        )
        iterations.to_csv(iterations_csv, index=False)

    if summary_csv.exists():
        summary = pd.read_csv(summary_csv)
        original_lookup = {
            (row["scenario"], row["metric"]): float(row["original_total"])
            for _, row in table.iterrows()
        }

        def transform(metric: str, pct_value: float, scenario: str) -> float:
            original_total = original_lookup.get((scenario, metric), float("nan"))
            return _panel_b_display_change(metric, pct_value, original_total)

        summary["center_display_pct"] = summary.apply(
            lambda row: transform(row["metric"], row["center_pct_reduction"], row["scenario"]),
            axis=1,
        )
        summary["bootstrap_mean_display_pct"] = summary.apply(
            lambda row: transform(row["metric"], row["bootstrap_mean_pct_reduction"], row["scenario"]),
            axis=1,
        )
        summary["display_interval_low_raw"] = summary.apply(
            lambda row: transform(row["metric"], row["bootstrap_p2_5_pct_reduction"], row["scenario"]),
            axis=1,
        )
        summary["display_interval_high_raw"] = summary.apply(
            lambda row: transform(row["metric"], row["bootstrap_p97_5_pct_reduction"], row["scenario"]),
            axis=1,
        )
        summary["display_interval_low"] = summary[["display_interval_low_raw", "display_interval_high_raw"]].min(axis=1)
        summary["display_interval_high"] = summary[["display_interval_low_raw", "display_interval_high_raw"]].max(axis=1)
        summary["lower_err_display"] = summary.apply(
            lambda row: float(row["center_display_pct"])
            - min(
                float(row["center_display_pct"]),
                float(row["display_interval_low"]),
                float(row["display_interval_high"]),
            ),
            axis=1,
        )
        summary["upper_err_display"] = summary.apply(
            lambda row: max(
                float(row["center_display_pct"]),
                float(row["display_interval_low"]),
                float(row["display_interval_high"]),
            )
            - float(row["center_display_pct"]),
            axis=1,
        )
        summary = summary.drop(columns=["display_interval_low_raw", "display_interval_high_raw"])
        summary.to_csv(summary_csv, index=False)
        _build_signed_panel_b(
            summary,
            base.FIG_DIR / "figure2_main_panel_b.png",
            base.FIG_DIR / "figure2_main_panel_b.pdf",
        )
    else:
        base.build_endpoint_figure(
            table,
            base.FIG_DIR / "figure2_main_panel_b.png",
            base.FIG_DIR / "figure2_main_panel_b.pdf",
        )

    base._assemble_composite()


def main(
    *,
    price_csv: Path,
    sandbox_root: Path,
    scenario_year: str,
    bootstrap_iterations: int,
    bootstrap_seed: int,
) -> None:
    fig_dir, out_dir = configure_base_paths(sandbox_root)
    price_df = load_stateprice_csv(price_csv)
    ratio_scenarios = build_ratio_scenarios_from_stateprice(price_df)
    if scenario_year not in ratio_scenarios:
        available = ", ".join(sorted(ratio_scenarios))
        raise ValueError(f"Scenario year {scenario_year!r} not found in {price_csv}. Available: {available}")
    state_price_lookup, national_price_lookup, zero_state_keys = build_stateprice_inputs(price_df)
    write_supporting_tables(price_df, out_dir, scenario_year)
    write_run_note(
        price_csv=price_csv,
        out_dir=out_dir,
        fig_dir=fig_dir,
        scenario_year=scenario_year,
        bootstrap_iterations=bootstrap_iterations,
        scenarios=ratio_scenarios,
    )

    base.load_ratio_scenarios = lambda: ratio_scenarios
    base.load_state_price_lookup = lambda: state_price_lookup
    patch_base_price_application(
        state_price_lookup=state_price_lookup,
        national_price_lookup=national_price_lookup,
        zero_state_keys=zero_state_keys,
    )
    base.main(
        scenario_year=scenario_year,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_seed=bootstrap_seed,
    )
    postprocess_panel_b_outputs()

    print(f"sandbox_root: {sandbox_root}")
    print(f"figure_png: {base.COMPOSITE_PNG}")
    print(f"figure_pdf: {base.COMPOSITE_PDF}")
    print(f"summary_csv: {base.SUMMARY_CSV}")
    print(f"coverage_csv: {base.COVERAGE_CSV}")
    print(f"audit_md: {base.AUDIT_MD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a sandbox Figure 2 rebuild using a statewise realized-price CSV."
    )
    parser.add_argument(
        "--price-csv",
        type=Path,
        default=DEFAULT_PRICE_CSV,
        help="CSV with Crop, State, Year, rupee_per_kg, and MSP_rs_per_kg columns.",
    )
    parser.add_argument(
        "--scenario-year",
        default=DEFAULT_SCENARIO_YEAR,
        help="Benchmark year to apply from the statewise realized-price CSV.",
    )
    parser.add_argument(
        "--sandbox-root",
        type=Path,
        default=ROOT / "sandbox" / DEFAULT_SANDBOX_NAME,
        help="Output root for the sandbox run.",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=500,
        help="Bootstrap iterations for panel b whiskers.",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=42,
        help="Random seed for the optional panel b bootstrap.",
    )
    args = parser.parse_args()
    main(
        price_csv=args.price_csv,
        sandbox_root=args.sandbox_root,
        scenario_year=args.scenario_year,
        bootstrap_iterations=args.bootstrap_iterations,
        bootstrap_seed=args.bootstrap_seed,
    )
