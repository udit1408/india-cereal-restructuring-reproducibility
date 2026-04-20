#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
import time
import types
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "working_variants"
OUT_DIR = ROOT / "data" / "generated" / "figure2_main"
DEFAULT_SCENARIO_YEAR = "2017-18"


def _relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _ensure_geopandas_stub() -> None:
    if "geopandas" not in sys.modules:
        sys.modules["geopandas"] = types.ModuleType("geopandas")


_ensure_geopandas_stub()
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

import generate_figure2c as figure2c_mod  # noqa: E402
import generate_figure2d_clean as figure2d_mod  # noqa: E402
from bootstrap_figure2b_no_historical_cap_core import (  # noqa: E402
    build_summary as build_panel_b_bootstrap_summary,
    deterministic_reproduction as bootstrap_deterministic_reproduction,
    load_sampling_pools as load_panel_b_sampling_pools,
    run_bootstrap as run_panel_b_bootstrap,
)
from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context as build_endpoint_context,
    build_figure as build_endpoint_figure,
    build_metric_table,
    write_latex_table,
)
from generate_figure2c import (  # noqa: E402
    NOTEBOOKS as CULTURAL_NOTEBOOKS,
    SeasonContext,
    build_context as build_cultural_context,
    combine_seasons,
    solve_season,
)
from generate_figure2d_clean import (  # noqa: E402
    _ordered_crops,
    build_crop_summary,
    build_transition_matrix,
    pivot_transition_matrix,
    solve_nitrogen_focused_areas,
)
from generate_si_revenue_profit_sensitivity import (  # noqa: E402
    canon,
    load_national_price_lookup,
    load_ratio_scenarios,
    load_state_price_lookup,
    load_unusable_direct_price_keys,
)
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    DEFAULT_ALPHAS,
    _baseline_violation_summary,
    _build_problem,
    _build_season_context,
    _plot_combined,
)


PANEL_FILES = {
    "a": FIG_DIR / "figure2_main_panel_a.png",
    "b": FIG_DIR / "figure2_main_panel_b.png",
    "c": FIG_DIR / "figure2_main_panel_c.png",
    "d": FIG_DIR / "figure2_main_panel_d.png",
}
COMPOSITE_PNG = FIG_DIR / "figure2_main.png"
COMPOSITE_PDF = FIG_DIR / "figure2_main.pdf"
SUMMARY_CSV = OUT_DIR / "figure2_main_summary.csv"
AUDIT_MD = OUT_DIR / "figure2_main_audit.md"
COVERAGE_CSV = OUT_DIR / "figure2_main_price_coverage.csv"
MANIFEST_MD = OUT_DIR / "figure2_main_manifest.md"
PANEL_B_BOOTSTRAP_DIR = OUT_DIR / "panel_b_bootstrap"

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


def _crop_key(crop: object) -> str:
    return str(crop).strip().lower()


def _recompute_initial_state_profit(
    *,
    states: list[str],
    districts_by_state: dict[str, list[str]],
    crops_by_pair: dict[tuple[str, str], list[str]],
    current_cereal_area: dict[tuple[str, str, str], float],
    yield_data: dict[tuple[str, str, str], float],
    price_map: dict[tuple[str, str, str], float],
    cost_per_prod: dict[tuple[str, str, str], float],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for state in states:
        total = 0.0
        for district in districts_by_state.get(state, []):
            for crop in crops_by_pair.get((state, district), []):
                key = (state, district, crop)
                total += (
                    current_cereal_area.get(key, 0.0)
                    * yield_data.get(key, 0.0)
                    * 0.01
                    * (price_map.get(key, 0.0) - cost_per_prod.get(key, 0.0))
                )
        out[state] = float(total)
    return out


def _current_cereal_area_from_dict_context(
    context: dict[str, object],
) -> dict[tuple[str, str, str], float]:
    if "current_cereal_area" in context:
        return context["current_cereal_area"]
    frame = context.get("frame")
    if frame is None:
        raise KeyError("current_cereal_area")
    return (
        frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()
    )


def _apply_hybrid_price_to_dict_context(
    base_context: dict[str, object],
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
    panel_key: str,
) -> tuple[dict[str, object], dict[str, object]]:
    context = copy.deepcopy(base_context)
    hybrid_prices: dict[tuple[str, str, str], float] = {}
    direct_keys = 0
    national_mean_keys = 0
    fallback_keys = 0
    direct_area = 0.0
    national_mean_area = 0.0
    fallback_area = 0.0
    national_price_lookup = national_price_lookup or {}
    unusable_direct_keys = unusable_direct_keys or set()

    current_cereal_area = _current_cereal_area_from_dict_context(context)
    context["current_cereal_area"] = current_cereal_area
    for key, value in context["msp_per_prod"].items():
        state, _, crop = key
        key_lookup = (scenario_year, canon(state), canon(crop))
        direct_price = state_price_lookup.get(key_lookup)
        area = float(current_cereal_area.get(key, 0.0))
        if direct_price is not None:
            hybrid_prices[key] = float(direct_price)
            direct_keys += 1
            direct_area += area
        elif key_lookup in unusable_direct_keys:
            national_price = national_price_lookup.get((scenario_year, canon(crop)))
            if national_price is not None:
                hybrid_prices[key] = float(national_price)
                national_mean_keys += 1
                national_mean_area += area
            else:
                hybrid_prices[key] = float(value) * float(crop_ratios.get(_crop_key(crop), 1.0))
                fallback_keys += 1
                fallback_area += area
        else:
            hybrid_prices[key] = float(value) * float(crop_ratios.get(_crop_key(crop), 1.0))
            fallback_keys += 1
            fallback_area += area

    context["msp_per_prod"] = hybrid_prices
    context["initial_state_profit"] = _recompute_initial_state_profit(
        states=context["states"],
        districts_by_state=context["districts_by_state"],
        crops_by_pair=context["crops_by_pair"],
        current_cereal_area=context["current_cereal_area"],
        yield_data=context["yield_data"],
        price_map=hybrid_prices,
        cost_per_prod=context["cost_per_prod"],
    )

    total_keys = direct_keys + national_mean_keys + fallback_keys
    total_area = direct_area + national_mean_area + fallback_area
    coverage = {
        "panel": panel_key,
        "season": str(context["season"]),
        "scenario_year": scenario_year,
        "direct_keys": direct_keys,
        "national_mean_keys": national_mean_keys,
        "fallback_keys": fallback_keys,
        "direct_key_share": direct_keys / total_keys if total_keys else np.nan,
        "national_mean_key_share": national_mean_keys / total_keys if total_keys else np.nan,
        "fallback_key_share": fallback_keys / total_keys if total_keys else np.nan,
        "direct_area_share": direct_area / total_area if total_area else np.nan,
        "national_mean_area_share": national_mean_area / total_area if total_area else np.nan,
        "fallback_area_share": fallback_area / total_area if total_area else np.nan,
    }
    return context, coverage


def _apply_hybrid_price_to_season_context(
    base_context: SeasonContext,
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
    panel_key: str,
) -> tuple[SeasonContext, dict[str, object]]:
    context = copy.deepcopy(base_context)
    hybrid_prices: dict[tuple[str, str, str], float] = {}
    direct_keys = 0
    national_mean_keys = 0
    fallback_keys = 0
    direct_area = 0.0
    national_mean_area = 0.0
    fallback_area = 0.0
    national_price_lookup = national_price_lookup or {}
    unusable_direct_keys = unusable_direct_keys or set()

    for key, value in context.msp_per_prod.items():
        state, _, crop = key
        key_lookup = (scenario_year, canon(state), canon(crop))
        direct_price = state_price_lookup.get(key_lookup)
        area = float(context.current_cereal_area.get(key, 0.0))
        if direct_price is not None:
            hybrid_prices[key] = float(direct_price)
            direct_keys += 1
            direct_area += area
        elif key_lookup in unusable_direct_keys:
            national_price = national_price_lookup.get((scenario_year, canon(crop)))
            if national_price is not None:
                hybrid_prices[key] = float(national_price)
                national_mean_keys += 1
                national_mean_area += area
            else:
                hybrid_prices[key] = float(value) * float(crop_ratios.get(_crop_key(crop), 1.0))
                fallback_keys += 1
                fallback_area += area
        else:
            hybrid_prices[key] = float(value) * float(crop_ratios.get(_crop_key(crop), 1.0))
            fallback_keys += 1
            fallback_area += area

    context.msp_per_prod = hybrid_prices
    context.initial_state_profit = _recompute_initial_state_profit(
        states=context.states,
        districts_by_state=context.districts_by_state,
        crops_by_pair=context.crops_by_pair,
        current_cereal_area=context.current_cereal_area,
        yield_data=context.yield_data,
        price_map=hybrid_prices,
        cost_per_prod=context.cost_per_prod,
    )

    total_keys = direct_keys + national_mean_keys + fallback_keys
    total_area = direct_area + national_mean_area + fallback_area
    coverage = {
        "panel": panel_key,
        "season": str(context.season),
        "scenario_year": scenario_year,
        "direct_keys": direct_keys,
        "national_mean_keys": national_mean_keys,
        "fallback_keys": fallback_keys,
        "direct_key_share": direct_keys / total_keys if total_keys else np.nan,
        "national_mean_key_share": national_mean_keys / total_keys if total_keys else np.nan,
        "fallback_key_share": fallback_keys / total_keys if total_keys else np.nan,
        "direct_area_share": direct_area / total_area if total_area else np.nan,
        "national_mean_area_share": national_mean_area / total_area if total_area else np.nan,
        "fallback_area_share": fallback_area / total_area if total_area else np.nan,
    }
    return context, coverage


def _build_panel_a(
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
) -> tuple[pd.DataFrame, list[dict[str, object]], list[dict[str, object]]]:
    layout = default_layout(AUDIT_ROOT)
    contexts: dict[str, dict[str, object]] = {}
    coverage_rows: list[dict[str, object]] = []
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        base_context = _build_season_context(layout, season, notebook_name)
        context, coverage = _apply_hybrid_price_to_dict_context(
            base_context,
            scenario_year=scenario_year,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
            panel_key="a",
        )
        contexts[season] = context
        coverage_rows.append(coverage)

    baseline_summaries = {
        season: _baseline_violation_summary(context, use_historical_caps=False)
        for season, context in contexts.items()
    }
    rows_by_season = {
        season: [
            _build_problem(
                context,
                alpha,
                solver_name="highs",
                income_mode="profit",
                objective_mode="normalized",
                use_historical_caps=False,
            )
            for alpha in DEFAULT_ALPHAS
        ]
        for season, context in contexts.items()
    }
    kharif = pd.DataFrame(rows_by_season["kharif"]).sort_values("Alpha").reset_index(drop=True)
    rabi = pd.DataFrame(rows_by_season["rabi"]).sort_values("Alpha").reset_index(drop=True)
    combined = (
        kharif.merge(rabi, on="Alpha", suffixes=("_kharif", "_rabi"), how="inner")
        .sort_values("Alpha")
        .reset_index(drop=True)
    )
    combined["objective_nitrogen"] = combined["objective_nitrogen_kharif"] + combined["objective_nitrogen_rabi"]
    combined["objective_water"] = combined["objective_water_kharif"] + combined["objective_water_rabi"]
    combined["nitrogen_mt"] = combined["objective_nitrogen"] / 1e9
    combined["water_bcm"] = combined["objective_water"] / 1e9
    combined["is_valid"] = combined["is_valid_kharif"] & combined["is_valid_rabi"]
    combined["solve_status"] = combined["solve_status_kharif"] + "|" + combined["solve_status_rabi"]
    baseline_n_surplus = sum(float(context["baseline_n_surplus"]) for context in contexts.values())
    baseline_water = sum(float(context["baseline_water"]) for context in contexts.values())
    combined["nitrogen_pct_of_2017_baseline"] = 100.0 * combined["objective_nitrogen"] / baseline_n_surplus
    combined["water_pct_of_2017_baseline"] = 100.0 * combined["objective_water"] / baseline_water

    kharif.to_csv(OUT_DIR / "figure2_main_panel_a_kharif_by_alpha.csv", index=False)
    rabi.to_csv(OUT_DIR / "figure2_main_panel_a_rabi_by_alpha.csv", index=False)
    combined.to_csv(OUT_DIR / "figure2_main_panel_a_combined_by_alpha.csv", index=False)

    _plot_combined(
        combined,
        FIG_DIR,
        x_column="nitrogen_mt",
        y_column="water_bcm",
        x_label="Nitrogen surplus (Tg N)",
        y_label="Consumptive water demand (BCM)",
        stem="figure2_main_panel_a",
    )
    _plot_combined(
        combined,
        FIG_DIR,
        x_column="nitrogen_pct_of_2017_baseline",
        y_column="water_pct_of_2017_baseline",
        x_label="Nitrogen surplus (% of 2017 baseline)",
        y_label="Consumptive water demand (% of 2017 baseline)",
        stem="figure2_main_panel_a_pct_2017_baseline",
    )

    summary_rows: list[dict[str, object]] = []
    valid = combined[combined["is_valid"]].copy()
    if not valid.empty:
        water_focus = valid.loc[valid["Alpha"].idxmin()]
        nitrogen_focus = valid.loc[valid["Alpha"].idxmax()]
        summary_rows.extend(
            [
                {
                    "panel": "a",
                    "scenario_year": scenario_year,
                    "strategy": "Water based",
                    "metric": "Nitrogen surplus (Tg N)",
                    "value": float(water_focus["nitrogen_mt"]),
                },
                {
                    "panel": "a",
                    "scenario_year": scenario_year,
                    "strategy": "Water based",
                    "metric": "Water demand (BCM)",
                    "value": float(water_focus["water_bcm"]),
                },
                {
                    "panel": "a",
                    "scenario_year": scenario_year,
                    "strategy": "Nitrogen based",
                    "metric": "Nitrogen surplus (Tg N)",
                    "value": float(nitrogen_focus["nitrogen_mt"]),
                },
                {
                    "panel": "a",
                    "scenario_year": scenario_year,
                    "strategy": "Nitrogen based",
                    "metric": "Water demand (BCM)",
                    "value": float(nitrogen_focus["water_bcm"]),
                },
            ]
        )

    for season, baseline_summary in baseline_summaries.items():
        summary_rows.append(
            {
                "panel": "a",
                "scenario_year": scenario_year,
                "strategy": season,
                "metric": "Worst baseline income gap",
                "value": float(baseline_summary["worst_income_gap"]),
            }
        )

    return combined, coverage_rows, summary_rows


def _build_panel_b_whisker_figure(summary: pd.DataFrame, out_png: Path, out_pdf: Path) -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "font.family": "DejaVu Sans",
        }
    )

    metric_order = [label for label, _ in METRICS]
    water = summary[summary["scenario"] == "Water based"].set_index("metric").loc[metric_order]
    nitrogen = summary[summary["scenario"] == "Nitrogen based"].set_index("metric").loc[metric_order]
    positions = np.arange(len(metric_order))
    offset = 0.18
    bar_height = 0.32

    fig, ax = plt.subplots(figsize=(7.6, 5.0), constrained_layout=True)
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
            xerr=np.vstack(
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
        plt.Rectangle((0, 0), 1, 1, facecolor="#2a9d8f", edgecolor="black", linewidth=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        Line2D([0], [0], color="#303030", linestyle="-", linewidth=1.0),
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
    ax.set_xlim(min(-52.0, x_min - 4.0), max(30.0, x_max + 4.0))

    fig.savefig(out_png, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(out_pdf, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def _write_panel_b_bootstrap_audit(
    *,
    summary: pd.DataFrame,
    reproduction: pd.DataFrame,
    iterations: pd.DataFrame,
    scenario_year: str,
    n_iterations: int,
    elapsed_seconds: float,
) -> None:
    lines = [
        "# figure2_main panel b bootstrap audit",
        "",
        f"This bootstrap adds whiskers to the primary Figure 2(b) rebuild under the {scenario_year} realized-price benchmark.",
        "The revenue benchmark is held fixed across iterations. Uncertainty is propagated by resampling",
        "district-level historical coefficient fields for water demand, nitrogen application, and phosphorus",
        "application in the same style as the primary Figure 2(b) whisker workflow.",
        "",
        "This means the whiskers reflect optimization sensitivity to agronomic coefficient variation under",
        "the realized-price benchmark, rather than a second ad hoc uncertainty model for realized prices.",
        "",
        f"Bootstrap iterations requested: {n_iterations}",
        f"Elapsed time (s): {elapsed_seconds:.2f}",
        "",
        "## Deterministic reproduction check",
        "",
    ]
    for row in reproduction.itertuples(index=False):
        lines.append(
            f"- {row.scenario} | {row.metric}: reproduced {row.reproduced_pct_reduction:.3f}%, center {row.center_pct_reduction:.3f}%, delta {row.delta_pct_points:.3f} pp ({row.solver_status})"
        )

    lines.extend(["", "## Bootstrap feasibility", ""])
    status_counts = (
        iterations[["iteration", "scenario", "status"]]
        .drop_duplicates()
        .groupby(["scenario", "status"])
        .size()
        .reset_index(name="n")
    )
    for row in status_counts.itertuples(index=False):
        lines.append(f"- {row.scenario} | {row.status}: {row.n}")

    lines.extend(["", "## Summary by metric", ""])
    for row in summary.itertuples(index=False):
        lines.append(
            f"- {row.scenario} | {row.metric}: center {row.center_pct_reduction:.3f}%, mean {row.bootstrap_mean_pct_reduction:.3f}%, 95% CI [{row.bootstrap_p2_5_pct_reduction:.3f}, {row.bootstrap_p97_5_pct_reduction:.3f}]%, optimal {row.n_optimal}/{row.n_total}"
        )

    (PANEL_B_BOOTSTRAP_DIR / "figure2_main_panel_b_bootstrap_audit.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _build_panel_b_with_bootstrap(
    *,
    table: pd.DataFrame,
    contexts: dict[str, dict[str, object]],
    layout,
    scenario_year: str,
    bootstrap_iterations: int,
    bootstrap_seed: int,
) -> None:
    PANEL_B_BOOTSTRAP_DIR.mkdir(parents=True, exist_ok=True)
    pools = {
        season: load_panel_b_sampling_pools(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    start = time.time()
    reproduction = bootstrap_deterministic_reproduction(contexts, table)
    iterations = run_panel_b_bootstrap(contexts, pools, bootstrap_iterations, bootstrap_seed)
    summary = build_panel_b_bootstrap_summary(iterations, table)
    elapsed = time.time() - start

    reproduction.to_csv(
        PANEL_B_BOOTSTRAP_DIR / "figure2_main_panel_b_deterministic_reproduction_check.csv",
        index=False,
    )
    iterations.to_csv(
        PANEL_B_BOOTSTRAP_DIR / "figure2_main_panel_b_bootstrap_iterations.csv",
        index=False,
    )
    summary.to_csv(
        PANEL_B_BOOTSTRAP_DIR / "figure2_main_panel_b_bootstrap_summary.csv",
        index=False,
    )

    _build_panel_b_whisker_figure(
        summary,
        FIG_DIR / "figure2_main_panel_b.png",
        FIG_DIR / "figure2_main_panel_b.pdf",
    )
    _write_panel_b_bootstrap_audit(
        summary=summary,
        reproduction=reproduction,
        iterations=iterations,
        scenario_year=scenario_year,
        n_iterations=bootstrap_iterations,
        elapsed_seconds=elapsed,
    )


def _build_panel_b(
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
    bootstrap_iterations: int = 0,
    bootstrap_seed: int = 42,
) -> tuple[pd.DataFrame, list[dict[str, object]], list[dict[str, object]]]:
    layout = default_layout(AUDIT_ROOT)
    contexts: dict[str, dict[str, object]] = {}
    coverage_rows: list[dict[str, object]] = []
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        base_context = build_endpoint_context(layout, season, notebook_name)
        context, coverage = _apply_hybrid_price_to_dict_context(
            base_context,
            scenario_year=scenario_year,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
            panel_key="b",
        )
        contexts[season] = context
        coverage_rows.append(coverage)

    table, _statuses = build_metric_table(contexts, use_historical_caps=False)
    table.to_csv(OUT_DIR / "figure2_main_panel_b_values.csv", index=False)
    write_latex_table(table, OUT_DIR / "figure2_main_panel_b_values.tex")
    if bootstrap_iterations > 0:
        _build_panel_b_with_bootstrap(
            table=table,
            contexts=contexts,
            layout=layout,
            scenario_year=scenario_year,
            bootstrap_iterations=bootstrap_iterations,
            bootstrap_seed=bootstrap_seed,
        )
    else:
        build_endpoint_figure(
            table,
            FIG_DIR / "figure2_main_panel_b.png",
            FIG_DIR / "figure2_main_panel_b.pdf",
        )

    summary_rows = []
    for row in table.itertuples(index=False):
        summary_rows.append(
            {
                "panel": "b",
                "scenario_year": scenario_year,
                "strategy": row.scenario,
                "metric": row.metric,
                "value": float(row.pct_reduction),
            }
        )
    return table, coverage_rows, summary_rows


def _build_panel_c(
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
) -> tuple[pd.DataFrame, list[dict[str, object]], list[dict[str, object]]]:
    coverage_rows: list[dict[str, object]] = []
    contexts: dict[str, SeasonContext] = {}
    for season, config in CULTURAL_NOTEBOOKS.items():
        base_context = build_cultural_context(config)
        context, coverage = _apply_hybrid_price_to_season_context(
            base_context,
            scenario_year=scenario_year,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
            panel_key="c",
        )
        contexts[season] = context
        coverage_rows.append(coverage)

    kharif = solve_season(contexts["kharif"], use_historical_caps=False, retention_level="state")
    rabi = solve_season(contexts["rabi"], use_historical_caps=False, retention_level="state")
    combined = combine_seasons(
        kharif,
        rabi,
        label=f"hybrid_{scenario_year}_state_retention_no_historical_caps",
    )

    kharif.to_csv(OUT_DIR / "figure2_main_panel_c_kharif.csv", index=False)
    rabi.to_csv(OUT_DIR / "figure2_main_panel_c_rabi.csv", index=False)
    combined.to_csv(OUT_DIR / "figure2_main_panel_c_combined.csv", index=False)

    original_fig_dir = figure2c_mod.FIG_DIR
    try:
        figure2c_mod.FIG_DIR = FIG_DIR
        figure2c_mod.plot_nominal_panel(combined, output_stem="figure2_main_panel_c")
    finally:
        figure2c_mod.FIG_DIR = original_fig_dir

    summary_rows = [
        {
            "panel": "c",
            "scenario_year": scenario_year,
            "strategy": "Combined",
            "metric": "Max nitrogen-surplus reduction (%)",
            "value": float(combined["pct_reduction_n_surplus"].max()),
        },
        {
            "panel": "c",
            "scenario_year": scenario_year,
            "strategy": "Combined",
            "metric": "Max realized staple replacement (%)",
            "value": float(combined["realized_staple_replacement_pct"].max()),
        },
    ]
    return combined, coverage_rows, summary_rows


def _build_panel_d(
    *,
    scenario_year: str,
    crop_ratios: dict[str, float],
    state_price_lookup: dict[tuple[str, str, str], float],
    national_price_lookup: dict[tuple[str, str], float] | None = None,
    unusable_direct_keys: set[tuple[str, str, str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]], list[dict[str, object]]]:
    layout = default_layout(AUDIT_ROOT)
    contexts: dict[str, dict[str, object]] = {}
    coverage_rows: list[dict[str, object]] = []
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        base_context = _build_season_context(layout, season, notebook_name)
        context, coverage = _apply_hybrid_price_to_dict_context(
            base_context,
            scenario_year=scenario_year,
            crop_ratios=crop_ratios,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            unusable_direct_keys=unusable_direct_keys,
            panel_key="d",
        )
        contexts[season] = context
        coverage_rows.append(coverage)

    solved_frames = []
    state_audits = []
    district_audits = []
    for season in ("kharif", "rabi"):
        area_frame, state_audit, district_audit = solve_nitrogen_focused_areas(
            contexts[season],
            solver_name="highs",
            income_mode="profit",
            use_historical_caps=False,
        )
        solved_frames.append(area_frame)
        state_audits.append(state_audit)
        district_audits.append(district_audit)

    combined_areas = pd.concat(solved_frames, ignore_index=True)
    combined_state_audit = pd.concat(state_audits, ignore_index=True)
    combined_district_audit = pd.concat(district_audits, ignore_index=True)
    crop_order = _ordered_crops(combined_areas)
    crop_summary = build_crop_summary(combined_areas, crop_order)
    transition_long = build_transition_matrix(combined_areas, crop_order)
    transition_matrix = pivot_transition_matrix(transition_long, crop_order)

    combined_areas.to_csv(OUT_DIR / "figure2_main_panel_d_optimized_areas.csv", index=False)
    combined_state_audit.to_csv(OUT_DIR / "figure2_main_panel_d_state_constraint_audit.csv", index=False)
    combined_district_audit.to_csv(OUT_DIR / "figure2_main_panel_d_district_area_audit.csv", index=False)
    crop_summary.to_csv(OUT_DIR / "figure2_main_panel_d_crop_summary.csv", index=False)
    transition_long.to_csv(OUT_DIR / "figure2_main_panel_d_transition_long.csv", index=False)
    transition_matrix.to_csv(OUT_DIR / "figure2_main_panel_d_transition_matrix.csv")

    original_fig_dir = figure2d_mod.FIG_DIR
    try:
        figure2d_mod.FIG_DIR = FIG_DIR
        figure2d_mod.plot_alluvial(
            transition_matrix,
            crop_summary,
            title=None,
            output_stem="figure2_main_panel_d",
        )
    finally:
        figure2d_mod.FIG_DIR = original_fig_dir

    summary_rows = []
    for row in crop_summary.itertuples(index=False):
        summary_rows.append(
            {
                "panel": "d",
                "scenario_year": scenario_year,
                "strategy": "Optimized share",
                "metric": f"{row.Crop} optimized area (ha)",
                "value": float(row.optimized_total_ha),
            }
        )
    return crop_summary, transition_long, coverage_rows, summary_rows


def _crop_white_margins(image: np.ndarray, *, threshold: float = 0.985, pad_px: int = 6) -> np.ndarray:
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


def _prepare_panel_image(key: str) -> np.ndarray:
    image = mpimg.imread(PANEL_FILES[key]).copy()
    erase_box = PANEL_LABEL_ERASE_BOXES.get(key)
    if erase_box is not None:
        x0, y0, x1, y1 = erase_box
        image[y0:y1, x0:x1, :3] = 1.0
        if image.shape[2] == 4:
            image[y0:y1, x0:x1, 3] = 1.0
    return _crop_white_margins(image, pad_px=PANEL_CROP_PAD_PX.get(key, 6))


def _assemble_composite() -> None:
    fig = plt.figure(figsize=(10.7, 7.1), facecolor="white")
    grid = GridSpec(2, 2, figure=fig, wspace=0.05, hspace=0.012)
    for idx, key in enumerate(["a", "b", "c", "d"]):
        ax = fig.add_subplot(grid[idx // 2, idx % 2])
        ax.imshow(_prepare_panel_image(key), aspect="auto")
        ax.axis("off")
        ax.text(
            0.012,
            0.988,
            key,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=15,
            fontweight="bold",
            color="black",
            clip_on=False,
        )
    fig.subplots_adjust(left=0.03, right=0.972, top=0.975, bottom=0.035)
    fig.savefig(COMPOSITE_PNG, dpi=400, facecolor="white")
    fig.savefig(COMPOSITE_PDF, dpi=400, facecolor="white")
    plt.close(fig)


def _write_audit(
    *,
    scenario_year: str,
    coverage: pd.DataFrame,
    panel_a: pd.DataFrame,
    panel_b: pd.DataFrame,
    panel_c: pd.DataFrame,
    panel_d_summary: pd.DataFrame,
) -> None:
    valid_a = panel_a[panel_a["is_valid"]].copy()
    water_focus = valid_a.loc[valid_a["Alpha"].idxmin()]
    nitrogen_focus = valid_a.loc[valid_a["Alpha"].idxmax()]

    rice_row = panel_d_summary.loc[panel_d_summary["Crop"] == "rice"]
    wheat_row = panel_d_summary.loc[panel_d_summary["Crop"] == "wheat"]

    lines = [
        "# figure2_main audit",
        "",
        f"This standalone figure reruns all Figure 2 panels on the primary no-hard-cap branch using the {scenario_year} realized-price benchmark.",
        "Matched official state-year realized prices are used where available, and unmatched state-crop combinations fall back to the crop-specific realized-price/MSP multiplier for the selected year.",
        "",
        "Price coverage by panel and season:",
    ]
    for row in coverage.sort_values(["panel", "season"]).itertuples(index=False):
        lines.append(
            f"- panel {row.panel} | {row.season}: direct realized-price coverage = {100.0 * float(row.direct_key_share):.2f}% of decision keys and {100.0 * float(row.direct_area_share):.2f}% of baseline cereal area"
        )

    lines.extend(
        [
            "",
            "Panel a endpoints:",
            f"- Water-based endpoint: {float(water_focus['nitrogen_mt']):.3f} Tg N and {float(water_focus['water_bcm']):.3f} BCM",
            f"- Nitrogen-based endpoint: {float(nitrogen_focus['nitrogen_mt']):.3f} Tg N and {float(nitrogen_focus['water_bcm']):.3f} BCM",
            "",
            "Panel b headline percentage reductions:",
        ]
    )
    for scenario in ("Water based", "Nitrogen based"):
        subset = panel_b[panel_b["scenario"] == scenario]
        water_change = float(subset.loc[subset["metric"] == "Water Demand", "pct_reduction"].iloc[0])
        nitrogen_change = float(subset.loc[subset["metric"] == "Nitrogen Surplus", "pct_reduction"].iloc[0])
        profit_change = float(subset.loc[subset["metric"] == "Profit", "pct_reduction"].iloc[0])
        calorie_change = float(subset.loc[subset["metric"] == "Calorie", "pct_reduction"].iloc[0])
        lines.append(
            f"- {scenario}: water {water_change:.3f}%, nitrogen surplus {nitrogen_change:.3f}%, profit {profit_change:.3f}%, calorie {calorie_change:.3f}%"
        )

    lines.extend(
        [
            "",
            "Panel c combined state-retention range:",
            f"- nitrogen-surplus reduction: {float(panel_c['pct_reduction_n_surplus'].min()):.3f}% to {float(panel_c['pct_reduction_n_surplus'].max()):.3f}%",
            f"- realized rice+wheat replacement: {float(panel_c['realized_staple_replacement_pct'].min()):.3f}% to {float(panel_c['realized_staple_replacement_pct'].max()):.3f}%",
        ]
    )
    if not rice_row.empty:
        rice = rice_row.iloc[0]
        lines.append(
            f"- rice area: {float(rice['original_total_ha']) / 1e6:.3f} to {float(rice['optimized_total_ha']) / 1e6:.3f} Mha"
        )
    if not wheat_row.empty:
        wheat = wheat_row.iloc[0]
        lines.append(
            f"- wheat area: {float(wheat['original_total_ha']) / 1e6:.3f} to {float(wheat['optimized_total_ha']) / 1e6:.3f} Mha"
        )
    AUDIT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_manifest() -> None:
    lines = [
        "# figure2_main manifest",
        "",
        "Composite outputs:",
        f"- {_relpath(COMPOSITE_PNG)}",
        f"- {_relpath(COMPOSITE_PDF)}",
        "",
        "Panel outputs:",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_a.png')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_a.pdf')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_a_pct_2017_baseline.png')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_a_pct_2017_baseline.pdf')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_b.png')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_b.pdf')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_c.png')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_c.pdf')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_d.png')}",
        f"- {_relpath(FIG_DIR / 'figure2_main_panel_d.pdf')}",
        "",
        "Tabular outputs:",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_a_kharif_by_alpha.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_a_rabi_by_alpha.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_a_combined_by_alpha.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_b_values.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_b_values.tex')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_c_kharif.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_c_rabi.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_c_combined.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_optimized_areas.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_state_constraint_audit.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_district_area_audit.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_crop_summary.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_transition_long.csv')}",
        f"- {_relpath(OUT_DIR / 'figure2_main_panel_d_transition_matrix.csv')}",
        f"- {_relpath(SUMMARY_CSV)}",
        f"- {_relpath(COVERAGE_CSV)}",
    ]
    if PANEL_B_BOOTSTRAP_DIR.exists():
        lines.extend(
            [
                f"- {_relpath(PANEL_B_BOOTSTRAP_DIR / 'figure2_main_panel_b_deterministic_reproduction_check.csv')}",
                f"- {_relpath(PANEL_B_BOOTSTRAP_DIR / 'figure2_main_panel_b_bootstrap_iterations.csv')}",
                f"- {_relpath(PANEL_B_BOOTSTRAP_DIR / 'figure2_main_panel_b_bootstrap_summary.csv')}",
            ]
        )
    lines.extend(
        [
            "",
            "Notes:",
            f"- {_relpath(AUDIT_MD)}",
        ]
    )
    if PANEL_B_BOOTSTRAP_DIR.exists():
        lines.append(f"- {_relpath(PANEL_B_BOOTSTRAP_DIR / 'figure2_main_panel_b_bootstrap_audit.md')}")
    MANIFEST_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(
    *,
    scenario_year: str = DEFAULT_SCENARIO_YEAR,
    bootstrap_iterations: int = 0,
    bootstrap_seed: int = 42,
) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ratio_scenarios = load_ratio_scenarios()
    if scenario_year not in ratio_scenarios:
        raise ValueError(f"Unsupported scenario year: {scenario_year}")
    state_price_lookup = load_state_price_lookup()
    national_price_lookup = load_national_price_lookup()
    unusable_direct_keys = load_unusable_direct_price_keys()
    crop_ratios = ratio_scenarios[scenario_year]

    panel_a, cov_a, summary_a = _build_panel_a(
        scenario_year=scenario_year,
        crop_ratios=crop_ratios,
        state_price_lookup=state_price_lookup,
        national_price_lookup=national_price_lookup,
        unusable_direct_keys=unusable_direct_keys,
    )
    panel_b, cov_b, summary_b = _build_panel_b(
        scenario_year=scenario_year,
        crop_ratios=crop_ratios,
        state_price_lookup=state_price_lookup,
        national_price_lookup=national_price_lookup,
        unusable_direct_keys=unusable_direct_keys,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_seed=bootstrap_seed,
    )
    panel_c, cov_c, summary_c = _build_panel_c(
        scenario_year=scenario_year,
        crop_ratios=crop_ratios,
        state_price_lookup=state_price_lookup,
        national_price_lookup=national_price_lookup,
        unusable_direct_keys=unusable_direct_keys,
    )
    panel_d_summary, _panel_d_transition, cov_d, summary_d = _build_panel_d(
        scenario_year=scenario_year,
        crop_ratios=crop_ratios,
        state_price_lookup=state_price_lookup,
        national_price_lookup=national_price_lookup,
        unusable_direct_keys=unusable_direct_keys,
    )

    _assemble_composite()

    coverage = pd.DataFrame(cov_a + cov_b + cov_c + cov_d)
    coverage.to_csv(COVERAGE_CSV, index=False)

    summary = pd.DataFrame(summary_a + summary_b + summary_c + summary_d)
    summary.to_csv(SUMMARY_CSV, index=False)

    _write_audit(
        scenario_year=scenario_year,
        coverage=coverage,
        panel_a=panel_a,
        panel_b=panel_b,
        panel_c=panel_c,
        panel_d_summary=panel_d_summary,
    )
    _write_manifest()

    print(f"figure_png: {COMPOSITE_PNG}")
    print(f"figure_pdf: {COMPOSITE_PDF}")
    print(f"summary_csv: {SUMMARY_CSV}")
    print(f"audit_md: {AUDIT_MD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the primary Figure 2 rebuild under the official realized-price benchmark."
    )
    parser.add_argument(
        "--scenario-year",
        default=DEFAULT_SCENARIO_YEAR,
        help="Realized-price benchmark year to apply in the state-price replacement (default: 2017-18).",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=0,
        help="If > 0, add bootstrap whiskers to panel b using the district-coefficient resampling workflow.",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=42,
        help="Random seed for the optional panel b bootstrap.",
    )
    args = parser.parse_args()
    main(
        scenario_year=args.scenario_year,
        bootstrap_iterations=args.bootstrap_iterations,
        bootstrap_seed=args.bootstrap_seed,
    )
