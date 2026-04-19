#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import math
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures"
DATA_DIR = ROOT / "data" / "generated"
OUT_DIR = DATA_DIR / "figure2b_no_historical_cap_core_expanded_bootstrap"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AUDIT_ROOT))

from generate_figure2b_clean import (  # noqa: E402
    METRICS,
    SEASON_NOTEBOOKS,
    build_context as build_clean_context,
    metric_totals,
    solve_endpoint,
)
from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import _prepare_namespace  # noqa: E402


OUT_ITERATIONS = OUT_DIR / "figure2b_no_historical_cap_core_expanded_bootstrap_iterations.csv"
OUT_SUMMARY = OUT_DIR / "figure2b_no_historical_cap_core_expanded_bootstrap_summary.csv"
OUT_REPRO = OUT_DIR / "figure2b_no_historical_cap_core_expanded_deterministic_reproduction_check.csv"
OUT_AUDIT = OUT_DIR / "figure2b_no_historical_cap_core_expanded_bootstrap_audit.md"
OUT_PNG = FIG_DIR / "figure2b_no_historical_cap_core_expanded_with_whiskers.png"
OUT_PDF = FIG_DIR / "figure2b_no_historical_cap_core_expanded_with_whiskers.pdf"
CENTERS_CSV = DATA_DIR / "figure2b_no_historical_cap_core_values.csv"


PARAM_SPECS = [
    {"raw_col": "CWR m3/ha", "context_key": "water_rate", "mode": "delta"},
    {"raw_col": "net_N_applied(kg/ha)", "context_key": "nitrogen_rate", "mode": "delta"},
    {"raw_col": "net_P_applied(kg/ha)", "context_key": "p_rate", "mode": "delta"},
    {"raw_col": "n_removed_rate", "context_key": "n_removed_rate", "mode": "ratio"},
    {"raw_col": "p_removed_rate", "context_key": "p_removed_rate", "mode": "ratio"},
    {"raw_col": "fn2o", "context_key": "n_emission_rate", "mode": "ratio"},
    {"raw_col": "fno3", "context_key": "n_leach_rate", "mode": "ratio"},
]
POOL_COLS = [spec["raw_col"] for spec in PARAM_SPECS]


def canon(value: object) -> str:
    if pd.isna(value):
        return "__missing__"
    text = str(value).strip().lower()
    return text if text else "__missing__"


def lower_key_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for src, dst in (("State", "state"), ("District", "district"), ("Crop", "crop")):
        if src in frame.columns and dst not in frame.columns:
            rename_map[src] = dst
    out = frame.rename(columns=rename_map).copy()
    for col in ("state", "district", "crop"):
        if col in out.columns:
            out[col] = out[col].map(canon)
    return out


def build_pool(frame: pd.DataFrame, cols: list[str], by: list[str]) -> dict[object, list[tuple[float, ...]]]:
    pool: dict[object, list[tuple[float, ...]]] = {}
    valid = frame.dropna(subset=cols, how="all").copy()
    for key, group in valid.groupby(by, sort=False):
        records = [
            tuple(float(value) for value in row)
            for row in group[cols].itertuples(index=False, name=None)
            if not any(pd.isna(value) or not math.isfinite(float(value)) for value in row)
        ]
        if records:
            pool[key] = records
    return pool


def build_pool_means(pool: dict[object, list[tuple[float, ...]]]) -> dict[object, tuple[float, ...]]:
    means: dict[object, tuple[float, ...]] = {}
    for key, records in pool.items():
        arr = np.asarray(records, dtype=float)
        means[key] = tuple(float(value) for value in arr.mean(axis=0))
    return means


def load_sampling_pools(layout, season: str, notebook_name: str) -> dict[str, object]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        namespace = _prepare_namespace(layout, notebook_name)

    raw_panel = lower_key_columns(namespace[season])
    exact_pool = build_pool(raw_panel, POOL_COLS, ["state", "district", "crop"])
    state_crop_pool = build_pool(raw_panel, POOL_COLS, ["state", "crop"])
    crop_pool = build_pool(raw_panel, POOL_COLS, ["crop"])

    return {
        "exact_pool": exact_pool,
        "state_crop_pool": state_crop_pool,
        "crop_pool": crop_pool,
        "exact_pool_mean": build_pool_means(exact_pool),
        "state_crop_pool_mean": build_pool_means(state_crop_pool),
        "crop_pool_mean": build_pool_means(crop_pool),
    }


def iter_allowed_triples(context: dict[str, object]) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    for state, district in context["pairs_with_area"]:
        for crop in context["crops_by_pair"][(state, district)]:
            triples.append((state, district, crop))
    return triples


def _apply_draw(base: float, draw: float, mean_draw: float, mode: str) -> float:
    if not math.isfinite(base):
        return 0.0
    if not math.isfinite(draw):
        return base
    if mode == "delta":
        return max(0.0, base + (draw - mean_draw))
    if mode == "ratio":
        if not math.isfinite(mean_draw) or mean_draw == 0:
            return base
        return max(0.0, base * (draw / mean_draw))
    raise ValueError(f"Unsupported perturbation mode: {mode}")


def draw_coefficients(
    rng: np.random.Generator,
    context: dict[str, object],
    pools: dict[str, object],
) -> dict[str, dict[tuple[str, str, str], float]]:
    perturbed = {
        "water_rate": dict(context["water_rate"]),
        "nitrogen_rate": dict(context["nitrogen_rate"]),
        "p_rate": dict(context["p_rate"]),
        "yield_data": dict(context["yield_data"]),
        "n_removed_rate": dict(context["n_removed_rate"]),
        "p_removed_rate": dict(context["p_removed_rate"]),
        "n_emission_rate": dict(context["n_emission_rate"]),
        "n_leach_rate": dict(context["n_leach_rate"]),
    }

    for key in iter_allowed_triples(context):
        ckey = (canon(key[0]), canon(key[1]), canon(key[2]))
        sample = None
        sample_mean = None
        for candidate, candidate_mean in (
            (pools["exact_pool"].get(ckey), pools["exact_pool_mean"].get(ckey)),
            (
                pools["state_crop_pool"].get((canon(key[0]), canon(key[2]))),
                pools["state_crop_pool_mean"].get((canon(key[0]), canon(key[2]))),
            ),
            (pools["crop_pool"].get(canon(key[2])), pools["crop_pool_mean"].get(canon(key[2]))),
        ):
            if candidate:
                sample = candidate[int(rng.integers(len(candidate)))]
                sample_mean = candidate_mean
                break

        if sample is None or sample_mean is None:
            continue

        for idx, spec in enumerate(PARAM_SPECS):
            context_key = spec["context_key"]
            base = float(perturbed[context_key].get(key, sample_mean[idx]))
            perturbed[context_key][key] = _apply_draw(base, float(sample[idx]), float(sample_mean[idx]), spec["mode"])

    return perturbed


def load_centers() -> pd.DataFrame:
    centers = pd.read_csv(CENTERS_CSV)
    centers["metric"] = pd.Categorical(
        centers["metric"],
        categories=[metric for metric, _ in METRICS],
        ordered=True,
    )
    return centers.sort_values(["metric", "scenario"]).reset_index(drop=True)


def deterministic_reproduction(contexts: dict[str, dict[str, object]], centers: pd.DataFrame) -> pd.DataFrame:
    center_map = {
        (row.scenario, row.metric): float(row.pct_reduction)
        for row in centers.itertuples(index=False)
    }
    baseline_totals = {
        season: metric_totals(context["current_cereal_area"], context)
        for season, context in contexts.items()
    }
    rows: list[dict[str, object]] = []

    for scenario in ["Water based", "Nitrogen based"]:
        objective = "water" if scenario == "Water based" else "nitrogen"
        optimized = {metric_key: 0.0 for _, metric_key in METRICS}
        baseline = {metric_key: 0.0 for _, metric_key in METRICS}
        statuses = []

        for season, context in contexts.items():
            status, area_map = solve_endpoint(context, objective, use_historical_caps=False)
            statuses.append(f"{season}:{status}")
            if status != "Optimal":
                continue
            season_totals = metric_totals(area_map, context)
            for metric_key in baseline:
                baseline[metric_key] += baseline_totals[season][metric_key]
                optimized[metric_key] += season_totals[metric_key]

        for metric_label, metric_key in METRICS:
            baseline_total = baseline[metric_key]
            reproduced = 100.0 * (baseline_total - optimized[metric_key]) / baseline_total
            center = center_map[(scenario, metric_label)]
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric_label,
                    "baseline_total": baseline_total,
                    "reproduced_pct_reduction": reproduced,
                    "center_pct_reduction": center,
                    "delta_pct_points": reproduced - center,
                    "solver_status": ";".join(statuses),
                }
            )

    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["metric", "scenario"]).reset_index(drop=True)


def run_bootstrap(
    contexts: dict[str, dict[str, object]],
    pools: dict[str, dict[str, object]],
    iterations: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    baseline_totals = {
        season: metric_totals(context["current_cereal_area"], context)
        for season, context in contexts.items()
    }
    annual_baseline = {metric_key: 0.0 for _, metric_key in METRICS}
    for season in contexts:
        for metric_key in annual_baseline:
            annual_baseline[metric_key] += baseline_totals[season][metric_key]

    rows: list[dict[str, object]] = []
    for iteration in range(iterations):
        drawn_by_season = {}
        for season, context in contexts.items():
            drawn_by_season[season] = draw_coefficients(rng, context, pools[season])

        for scenario in ["Water based", "Nitrogen based"]:
            objective = "water" if scenario == "Water based" else "nitrogen"
            combined = {metric_key: 0.0 for _, metric_key in METRICS}
            statuses: dict[str, str] = {}

            for season, context in contexts.items():
                iter_context = dict(context)
                iter_context.update(drawn_by_season[season])

                status, area_map = solve_endpoint(iter_context, objective, use_historical_caps=False)
                statuses[season] = status
                if status != "Optimal":
                    continue

                totals = metric_totals(area_map, iter_context)
                for metric_key, value in totals.items():
                    combined[metric_key] += value

            scenario_status = "Optimal" if all(status == "Optimal" for status in statuses.values()) else "Infeasible"
            for metric_label, metric_key in METRICS:
                pct_reduction = np.nan
                if scenario_status == "Optimal":
                    baseline = annual_baseline[metric_key]
                    pct_reduction = 100.0 * (baseline - combined[metric_key]) / baseline

                rows.append(
                    {
                        "iteration": iteration,
                        "scenario": scenario,
                        "metric": metric_label,
                        "metric_key": metric_key,
                        "status": scenario_status,
                        "kharif_status": statuses.get("kharif", "NA"),
                        "rabi_status": statuses.get("rabi", "NA"),
                        "pct_reduction": pct_reduction,
                        "display_pct_change": -pct_reduction if pd.notna(pct_reduction) else np.nan,
                    }
                )

    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["iteration", "metric", "scenario"]).reset_index(drop=True)


def build_summary(iterations: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
    center_map = {
        (row.scenario, row.metric): (float(row.pct_reduction), float(row.display_pct_change))
        for row in centers.itertuples(index=False)
    }
    rows = []
    for (scenario, metric), group in iterations.groupby(["scenario", "metric"], sort=False):
        valid = group[group["status"] == "Optimal"]["pct_reduction"].astype(float)
        center_pct, center_display = center_map[(scenario, metric)]

        if valid.empty:
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "center_pct_reduction": center_pct,
                    "center_display_pct": center_display,
                    "bootstrap_mean_pct_reduction": np.nan,
                    "bootstrap_p2_5_pct_reduction": np.nan,
                    "bootstrap_p97_5_pct_reduction": np.nan,
                    "bootstrap_mean_display_pct": np.nan,
                    "display_interval_low": np.nan,
                    "display_interval_high": np.nan,
                    "lower_err_display": np.nan,
                    "upper_err_display": np.nan,
                    "n_optimal": int(valid.size),
                    "n_total": int(group.shape[0]),
                }
            )
            continue

        p2_5 = float(valid.quantile(0.025))
        p97_5 = float(valid.quantile(0.975))
        display_low = min(-p2_5, -p97_5)
        display_high = max(-p2_5, -p97_5)

        rows.append(
            {
                "scenario": scenario,
                "metric": metric,
                "center_pct_reduction": center_pct,
                "center_display_pct": center_display,
                "bootstrap_mean_pct_reduction": float(valid.mean()),
                "bootstrap_p2_5_pct_reduction": p2_5,
                "bootstrap_p97_5_pct_reduction": p97_5,
                "bootstrap_mean_display_pct": float((-valid).mean()),
                "display_interval_low": display_low,
                "display_interval_high": display_high,
                "lower_err_display": max(center_display - display_low, 0.0),
                "upper_err_display": max(display_high - center_display, 0.0),
                "n_optimal": int(valid.size),
                "n_total": int(group.shape[0]),
            }
        )

    out = pd.DataFrame(rows)
    out["metric"] = pd.Categorical(out["metric"], [label for label, _ in METRICS], ordered=True)
    return out.sort_values(["metric", "scenario"]).reset_index(drop=True)


def build_figure(summary: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
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
        label="Water-based",
        zorder=3,
    )
    ax.barh(
        positions + offset,
        nitrogen["center_display_pct"].to_numpy(),
        height=bar_height,
        color="#d18f00",
        edgecolor="black",
        linewidth=0.5,
        label="Nitrogen-based",
        zorder=3,
    )

    ax.errorbar(
        water["center_display_pct"].to_numpy(),
        positions - offset,
        xerr=np.vstack([water["lower_err_display"].to_numpy(dtype=float), water["upper_err_display"].to_numpy(dtype=float)]),
        fmt="none",
        ecolor="#303030",
        elinewidth=1.0,
        capsize=2.6,
        zorder=4,
    )
    ax.errorbar(
        nitrogen["center_display_pct"].to_numpy(),
        positions + offset,
        xerr=np.vstack(
            [nitrogen["lower_err_display"].to_numpy(dtype=float), nitrogen["upper_err_display"].to_numpy(dtype=float)]
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
    ax.legend(loc="lower center", bbox_to_anchor=(0.53, 1.015), ncol=3, frameon=False, fontsize=7.2, handlelength=1.8, borderaxespad=0.0, columnspacing=1.0)

    x_min = min(
        float((water["center_display_pct"] - water["lower_err_display"]).min()),
        float((nitrogen["center_display_pct"] - nitrogen["lower_err_display"]).min()),
    )
    x_max = max(
        float((water["center_display_pct"] + water["upper_err_display"]).max()),
        float((nitrogen["center_display_pct"] + nitrogen["upper_err_display"]).max()),
    )
    ax.set_xlim(min(-52.0, x_min - 4.0), max(30.0, x_max + 4.0))

    fig.savefig(OUT_PNG, dpi=500, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white", pad_inches=0.02)
    plt.close(fig)


def write_audit(
    summary: pd.DataFrame,
    reproduction: pd.DataFrame,
    iterations: pd.DataFrame,
    n_iterations: int,
    elapsed_seconds: float,
) -> None:
    lines = [
        "# Figure 2(b) approved expanded bootstrap audit",
        "",
        "This rebuild extends the district-input bootstrap on the approved",
        "Figure 2(b) branch by perturbing both the optimization",
        "coefficients and the downstream environmental translation coefficients",
        "available in the prepared seasonal panels.",
        "",
        "Perturbed raw-panel coefficients and mapped model fields:",
    ]
    for spec in PARAM_SPECS:
        lines.append(f"- `{spec['raw_col']}` -> `{spec['context_key']}` ({spec['mode']})")
    lines.extend(
        [
            "",
            "All perturbations are centered on the prepared 2017 coefficient fields.",
            "For `delta` specifications, the sampled deviation from the empirical pool mean is added to the",
            "prepared 2017 value. For `ratio` specifications, the prepared 2017 value is multiplied by the",
            "sample-to-mean ratio from the empirical pool.",
            "",
            f"Bootstrap iterations requested: {n_iterations}",
            f"Elapsed time (s): {elapsed_seconds:.2f}",
            "",
            "## Deterministic reproduction check",
            "",
        ]
    )
    for row in reproduction.itertuples(index=False):
        lines.append(
            f"- {row.scenario} | {row.metric}: reproduced {row.reproduced_pct_reduction:.3f}%, "
            f"center {row.center_pct_reduction:.3f}%, delta {row.delta_pct_points:.3f} pp "
            f"({row.solver_status})"
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
            f"- {row.scenario} | {row.metric}: center {row.center_pct_reduction:.3f}%, "
            f"mean {row.bootstrap_mean_pct_reduction:.3f}%, "
            f"95% CI [{row.bootstrap_p2_5_pct_reduction:.3f}, {row.bootstrap_p97_5_pct_reduction:.3f}]%, "
            f"optimal {row.n_optimal}/{row.n_total}"
        )

    OUT_AUDIT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add expanded traceable whiskers to the approved Figure 2(b) panel."
    )
    parser.add_argument("--iterations", type=int, default=200, help="Number of bootstrap iterations.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap draws.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout = default_layout(AUDIT_ROOT)
    contexts = {
        season: build_clean_context(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    pools = {
        season: load_sampling_pools(layout, season, notebook_name)
        for season, notebook_name in SEASON_NOTEBOOKS.items()
    }
    centers = load_centers()

    start = time.time()
    reproduction = deterministic_reproduction(contexts, centers)
    iterations = run_bootstrap(contexts, pools, args.iterations, args.seed)
    summary = build_summary(iterations, centers)
    elapsed = time.time() - start

    reproduction.to_csv(OUT_REPRO, index=False)
    iterations.to_csv(OUT_ITERATIONS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    build_figure(summary)
    write_audit(summary, reproduction, iterations, args.iterations, elapsed)


if __name__ == "__main__":
    main()
