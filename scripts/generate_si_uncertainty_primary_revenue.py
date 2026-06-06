#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import copy
import io
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
OUT_DIR = ROOT / "data" / "generated" / "si_uncertainty_primary_revenue"
DEFAULT_SCENARIO_YEAR = "2017-18"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from bootstrap_figure2b_no_historical_cap_core import (  # noqa: E402
    draw_coefficients,
    load_sampling_pools,
)
from generate_Figure2_equivalent import (  # noqa: E402
    _apply_official_benchmark_to_dict_context,
    _prepare_panel_b_display_table,
)
from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context as build_endpoint_context,
    build_metric_table,
    metric_totals,
    signed_display_change,
    solve_endpoint,
)
from official_price_benchmark import (  # noqa: E402
    load_national_cost_lookup,
    load_national_price_lookup,
    load_state_cost_lookup,
    load_state_price_lookup,
)
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _prepare_namespace  # noqa: E402


SEASONAL_BOOTSTRAP_METRICS = [label for label, _ in METRICS]
SEASONAL_BOOTSTRAP_PLOT_METRICS = [label for label, _ in METRICS if label != "Net return"]
COMPONENT_ORDER = [
    ("Synthetic N", "N_applied(kg/ha)"),
    ("Manure N", "Manure (N_kg/ha)"),
    ("Atmospheric deposition", "atm_depo"),
    ("BNF input", "BNF_kg_per_hec"),
]
COMPONENT_METRICS = [
    "Nitrogen Surplus",
    "Greenhouse Gas emission",
    "Water Demand",
    "Calorie",
]
PERTURBATION_LABELS = {-0.10: "-10%", 0.10: "+10%"}
PERTURBATION_COLORS = {-0.10: "#4c78a8", 0.10: "#f58518"}
SEASON_FIGURES = {
    "kharif": {
        "bootstrap_png": FIG_DIR / "si_s8_kharif_bootstrap_uncertainty.png",
        "component_png": FIG_DIR / "si_s10_kharif_n_component_sensitivity.png",
    },
    "rabi": {
        "bootstrap_png": FIG_DIR / "si_s9_rabi_bootstrap_uncertainty.png",
        "component_png": FIG_DIR / "si_s11_rabi_n_component_sensitivity.png",
    },
}


def _build_official_contexts(
    scenario_year: str,
) -> tuple[dict[str, dict[str, object]], dict[str, pd.DataFrame], object]:
    layout = default_layout(AUDIT_ROOT)
    state_price_lookup = load_state_price_lookup()
    national_price_lookup = load_national_price_lookup()
    state_cost_lookup = load_state_cost_lookup()
    national_cost_lookup = load_national_cost_lookup()

    contexts: dict[str, dict[str, object]] = {}
    namespace_frames: dict[str, pd.DataFrame] = {}

    for season, notebook_name in SEASON_NOTEBOOKS.items():
        base_context = build_endpoint_context(layout, season, notebook_name)
        context, _coverage = _apply_official_benchmark_to_dict_context(
            base_context,
            scenario_year=scenario_year,
            state_price_lookup=state_price_lookup,
            national_price_lookup=national_price_lookup,
            state_cost_lookup=state_cost_lookup,
            national_cost_lookup=national_cost_lookup,
            panel_key=f"si_{season}",
        )
        contexts[season] = context

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            namespace = _prepare_namespace(layout, notebook_name)
        namespace_frames[season] = namespace["df"].copy()

    return contexts, namespace_frames, layout


def _single_scenario_summary(iterations: pd.DataFrame, center_table: pd.DataFrame) -> pd.DataFrame:
    center_map = {
        row.metric: (
            float(row.pct_reduction),
            float(row.display_pct_change),
            float(row.original_total),
            str(row.display_metric),
        )
        for row in center_table.itertuples(index=False)
    }

    rows: list[dict[str, object]] = []
    for metric, group in iterations.groupby("metric", sort=False):
        valid = group[group["status"] == "Optimal"]["pct_reduction"].astype(float)
        center_pct, center_display, original_total, display_metric = center_map[metric]
        if valid.empty:
            rows.append(
                {
                    "metric": metric,
                    "display_metric": display_metric,
                    "center_pct_reduction": center_pct,
                    "center_display_pct": center_display,
                    "bootstrap_mean_pct_reduction": np.nan,
                    "bootstrap_p2_5_pct_reduction": np.nan,
                    "bootstrap_p97_5_pct_reduction": np.nan,
                    "display_interval_low": np.nan,
                    "display_interval_high": np.nan,
                    "lower_err_display": np.nan,
                    "upper_err_display": np.nan,
                    "n_optimal": 0,
                    "n_total": int(group.shape[0]),
                }
            )
            continue

        p2_5 = float(valid.quantile(0.025))
        p97_5 = float(valid.quantile(0.975))
        display_values = valid.map(lambda value: signed_display_change(metric, value, original_total))
        display_mean = float(display_values.mean())
        display_p2_5 = signed_display_change(metric, p2_5, original_total)
        display_p97_5 = signed_display_change(metric, p97_5, original_total)
        raw_low = min(display_p2_5, display_p97_5)
        raw_high = max(display_p2_5, display_p97_5)
        display_low = center_display + (raw_low - display_mean)
        display_high = center_display + (raw_high - display_mean)
        rows.append(
            {
                "metric": metric,
                "display_metric": display_metric,
                "center_pct_reduction": center_pct,
                "center_display_pct": center_display,
                "bootstrap_mean_pct_reduction": float(valid.mean()),
                "bootstrap_p2_5_pct_reduction": p2_5,
                "bootstrap_p97_5_pct_reduction": p97_5,
                "display_interval_low": display_low,
                "display_interval_high": display_high,
                "lower_err_display": max(center_display - display_low, 0.0),
                "upper_err_display": max(display_high - center_display, 0.0),
                "n_optimal": int(valid.size),
                "n_total": int(group.shape[0]),
            }
        )

    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], categories=SEASONAL_BOOTSTRAP_METRICS, ordered=True)
    return out.sort_values("metric").reset_index(drop=True)


def _plot_single_strategy_bootstrap(summary: pd.DataFrame, out_path: Path) -> None:
    summary = summary[summary["metric"].astype(str) != "Net return"].reset_index(drop=True)

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

    positions = np.arange(summary.shape[0])
    fig, ax = plt.subplots(figsize=(7.4, 5.0), constrained_layout=True)
    ax.barh(
        positions,
        summary["center_display_pct"].to_numpy(dtype=float),
        height=0.48,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )
    ax.errorbar(
        summary["center_display_pct"].to_numpy(dtype=float),
        positions,
        xerr=np.vstack(
            [
                summary["lower_err_display"].to_numpy(dtype=float),
                summary["upper_err_display"].to_numpy(dtype=float),
            ]
        ),
        fmt="none",
        ecolor="#303030",
        elinewidth=1.0,
        capsize=2.8,
        zorder=4,
    )
    ax.axvline(0, color="black", linewidth=0.8, zorder=2)
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.6, linestyle="-", alpha=0.85, zorder=1)
    ax.set_yticks(positions)
    ax.set_yticklabels(summary["display_metric"].astype(str).tolist())
    ax.invert_yaxis()
    ax.set_xlabel("Change relative to baseline (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    x_min = float((summary["center_display_pct"] - summary["lower_err_display"]).min())
    x_max = float((summary["center_display_pct"] + summary["upper_err_display"]).max())
    ax.set_xlim(min(-55.0, x_min - 4.0), max(35.0, x_max + 4.0))

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="#d18f00", edgecolor="black", linewidth=0.5),
        plt.Line2D([0], [0], color="#303030", linewidth=1.0),
    ]
    ax.legend(
        handles,
        ["Nitrogen-based endpoint", "95% bootstrap interval"],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=2,
        frameon=False,
        fontsize=8.0,
        handlelength=1.8,
        columnspacing=1.2,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def _run_seasonal_bootstrap(
    season: str,
    context: dict[str, object],
    layout,
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    notebook_name = SEASON_NOTEBOOKS[season]
    pools = load_sampling_pools(layout, season, notebook_name)
    table, _statuses = build_metric_table({season: context}, use_historical_caps=False)
    table = _prepare_panel_b_display_table(table)
    center_table = (
        table[table["scenario"] == "Nitrogen based"]
        .copy()
        .loc[:, ["metric", "display_metric", "pct_reduction", "display_pct_change", "original_total"]]
    )

    rng = np.random.default_rng(seed)
    baseline_totals = metric_totals(context["current_cereal_area"], context)
    rows: list[dict[str, object]] = []
    for iteration in range(iterations):
        n_rate_iter, p_rate_iter, water_rate_iter = draw_coefficients(rng, context, pools)
        iter_context = dict(context)
        iter_context["nitrogen_rate"] = n_rate_iter
        iter_context["p_rate"] = p_rate_iter
        iter_context["water_rate"] = water_rate_iter
        status, area_map = solve_endpoint(iter_context, "nitrogen", use_historical_caps=False)
        optimized_totals = metric_totals(area_map, iter_context) if status == "Optimal" else {}
        for metric_label, metric_key in METRICS:
            pct_reduction = np.nan
            if status == "Optimal":
                baseline = baseline_totals[metric_key]
                pct_reduction = 100.0 * (baseline - optimized_totals[metric_key]) / baseline
            rows.append(
                {
                    "season": season,
                    "iteration": iteration,
                    "metric": metric_label,
                    "status": status,
                    "pct_reduction": pct_reduction,
                }
            )
    iterations_df = pd.DataFrame(rows)
    iterations_df["metric"] = pd.Categorical(
        iterations_df["metric"],
        categories=SEASONAL_BOOTSTRAP_METRICS,
        ordered=True,
    )
    summary_df = _single_scenario_summary(iterations_df, center_table)
    plot_summary_df = summary_df[summary_df["metric"].astype(str) != "Net return"].reset_index(drop=True)
    return iterations_df.sort_values(["iteration", "metric"]).reset_index(drop=True), plot_summary_df


def _component_maps(frame: pd.DataFrame) -> dict[str, dict[tuple[str, str, str], float]]:
    local = frame.copy()
    local["State"] = local["State"].astype(str)
    local["District"] = local["District"].astype(str)
    local["Crop"] = local["Crop"].astype(str)
    grouped = (
        local.groupby(["State", "District", "Crop"], as_index=False)[
            [column for _, column in COMPONENT_ORDER]
        ]
        .mean()
        .reset_index(drop=True)
    )
    out: dict[str, dict[tuple[str, str, str], float]] = {}
    for _, column in COMPONENT_ORDER:
        out[column] = (
            grouped.set_index(["State", "District", "Crop"])[column].astype(float).to_dict()
        )
    return out


def _metric_display_value(
    *,
    metric_label: str,
    original_total: float,
    optimized_total: float,
) -> tuple[str, float, float]:
    pct_reduction = 100.0 * (original_total - optimized_total) / original_total
    display_metric = metric_label
    display_pct_change = signed_display_change(metric_label, pct_reduction, original_total)
    if metric_label == "Net return" and original_total < 0:
        baseline_deficit = max(-original_total, 0.0)
        optimized_deficit = max(-optimized_total, 0.0)
        if baseline_deficit > 0:
            pct_reduction = 100.0 * (baseline_deficit - optimized_deficit) / baseline_deficit
        else:
            pct_reduction = 0.0
        display_metric = "Net-return deficit"
        display_pct_change = -pct_reduction
    return display_metric, pct_reduction, display_pct_change


def _run_component_sensitivity(
    season: str,
    context: dict[str, object],
    frame: pd.DataFrame,
) -> pd.DataFrame:
    component_maps = _component_maps(frame)
    rows: list[dict[str, object]] = []
    base_keys = list(context["nitrogen_rate"].keys())

    for component_label, component_column in COMPONENT_ORDER:
        component_map = component_maps[component_column]
        for perturbation, perturbation_label in PERTURBATION_LABELS.items():
            iter_context = dict(context)
            adjusted_n = dict(context["nitrogen_rate"])
            for key in base_keys:
                component_value = float(component_map.get(key, 0.0))
                adjusted_n[key] = max(0.0, adjusted_n[key] + perturbation * component_value)
            iter_context["nitrogen_rate"] = adjusted_n

            baseline_totals = metric_totals(iter_context["current_cereal_area"], iter_context)
            status, area_map = solve_endpoint(iter_context, "nitrogen", use_historical_caps=False)
            if status != "Optimal":
                raise RuntimeError(
                    f"Component sensitivity solve failed for season={season}, component={component_label}, perturbation={perturbation_label}"
                )
            optimized_totals = metric_totals(area_map, iter_context)

            for metric_label, metric_key in METRICS:
                if metric_label not in COMPONENT_METRICS:
                    continue
                display_metric, pct_reduction, display_pct_change = _metric_display_value(
                    metric_label=metric_label,
                    original_total=float(baseline_totals[metric_key]),
                    optimized_total=float(optimized_totals[metric_key]),
                )
                rows.append(
                    {
                        "season": season,
                        "component": component_label,
                        "perturbation": perturbation_label,
                        "metric": metric_label,
                        "display_metric": display_metric,
                        "pct_reduction": pct_reduction,
                        "display_pct_change": display_pct_change,
                    }
                )
    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], categories=COMPONENT_METRICS, ordered=True)
    return out.sort_values(["metric", "component", "perturbation"]).reset_index(drop=True)


def _plot_component_sensitivity(table: pd.DataFrame, out_path: Path) -> None:
    plt.rcParams.update(
        {
            "font.size": 9.5,
            "axes.titlesize": 9.8,
            "axes.labelsize": 9,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "font.family": "DejaVu Sans",
        }
    )

    display_names = (
        table.drop_duplicates(subset=["metric"])
        .set_index("metric")["display_metric"]
        .to_dict()
    )
    x_abs = max(5.0, float(table["display_pct_change"].abs().max()) + 2.5)
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 6.3), constrained_layout=True)
    axes = axes.flatten()

    positions = np.arange(len(COMPONENT_ORDER))
    component_labels = [label for label, _ in COMPONENT_ORDER]
    for idx, metric in enumerate(COMPONENT_METRICS):
        ax = axes[idx]
        subset = table[table["metric"] == metric].copy()
        neg = (
            subset[subset["perturbation"] == "-10%"]
            .set_index("component")
            .reindex(component_labels)
        )
        pos = (
            subset[subset["perturbation"] == "+10%"]
            .set_index("component")
            .reindex(component_labels)
        )
        ax.barh(
            positions - 0.17,
            neg["display_pct_change"].to_numpy(dtype=float),
            height=0.30,
            color=PERTURBATION_COLORS[-0.10],
            edgecolor="black",
            linewidth=0.4,
            zorder=3,
        )
        ax.barh(
            positions + 0.17,
            pos["display_pct_change"].to_numpy(dtype=float),
            height=0.30,
            color=PERTURBATION_COLORS[0.10],
            edgecolor="black",
            linewidth=0.4,
            zorder=3,
        )
        ax.axvline(0, color="black", linewidth=0.7, zorder=2)
        ax.grid(axis="x", color="#d9d9d9", linewidth=0.55, linestyle="-", alpha=0.85, zorder=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title(display_names.get(metric, metric), pad=6)
        local_abs = max(2.5, float(subset["display_pct_change"].abs().max()) + 1.5)
        ax.set_xlim(-local_abs, local_abs)
        ax.set_yticks(positions)
        ax.set_yticklabels(component_labels)
        ax.invert_yaxis()
        if idx % 2 == 1:
            ax.set_yticklabels([])
        if idx >= 2:
            ax.set_xlabel("Change relative to perturbed baseline (%)")

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=PERTURBATION_COLORS[-0.10], edgecolor="black", linewidth=0.4),
        plt.Rectangle((0, 0), 1, 1, facecolor=PERTURBATION_COLORS[0.10], edgecolor="black", linewidth=0.4),
    ]
    fig.legend(
        handles,
        ["-10% perturbation", "+10% perturbation"],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.08),
        ncol=2,
        frameon=False,
        fontsize=8.6,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def _write_audit(
    *,
    scenario_year: str,
    iterations: int,
    seed: int,
    outputs: list[str],
) -> None:
    lines = [
        "# SI primary-revenue uncertainty audit",
        "",
        f"Scenario year: {scenario_year}",
        f"Bootstrap iterations per season: {iterations}",
        f"Bootstrap seed: {seed}",
        "",
        "This workflow regenerates Supplementary Figures S8-S11 from the same official",
        "2017-18 realized-price and state-crop C2 cost benchmark used in the main Figure 2 branch.",
        "The seasonal uncertainty bars (S8-S9) use the nitrogen-focused endpoint only and propagate",
        "district-level coefficient uncertainty through water-demand, net-nitrogen, and net-phosphorus",
        "coefficients. The component-sensitivity panels (S10-S11) apply one-at-a-time +/-10% changes",
        "to the four nitrogen-input components that sum into net nitrogen application.",
        "",
        "Outputs:",
    ]
    lines.extend([f"- {line}" for line in outputs])
    (OUT_DIR / "si_uncertainty_primary_revenue_audit.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-year", default=DEFAULT_SCENARIO_YEAR)
    parser.add_argument("--bootstrap-iterations", type=int, default=500)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    contexts, namespace_frames, layout = _build_official_contexts(args.scenario_year)

    outputs: list[str] = []
    for season in ("kharif", "rabi"):
        iterations_df, summary_df = _run_seasonal_bootstrap(
            season=season,
            context=contexts[season],
            layout=layout,
            iterations=args.bootstrap_iterations,
            seed=args.bootstrap_seed,
        )
        iterations_csv = OUT_DIR / f"{season}_bootstrap_iterations.csv"
        summary_csv = OUT_DIR / f"{season}_bootstrap_summary.csv"
        iterations_df.to_csv(iterations_csv, index=False)
        summary_df.to_csv(summary_csv, index=False)
        _plot_single_strategy_bootstrap(summary_df, SEASON_FIGURES[season]["bootstrap_png"])
        outputs.extend(
            [
                str(iterations_csv),
                str(summary_csv),
                str(SEASON_FIGURES[season]["bootstrap_png"]),
            ]
        )

        component_table = _run_component_sensitivity(
            season=season,
            context=contexts[season],
            frame=namespace_frames[season],
        )
        component_csv = OUT_DIR / f"{season}_component_sensitivity.csv"
        component_table.to_csv(component_csv, index=False)
        _plot_component_sensitivity(component_table, SEASON_FIGURES[season]["component_png"])
        outputs.extend(
            [
                str(component_csv),
                str(SEASON_FIGURES[season]["component_png"]),
            ]
        )

    _write_audit(
        scenario_year=args.scenario_year,
        iterations=args.bootstrap_iterations,
        seed=args.bootstrap_seed,
        outputs=outputs,
    )


if __name__ == "__main__":
    main()
