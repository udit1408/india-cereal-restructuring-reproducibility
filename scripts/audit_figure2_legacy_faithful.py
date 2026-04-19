#!/usr/bin/env python3
from __future__ import annotations

import ast
import contextlib
import io
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
DATA_DIR = ROOT / "data" / "generated"

sys.path.insert(0, str(AUDIT_ROOT))

from repro.config import default_layout  # noqa: E402
from repro.legacy_notebook_runner import (  # noqa: E402
    NotebookRunConfig,
    _rewrite_source,
    extract_archive_if_needed,
)


PERITO_NOTEBOOKS = {
    "kharif": {
        "notebook": "kharif_perito_cop.ipynb",
        "income_mode": "profit",
    },
    "rabi": {
        "notebook": "rabi_perito_cop.ipynb",
        "income_mode": "msp",
    },
}

SAMPLE_ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
OUT_MD = DATA_DIR / "figure2_legacy_faithful_audit.md"
OUT_SUMMARY = DATA_DIR / "figure2_legacy_faithful_summary.csv"
OUT_2A_SAMPLE = DATA_DIR / "figure2a_legacy_faithful_sample_rebuild.csv"
CAP_VARIANT_SUMMARY = DATA_DIR / "figure2_cap_variant_summary.csv"
FIGURE2C_DIR = DATA_DIR / "figure2c"

SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]+")


def sanitize(text: str) -> str:
    return SANITIZE_RE.sub("_", str(text)).strip("_") or "x"


def float_triplet_map(mapping: object) -> dict[tuple[str, str, str], float]:
    if isinstance(mapping, pd.Series):
        mapping = mapping.to_dict()
    if not isinstance(mapping, dict):
        raise TypeError(f"Expected dict-like mapping, found {type(mapping)!r}")
    out: dict[tuple[str, str, str], float] = {}
    for key, value in mapping.items():
        if not isinstance(key, tuple) or len(key) != 3:
            continue
        try:
            out[(str(key[0]), str(key[1]), str(key[2]))] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def execute_notebook_until_marker(notebook_name: str, stop_marker: str) -> dict[str, object]:
    layout = default_layout(AUDIT_ROOT)
    data_dir = extract_archive_if_needed(layout.root)
    notebook = (AUDIT_ROOT / notebook_name).resolve()
    config = NotebookRunConfig(
        notebook=notebook,
        data_dir=data_dir.resolve(),
        generated_dir=layout.generated_dir.resolve(),
        use_cbc=False,
    )
    raw = json.loads(notebook.read_text())
    namespace: dict[str, object] = {"__name__": "__main__", "pd": pd}

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for idx, cell in enumerate(raw.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue
            rewritten = _rewrite_source(source, config).replace("import geopandas as gpd\n", "")
            try:
                parsed = ast.parse(rewritten, mode="exec")
            except SyntaxError:
                parsed = None

            if (
                parsed is not None
                and len(parsed.body) == 1
                and isinstance(parsed.body[0], ast.Expr)
                and isinstance(parsed.body[0].value, ast.Name)
                and parsed.body[0].value.id not in namespace
            ):
                continue

            if stop_marker in rewritten:
                rewritten = rewritten.split(stop_marker, 1)[0]
                if rewritten.strip():
                    exec(compile(rewritten, f"{notebook.name}:cell_{idx}", "exec"), namespace, namespace)
                break
            exec(compile(rewritten, f"{notebook.name}:cell_{idx}", "exec"), namespace, namespace)
    return namespace


def build_perito_context(season: str) -> dict[str, object]:
    spec = PERITO_NOTEBOOKS[season]
    namespace = execute_notebook_until_marker(
        spec["notebook"],
        "# Results dictionary to store optimized nitrogen for each coefficient",
    )
    frame = namespace["df"].copy()
    frame["State"] = frame["State"].astype(str)
    frame["District"] = frame["District"].astype(str)
    frame["Crop"] = frame["Crop"].astype(str)

    history_raw = namespace["historical_cereal_area"]
    historical_cereal_area = float_triplet_map(history_raw)

    states = frame["State"].dropna().astype(str).unique().tolist()
    districts = frame["District"].dropna().astype(str).unique().tolist()
    cereals = frame["Crop"].dropna().astype(str).unique().tolist()

    return {
        "season": season,
        "income_mode": spec["income_mode"],
        "frame": frame,
        "states": states,
        "districts": districts,
        "cereals": cereals,
        "district_to_state": frame.set_index("District")["State"].to_dict(),
        "current_area": frame.groupby(["State", "District"])["Area (Hectare)"].sum().astype(float).to_dict(),
        "current_cereal_area": frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict(),
        "historical_cereal_area": historical_cereal_area,
        "nitrogen_rate": float_triplet_map(namespace["nitrogen_rate"]),
        "nitrogen_removal_rate": float_triplet_map(namespace["nitrogen_removal_rate_perkg"]),
        "water_rate": float_triplet_map(namespace["water_rate"]),
        "yield_data": float_triplet_map(namespace["yield_data"]),
        "calories_per_prod": float_triplet_map(namespace["calories_per_prod"]),
        "msp_per_prod": float_triplet_map(namespace["MSP_per_prod"]),
        "cost_per_area": float_triplet_map(namespace["cost_per_area"]),
        "initial_state_calories": frame.groupby("State")["Total Calorie Supply"].sum().astype(float).to_dict(),
        "initial_state_profit": frame.groupby("State")["Total initial profit"].sum().astype(float).to_dict(),
        "initial_state_msp": frame.groupby("State")["Total MSP Supply"].sum().astype(float).to_dict(),
        "row_count": len(districts) * len(cereals),
    }


def solve_legacy_perito_sample(context: dict[str, object], alpha: float) -> dict[str, object]:
    states = context["states"]
    districts = context["districts"]
    cereals = context["cereals"]
    district_to_state = context["district_to_state"]
    current_area = context["current_area"]
    historical_cereal_area = context["historical_cereal_area"]
    nitrogen_rate = context["nitrogen_rate"]
    nitrogen_removal_rate = context["nitrogen_removal_rate"]
    water_rate = context["water_rate"]
    yield_data = context["yield_data"]
    calories_per_prod = context["calories_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    cost_per_area = context["cost_per_area"]

    prob = pulp.LpProblem(
        f"LegacyPerito_{context['season']}_{alpha:.2f}",
        pulp.LpMinimize,
    )
    x = pulp.LpVariable.dicts("Area_Hectare", (states, districts, cereals), 0, None, pulp.LpContinuous)

    objective_n = pulp.lpSum(
        x[s][d][c]
        * (
            nitrogen_rate.get((s, d, c), 0.0)
            - yield_data.get((s, d, c), 0.0) * nitrogen_removal_rate.get((s, d, c), 0.0)
        )
        for s in states
        for d in districts
        for c in cereals
    )
    objective_w = pulp.lpSum(
        x[s][d][c] * water_rate.get((s, d, c), 0.0)
        for s in states
        for d in districts
        for c in cereals
    )
    prob += alpha * objective_n + (1.0 - alpha) * objective_w

    for s in states:
        for d in districts:
            for c in cereals:
                if historical_cereal_area.get((s, d, c), 0.0) == 0:
                    prob += x[s][d][c] == 0
            prob += pulp.lpSum(x[s][d][c] for c in cereals) == current_area.get((s, d), 0.0)

    for s in states:
        prob += (
            pulp.lpSum(
                x[s][d][c]
                * yield_data.get((s, d, c), 0.0)
                * calories_per_prod.get((s, d, c), 0.0)
                for d in districts
                for c in cereals
            )
            >= context["initial_state_calories"].get(s, 0.0)
        )
        if context["income_mode"] == "profit":
            prob += (
                pulp.lpSum(
                    (
                        x[s][d][c]
                        * yield_data.get((s, d, c), 0.0)
                        * 0.01
                        * msp_per_prod.get((s, d, c), 0.0)
                    )
                    - (
                        x[s][d][c]
                        * yield_data.get((s, d, c), 0.0)
                        * 0.01
                        * cost_per_area.get((s, d, c), 0.0)
                    )
                    for d in districts
                    if district_to_state.get(d) == s
                    for c in cereals
                )
                >= context["initial_state_profit"].get(s, 0.0)
            )
        elif context["income_mode"] == "msp":
            prob += (
                pulp.lpSum(
                    x[s][d][c]
                    * yield_data.get((s, d, c), 0.0)
                    * 0.01
                    * msp_per_prod.get((s, d, c), 0.0)
                    for d in districts
                    if district_to_state.get(d) == s
                    for c in cereals
                )
                >= context["initial_state_msp"].get(s, 0.0)
            )
        else:
            raise ValueError(f"Unsupported income mode: {context['income_mode']}")

    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    return {
        "season": context["season"],
        "alpha": alpha,
        "status": pulp.LpStatus.get(prob.status, str(prob.status)),
        "objective_n": float(pulp.value(objective_n) or math.nan),
        "objective_w": float(pulp.value(objective_w) or math.nan),
        "row_count": int(context["row_count"]),
    }


def load_generated_frontier() -> tuple[pd.DataFrame, dict[str, int]]:
    generated_root = AUDIT_ROOT / "generated"
    kharif = pd.read_csv(generated_root / "kharif_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv")
    rabi = pd.read_csv(generated_root / "rabi_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv")
    for frame in (kharif, rabi):
        frame["Alpha"] = frame["Alpha"].astype(float)
    combined = (
        pd.concat([kharif, rabi], ignore_index=True)
        .groupby("Alpha", as_index=False)[["Objective Nitrogen", "Objective Water"]]
        .mean()
        .rename(columns={"Alpha": "alpha"})
    )
    row_counts = {
        "kharif": int(kharif.groupby("Alpha").size().iloc[0]),
        "rabi": int(rabi.groupby("Alpha").size().iloc[0]),
    }
    return combined, row_counts


def build_2a_sample_table() -> pd.DataFrame:
    contexts = {season: build_perito_context(season) for season in PERITO_NOTEBOOKS}
    frontier, archived_counts = load_generated_frontier()
    rows: list[dict[str, object]] = []
    for alpha in SAMPLE_ALPHAS:
        sample = {season: solve_legacy_perito_sample(contexts[season], alpha) for season in contexts}
        weighted_n = (
            sample["kharif"]["objective_n"] * sample["kharif"]["row_count"]
            + sample["rabi"]["objective_n"] * sample["rabi"]["row_count"]
        ) / (sample["kharif"]["row_count"] + sample["rabi"]["row_count"])
        weighted_w = (
            sample["kharif"]["objective_w"] * sample["kharif"]["row_count"]
            + sample["rabi"]["objective_w"] * sample["rabi"]["row_count"]
        ) / (sample["kharif"]["row_count"] + sample["rabi"]["row_count"])
        archived = frontier.loc[(frontier["alpha"] - alpha).abs() < 1e-9].iloc[0]
        rows.append(
            {
                "panel": "2a",
                "alpha": alpha,
                "kharif_status": sample["kharif"]["status"],
                "rabi_status": sample["rabi"]["status"],
                "kharif_rows": sample["kharif"]["row_count"],
                "rabi_rows": sample["rabi"]["row_count"],
                "archived_kharif_rows": archived_counts["kharif"],
                "archived_rabi_rows": archived_counts["rabi"],
                "rebuilt_nitrogen_tg": weighted_n / 1e9,
                "archived_nitrogen_tg": float(archived["Objective Nitrogen"]) / 1e9,
                "rebuilt_water_bcm": weighted_w / 1e9,
                "archived_water_bcm": float(archived["Objective Water"]) / 1e9,
                "delta_nitrogen_tg": (weighted_n - float(archived["Objective Nitrogen"])) / 1e9,
                "delta_water_bcm": (weighted_w - float(archived["Objective Water"])) / 1e9,
            }
        )
    return pd.DataFrame(rows)


def summarize_endpoint_export(path: Path) -> dict[str, float]:
    frame = pd.read_csv(path)
    return {
        "water_original": float(frame["Original water"].sum()),
        "water_optimized": float(frame["Optimized water"].sum()),
        "n_original": float(frame["Original Total N surplus"].sum()),
        "n_optimized": float(frame["Optimized Total N surplus"].sum()),
        "calorie_original": float(frame["Original Calorie"].sum()),
        "calorie_optimized": float(frame["Optimized Calorie"].sum()),
        "profit_original": float(frame["Original profit"].sum()),
        "profit_optimized": float(frame["Optimized profit"].sum()),
    }


def pct_reduction(original: float, optimized: float) -> float:
    return 100.0 * (original - optimized) / original


def build_2b_table() -> pd.DataFrame:
    generated_root = AUDIT_ROOT / "generated"
    legacy_water = summarize_endpoint_export(generated_root / "water_based_opt_cop_kharif.csv")
    legacy_water_rabi = summarize_endpoint_export(generated_root / "water_based_opt_cop_rabi.csv")
    legacy_n = summarize_endpoint_export(generated_root / "state_kharif_nitrogen.csv")
    legacy_n_rabi = summarize_endpoint_export(generated_root / "state_rabi_nitrogen.csv")

    rows = []
    for scenario, pair in {
        "Water based": (legacy_water, legacy_water_rabi),
        "Nitrogen based": (legacy_n, legacy_n_rabi),
    }.items():
        combined = {
            key: pair[0][key] + pair[1][key]
            for key in pair[0]
        }
        rows.extend(
            [
                {
                    "panel": "2b",
                    "variant": "legacy_endpoint_exports",
                    "scenario": scenario,
                    "metric": "Nitrogen Surplus",
                    "pct_reduction": pct_reduction(combined["n_original"], combined["n_optimized"]),
                },
                {
                    "panel": "2b",
                    "variant": "legacy_endpoint_exports",
                    "scenario": scenario,
                    "metric": "Water Demand",
                    "pct_reduction": pct_reduction(combined["water_original"], combined["water_optimized"]),
                },
                {
                    "panel": "2b",
                    "variant": "legacy_endpoint_exports",
                    "scenario": scenario,
                    "metric": "Calorie",
                    "pct_reduction": pct_reduction(combined["calorie_original"], combined["calorie_optimized"]),
                },
                {
                    "panel": "2b",
                    "variant": "legacy_endpoint_exports",
                    "scenario": scenario,
                    "metric": "Profit",
                    "pct_reduction": pct_reduction(combined["profit_original"], combined["profit_optimized"]),
                },
            ]
        )
    strict = pd.read_csv(DATA_DIR / "figure2b_clean_method_consistent_values.csv")
    for row in strict.itertuples(index=False):
        if row.metric not in {"Nitrogen Surplus", "Water Demand", "Calorie", "Profit"}:
            continue
        rows.append(
            {
                "panel": "2b",
                "variant": "clean_capped",
                "scenario": row.scenario,
                "metric": row.metric,
                "pct_reduction": float(row.pct_reduction),
            }
        )

    cap_variant = pd.read_csv(CAP_VARIANT_SUMMARY)
    no_cap = cap_variant[
        (cap_variant["panel"] == "2b")
        & (cap_variant["variant"] == "no_historical_caps")
        & (cap_variant["metric"].isin(["Nitrogen Surplus", "Water Demand", "Calorie", "Profit"]))
    ]
    for row in no_cap.itertuples(index=False):
        rows.append(
            {
                "panel": "2b",
                "variant": "no_historical_caps",
                "scenario": row.scenario_or_crop,
                "metric": row.metric,
                "pct_reduction": float(row.value),
            }
        )
    return pd.DataFrame(rows)


def build_2c_table() -> pd.DataFrame:
    combined_caps = pd.read_csv(FIGURE2C_DIR / "combined_method_consistent.csv")
    combined_no_caps = pd.read_csv(FIGURE2C_DIR / "combined_no_historical_caps.csv")
    combined_equation = pd.read_csv(FIGURE2C_DIR / "combined_equation_aligned_district_no_caps.csv")
    checkpoints = [0.0, 50.0, 100.0]
    rows: list[dict[str, object]] = []
    for variant, frame in {
        "method_consistent": combined_caps,
        "no_historical_caps": combined_no_caps,
        "district_no_caps": combined_equation,
    }.items():
        for checkpoint in checkpoints:
            hit = frame.loc[(frame["nominal_substitution_pct"] - checkpoint).abs() < 1e-9].iloc[0]
            rows.append(
                {
                    "panel": "2c",
                    "variant": variant,
                    "scenario": "combined",
                    "metric": f"n_surplus_reduction_at_{int(checkpoint)}pct_nominal_substitution",
                    "value": float(hit["pct_reduction_n_surplus"]),
                }
            )
            rows.append(
                {
                    "panel": "2c",
                    "variant": variant,
                    "scenario": "combined",
                    "metric": f"realized_staple_replacement_at_{int(checkpoint)}pct_nominal_substitution",
                    "value": float(hit["realized_staple_replacement_pct"]),
                }
            )
        rows.append(
            {
                "panel": "2c",
                "variant": variant,
                "scenario": "combined",
                "metric": "n_surplus_reduction_range_min",
                "value": float(frame["pct_reduction_n_surplus"].min()),
            }
        )
        rows.append(
            {
                "panel": "2c",
                "variant": variant,
                "scenario": "combined",
                "metric": "n_surplus_reduction_range_max",
                "value": float(frame["pct_reduction_n_surplus"].max()),
            }
        )
    return pd.DataFrame(rows)


def build_2d_table() -> pd.DataFrame:
    cap_variant = pd.read_csv(CAP_VARIANT_SUMMARY)
    frame = cap_variant[
        (cap_variant["panel"] == "2d")
        & (cap_variant["metric"] == "pct_change")
    ].copy()
    return frame.rename(
        columns={
            "variant": "variant",
            "scenario_or_crop": "scenario",
            "value": "value",
        }
    )[
        ["panel", "variant", "scenario", "metric", "value"]
    ]


def markdown_table(frame: pd.DataFrame, columns: list[str], float_cols: set[str] | None = None) -> str:
    float_cols = float_cols or set()
    widths: dict[str, int] = {}
    rendered_rows: list[list[str]] = []
    for _, row in frame.iterrows():
        rendered = []
        for col in columns:
            value = row[col]
            if col in float_cols and pd.notna(value):
                rendered.append(f"{float(value):.3f}")
            else:
                rendered.append(str(value))
        rendered_rows.append(rendered)
    for idx, col in enumerate(columns):
        widths[col] = max(len(col), *(len(row[idx]) for row in rendered_rows))
    header = "| " + " | ".join(col.ljust(widths[col]) for col in columns) + " |"
    divider = "| " + " | ".join("-" * widths[col] for col in columns) + " |"
    body = [
        "| " + " | ".join(row[idx].ljust(widths[col]) for idx, col in enumerate(columns)) + " |"
        for row in rendered_rows
    ]
    return "\n".join([header, divider, *body])


def write_audit(
    sample_2a: pd.DataFrame,
    table_2b: pd.DataFrame,
    table_2c: pd.DataFrame,
    table_2d: pd.DataFrame,
) -> None:
    water_based = table_2b[
        (table_2b["scenario"] == "Water based")
        & (table_2b["metric"].isin(["Nitrogen Surplus", "Water Demand"]))
    ].pivot(index="variant", columns="metric", values="pct_reduction")
    nitrogen_based = table_2b[
        (table_2b["scenario"] == "Nitrogen based")
        & (table_2b["metric"].isin(["Nitrogen Surplus", "Water Demand"]))
    ].pivot(index="variant", columns="metric", values="pct_reduction")

    c2_method = table_2c[(table_2c["variant"] == "method_consistent") & (table_2c["metric"] == "n_surplus_reduction_range_max")]["value"].iloc[0]
    c2_nocap = table_2c[(table_2c["variant"] == "no_historical_caps") & (table_2c["metric"] == "n_surplus_reduction_range_max")]["value"].iloc[0]
    c2_nocap_realized = table_2c[
        (table_2c["variant"] == "no_historical_caps")
        & (table_2c["metric"] == "realized_staple_replacement_at_100pct_nominal_substitution")
    ]["value"].iloc[0]

    rice_rows = table_2d[table_2d["scenario"] == "rice"].set_index("variant")["value"]
    wheat_rows = table_2d[table_2d["scenario"] == "wheat"].set_index("variant")["value"]

    lines = [
        "# Figure 2 Legacy-Faithful Audit",
        "",
        "The earlier strict rebuild drifted away from the manuscript because it made the district-crop historical maximum area cap genuinely binding. In the legacy notebooks, that cap is assembled with `(State, District, Crop)` tuple keys but tested inside the model as `if c in max_area_constraints`, so it is effectively inactive. Once that notebook behavior is preserved, the manuscript-scale magnitudes are much closer to the original outputs.",
        "",
        "For panel 2(a), I rebuilt sample alpha points directly from `kharif_perito_cop.ipynb` and `rabi_perito_cop.ipynb` using the raw weighted objective, the same row-weighted seasonal aggregation used in `rabi_kharif_plot_perito_combined.ipynb`, fixed district cropped area, and the same locally grown crop restriction. The kharif Pareto notebook enforces a state profit floor, whereas the rabi Pareto notebook enforces a state MSP floor. Under that legacy-faithful setup, the rebuilt combined frontier matches the archived plotted frontier exactly at sampled alpha values. The remaining concern is status handling: CBC still returns `Infeasible` for the kharif and rabi endpoint solves even though the reported objective values match the archived CSVs.",
        "",
        markdown_table(
            sample_2a[
                [
                    "alpha",
                    "kharif_status",
                    "rabi_status",
                    "rebuilt_nitrogen_tg",
                    "archived_nitrogen_tg",
                    "rebuilt_water_bcm",
                    "archived_water_bcm",
                    "delta_nitrogen_tg",
                    "delta_water_bcm",
                ]
            ],
            [
                "alpha",
                "kharif_status",
                "rabi_status",
                "rebuilt_nitrogen_tg",
                "archived_nitrogen_tg",
                "rebuilt_water_bcm",
                "archived_water_bcm",
                "delta_nitrogen_tg",
                "delta_water_bcm",
            ],
            {
                "alpha",
                "rebuilt_nitrogen_tg",
                "archived_nitrogen_tg",
                "rebuilt_water_bcm",
                "archived_water_bcm",
                "delta_nitrogen_tg",
                "delta_water_bcm",
            },
        ),
        "",
        "Panel 2(b) is internally consistent on the legacy branch. The generated endpoint exports in `generated/` recover the published combined bar heights exactly when their seasonal totals are summed. Those published values sit very close to the no-historical-cap branch and far from the strict capped rebuild, which is consistent with the ineffective crop-specific cap in the original endpoint notebooks as well.",
        "",
        "Water-based and nitrogen-based combined reductions for the two headline metrics are summarized below.",
        "",
        "Water-based endpoint:",
        "",
        markdown_table(
            water_based.reset_index()[["variant", "Nitrogen Surplus", "Water Demand"]],
            ["variant", "Nitrogen Surplus", "Water Demand"],
            {"Nitrogen Surplus", "Water Demand"},
        ),
        "",
        "Nitrogen-based endpoint:",
        "",
        markdown_table(
            nitrogen_based.reset_index()[["variant", "Nitrogen Surplus", "Water Demand"]],
            ["variant", "Nitrogen Surplus", "Water Demand"],
            {"Nitrogen Surplus", "Water Demand"},
        ),
        "",
        "Panel 2(c) shows the same structural split. With historical crop-area caps enforced, the combined nitrogen-surplus reduction only spans about "
        f"{table_2c[(table_2c['variant'] == 'method_consistent') & (table_2c['metric'] == 'n_surplus_reduction_range_min')]['value'].iloc[0]:.3f}% to {c2_method:.3f}%. "
        f"Without those caps, the combined curve spans about {table_2c[(table_2c['variant'] == 'no_historical_caps') & (table_2c['metric'] == 'n_surplus_reduction_range_min')]['value'].iloc[0]:.3f}% to {c2_nocap:.3f}%, which is much closer to the manuscript text describing roughly 12% to 22% reductions. The x-axis also needs care: the notebook grid is in 10% steps of the nominal retention parameter, not the 25/50/75 checkpoints described in the current prose, and even the most relaxed no-cap case only realizes about {c2_nocap_realized:.3f}% actual rice+wheat replacement.",
        "",
        markdown_table(
            table_2c[
                table_2c["metric"].isin(
                    [
                        "n_surplus_reduction_at_0pct_nominal_substitution",
                        "n_surplus_reduction_at_50pct_nominal_substitution",
                        "n_surplus_reduction_at_100pct_nominal_substitution",
                        "realized_staple_replacement_at_100pct_nominal_substitution",
                    ]
                )
            ],
            ["variant", "metric", "value"],
            {"value"},
        ),
        "",
        "Panel 2(d) remains the one place where the legacy-like no-cap branch gets much closer but does not fully recover the manuscript text. The no-cap rebuild moves rice area by about "
        f"{rice_rows['clean_no_caps']:.3f}% and wheat area by about {wheat_rows['clean_no_caps']:.3f}%, compared with manuscript text of {rice_rows['legacy_reported_text']:.3f}% and {wheat_rows['legacy_reported_text']:.3f}%. That makes the rice change broadly compatible with the legacy branch, but the wheat change still needs targeted checking before it is treated as fully recovered.",
        "",
        markdown_table(
            table_2d[["variant", "scenario", "value"]],
            ["variant", "scenario", "value"],
            {"value"},
        ),
        "",
        "Working conclusion: the repository and manuscript are not randomly wrong. Their central message and most of the published Figure 2 magnitudes sit on a legacy-faithful effective model defined by fixed district cropped area, locally grown crop substitution, panel-specific state income constraints, and an in-practice inactive crop-specific historical maximum cap. The main unresolved technical issue is not the direction of the science but whether the revision should stay on that legacy-effective branch or move to the stricter capped branch, and how to handle the Figure 2(a) solver-status problem if we stay close to the published outputs.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sample_2a = build_2a_sample_table()
    sample_2a.to_csv(OUT_2A_SAMPLE, index=False)
    table_2b = build_2b_table()
    table_2c = build_2c_table()
    table_2d = build_2d_table()
    summary = pd.concat(
        [
            sample_2a.assign(kind="2a_sample"),
            table_2b.assign(kind="2b_compare"),
            table_2c.assign(kind="2c_compare"),
            table_2d.assign(kind="2d_compare"),
        ],
        ignore_index=True,
        sort=False,
    )
    summary.to_csv(OUT_SUMMARY, index=False)
    write_audit(sample_2a, table_2b, table_2c, table_2d)


if __name__ == "__main__":
    main()
