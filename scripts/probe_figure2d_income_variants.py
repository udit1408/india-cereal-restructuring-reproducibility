#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pandas as pd
import pulp


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
OUT_CSV = ROOT / "data" / "generated" / "figure2d_income_variant_probe.csv"
OUT_MD = ROOT / "data" / "generated" / "figure2d_income_variant_probe.md"

sys.path.insert(0, str(AUDIT_ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from repro.config import default_layout  # noqa: E402
from repro.figure2a_clean_rebuild import (  # noqa: E402
    CALORIE_SCALE,
    INCOME_SCALE,
    _build_season_context,
    _relaxed_rhs,
    _sanitize,
    _solver,
)


def solve_variant(context: dict[str, object], income_mode: str | None) -> pd.DataFrame:
    pairs_with_area = context["pairs_with_area"]
    crops_by_pair = context["crops_by_pair"]
    current_area = context["current_area"]
    nitrogen_rate = context["nitrogen_rate"]
    nitrogen_removal_rate = context["nitrogen_removal_rate"]
    yield_data = context["yield_data"]
    calories_per_prod = context["calories_per_prod"]
    cost_per_prod = context["cost_per_prod"]
    msp_per_prod = context["msp_per_prod"]
    initial_state_calories = context["initial_state_calories"]
    initial_state_profit = context["initial_state_profit"]
    initial_state_msp = context["initial_state_msp"]
    districts_by_state = context["districts_by_state"]
    states = context["states"]
    frame = context["frame"]
    season = str(context["season"])

    original_area = frame.groupby(["State", "District", "Crop"])["Area (Hectare)"].sum().astype(float).to_dict()

    prob = pulp.LpProblem(f"Figure2DProbe_{season}_{income_mode or 'none'}", pulp.LpMinimize)
    x: dict[tuple[str, str, str], pulp.LpVariable] = {}
    for state, district in pairs_with_area:
        for crop in crops_by_pair[(state, district)]:
            var_name = f"area__{_sanitize(state)}__{_sanitize(district)}__{_sanitize(crop)}"
            x[(state, district, crop)] = pulp.LpVariable(var_name, lowBound=0, cat=pulp.LpContinuous)

    prob += pulp.lpSum(
        x[(state, district, crop)]
        * (
            nitrogen_rate.get((state, district, crop), 0.0)
            - yield_data.get((state, district, crop), 0.0)
            * nitrogen_removal_rate.get((state, district, crop), 0.0)
        )
        for state, district, crop in x
    )

    for state, district in pairs_with_area:
        prob += (
            pulp.lpSum(x[(state, district, crop)] for crop in crops_by_pair[(state, district)])
            == current_area.get((state, district), 0.0)
        )

    for state in states:
        valid_districts = districts_by_state.get(state, [])
        calorie_terms = [
            x[(state, district, crop)]
            * yield_data.get((state, district, crop), 0.0)
            * calories_per_prod.get((state, district, crop), 0.0)
            for district in valid_districts
            for crop in crops_by_pair.get((state, district), [])
            if (state, district, crop) in x
        ]
        prob += pulp.lpSum(calorie_terms) / CALORIE_SCALE >= _relaxed_rhs(
            float(initial_state_calories.get(state, 0.0))
        ) / CALORIE_SCALE

        if income_mode == "profit":
            income_terms = [
                x[(state, district, crop)]
                * yield_data.get((state, district, crop), 0.0)
                * 0.01
                * (
                    msp_per_prod.get((state, district, crop), 0.0)
                    - cost_per_prod.get((state, district, crop), 0.0)
                )
                for district in valid_districts
                for crop in crops_by_pair.get((state, district), [])
                if (state, district, crop) in x
            ]
            prob += pulp.lpSum(income_terms) / INCOME_SCALE >= _relaxed_rhs(
                float(initial_state_profit.get(state, 0.0))
            ) / INCOME_SCALE
        elif income_mode == "msp":
            income_terms = [
                x[(state, district, crop)]
                * yield_data.get((state, district, crop), 0.0)
                * 0.01
                * msp_per_prod.get((state, district, crop), 0.0)
                for district in valid_districts
                for crop in crops_by_pair.get((state, district), [])
                if (state, district, crop) in x
            ]
            prob += pulp.lpSum(income_terms) / INCOME_SCALE >= _relaxed_rhs(
                float(initial_state_msp.get(state, 0.0))
            ) / INCOME_SCALE
        elif income_mode is None:
            pass
        else:
            raise ValueError(f"Unsupported income mode: {income_mode}")

    prob.solve(_solver("highs"))
    status = pulp.LpStatus.get(prob.status, str(prob.status))
    if status != "Optimal":
        raise RuntimeError(f"{season} {income_mode or 'none'} returned {status}")

    rows = []
    for (state, district, crop), variable in sorted(x.items()):
        rows.append(
            {
                "season": season,
                "State": state,
                "District": district,
                "Crop": crop,
                "Original Area (Hectare)": float(original_area.get((state, district, crop), 0.0)),
                "Optimized Area (Hectare)": float(variable.value() or 0.0),
            }
        )
    return pd.DataFrame(rows)


def build_probe() -> pd.DataFrame:
    layout = default_layout(AUDIT_ROOT)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        kharif_context = _build_season_context(layout, "kharif", "kharif_nitrogen_min.ipynb")
        rabi_context = _build_season_context(layout, "rabi", "rabi__nitrogen_kharif_cop.ipynb")

    combos = [
        ("profit_profit", "profit", "profit"),
        ("profit_msp", "profit", "msp"),
        ("profit_none", "profit", None),
    ]

    rows = []
    for label, kharif_mode, rabi_mode in combos:
        combined = pd.concat(
            [
                solve_variant(kharif_context, kharif_mode),
                solve_variant(rabi_context, rabi_mode),
            ],
            ignore_index=True,
        )
        summary = (
            combined.groupby("Crop", as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
            .sum()
            .rename(
                columns={
                    "Original Area (Hectare)": "original_total_ha",
                    "Optimized Area (Hectare)": "optimized_total_ha",
                }
            )
        )
        summary["pct_change"] = (
            100.0 * (summary["optimized_total_ha"] - summary["original_total_ha"]) / summary["original_total_ha"]
        )
        summary["income_variant"] = label
        rows.append(summary)
    return pd.concat(rows, ignore_index=True)


def write_markdown(frame: pd.DataFrame) -> None:
    lookup = frame.pivot(index="income_variant", columns="Crop", values="pct_change")
    lines = [
        "# Figure 2(d) income-constraint probe",
        "",
        "This probe keeps the no-historical-cap nitrogen-minimization setup and changes only the seasonal income floor:",
        "",
        "- `profit_profit`: profit floor in both kharif and rabi.",
        "- `profit_msp`: profit floor in kharif, MSP floor in rabi.",
        "- `profit_none`: profit floor in kharif, no income floor in rabi.",
        "",
        "Rice and wheat area shifts (% change from baseline):",
        "",
        "| income_variant | rice | wheat |",
        "| --- | --- | --- |",
    ]
    for variant in ["profit_profit", "profit_msp", "profit_none"]:
        lines.append(
            f"| {variant} | {lookup.loc[variant, 'rice']:.3f} | {lookup.loc[variant, 'wheat']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The wheat-area reduction becomes materially larger when the rabi income floor is removed,",
            "but it still does not reach the manuscript text value of -22.6%.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines))


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame = build_probe()
    frame.to_csv(OUT_CSV, index=False)
    write_markdown(frame)


if __name__ == "__main__":
    main()
