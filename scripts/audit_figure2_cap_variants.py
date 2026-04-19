#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
DATA_DIR = ROOT / "data" / "generated"

OUT_MD = DATA_DIR / "figure2_cap_variant_audit.md"
OUT_CSV = DATA_DIR / "figure2_cap_variant_summary.csv"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def markdown_table(frame: pd.DataFrame, ordered_columns: list[str]) -> str:
    display = frame[ordered_columns].copy()
    headers = ordered_columns
    widths = [max(len(str(col)), display[col].astype(str).map(len).max() if not display.empty else 0) for col in headers]

    def row(values: list[object]) -> str:
        return "| " + " | ".join(str(value).ljust(width) for value, width in zip(values, widths)) + " |"

    lines = [row(headers), row(["-" * width for width in widths])]
    for _, record in display.iterrows():
        lines.append(row([record[col] for col in headers]))
    return "\n".join(lines)


def git_head(ref: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(AUDIT_ROOT), "rev-parse", ref],
        text=True,
    ).strip()


def git_diff_name_status(base: str, head: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(AUDIT_ROOT), "diff", "--name-status", f"{base}..{head}"],
        text=True,
    ).strip()
    return [line for line in output.splitlines() if line.strip()]


def compute_no_cap_figure2b_table() -> pd.DataFrame:
    module = load_module(ROOT / "scripts" / "generate_figure2b_clean.py", "figure2b_clean_module")
    layout = module.default_layout(module.AUDIT_ROOT)
    contexts = {
        season: module.build_context(layout, season, notebook_name)
        for season, notebook_name in module.SEASON_NOTEBOOKS.items()
    }
    for context in contexts.values():
        context["max_area_constraints"] = {}
    table, _ = module.build_metric_table(contexts)
    table["variant"] = "no_historical_caps"
    return table


def compute_no_cap_figure2d_summary() -> pd.DataFrame:
    module = load_module(ROOT / "scripts" / "generate_figure2d_clean.py", "figure2d_clean_module")
    layout = module.default_layout(module.AUDIT_ROOT)

    area_frames: list[pd.DataFrame] = []
    for season, notebook_name in module.SEASON_NOTEBOOKS.items():
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            context = module._build_season_context(layout, season, notebook_name)
            area_frame, _, _ = module.solve_nitrogen_focused_areas(
                context,
                solver_name="highs",
                income_mode="profit",
                use_historical_caps=False,
            )
        area_frames.append(area_frame)

    combined = pd.concat(area_frames, ignore_index=True)
    summary = (
        combined.groupby("Crop", as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_ha",
                "Optimized Area (Hectare)": "optimized_ha",
            }
        )
    )
    summary["pct_change"] = 100.0 * (summary["optimized_ha"] - summary["original_ha"]) / summary["original_ha"]
    return summary


def build_figure2a_summary(no_cap_2b: pd.DataFrame) -> pd.DataFrame:
    legacy = pd.read_csv(AUDIT_ROOT / "outputs" / "generated" / "figure2a" / "figure2a_combined_frontier.csv")
    clean = pd.read_csv(DATA_DIR / "figure2a_clean_rebuild_combined_by_alpha.csv")

    endpoint_rows: list[dict[str, object]] = []
    for scenario, alpha in [("Water based", 0.0), ("Nitrogen based", 1.0)]:
        legacy_row = legacy.loc[legacy["Alpha"] == alpha].iloc[0]
        clean_row = clean.loc[clean["Alpha"] == alpha].iloc[0]
        no_cap_row = no_cap_2b.loc[
            (no_cap_2b["scenario"] == scenario) & (no_cap_2b["metric"] == "Nitrogen Surplus")
        ].iloc[0]
        no_cap_water_row = no_cap_2b.loc[
            (no_cap_2b["scenario"] == scenario) & (no_cap_2b["metric"] == "Water Demand")
        ].iloc[0]

        endpoint_rows.extend(
            [
                {
                    "panel": "2a",
                    "scenario": scenario,
                    "variant": "legacy_plotted",
                    "nitrogen_tg": float(legacy_row["nitrogen_mt"]),
                    "water_bcm": float(legacy_row["water_bcm"]),
                },
                {
                    "panel": "2a",
                    "scenario": scenario,
                    "variant": "clean_capped",
                    "nitrogen_tg": float(clean_row["nitrogen_mt"]),
                    "water_bcm": float(clean_row["water_bcm"]),
                },
                {
                    "panel": "2a",
                    "scenario": scenario,
                    "variant": "clean_no_caps",
                    "nitrogen_tg": float(no_cap_row["optimized_total"]) / 1e9,
                    "water_bcm": float(no_cap_water_row["optimized_total"]) / 1e9,
                },
            ]
        )

    summary = pd.DataFrame(endpoint_rows)
    summary["nitrogen_tg"] = summary["nitrogen_tg"].map(lambda value: fmt(value, 3))
    summary["water_bcm"] = summary["water_bcm"].map(lambda value: fmt(value, 3))
    return summary


def build_figure2b_summary(no_cap_2b: pd.DataFrame) -> pd.DataFrame:
    clean = pd.read_csv(DATA_DIR / "figure2b_clean_method_consistent_values.csv").copy()
    clean["variant"] = "clean_capped"
    legacy = pd.read_csv(DATA_DIR / "figure2b_regenerated_deterministic_values.csv").copy()
    legacy["variant"] = "legacy_endpoint_exports"
    no_cap = no_cap_2b.copy()

    focus_metrics = ["Nitrogen Surplus", "Water Demand", "Profit", "Calorie"]
    merged = pd.concat([clean, no_cap, legacy], ignore_index=True)
    merged = merged[merged["metric"].isin(focus_metrics)].copy()
    merged["pct_reduction"] = merged["pct_reduction"].map(lambda value: fmt(float(value), 3))
    return merged[["scenario", "variant", "metric", "pct_reduction"]]


def build_figure2c_summary() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    configs = {
        "clean_capped": DATA_DIR / "figure2c" / "combined_method_consistent.csv",
        "clean_no_caps_state_retention": DATA_DIR / "figure2c" / "combined_no_historical_caps.csv",
        "clean_no_caps_district_retention": DATA_DIR / "figure2c" / "combined_equation_aligned_district_no_caps.csv",
    }

    for variant, path in configs.items():
        frame = pd.read_csv(path)
        endpoint = frame.loc[frame["gamma"] == 0.0].iloc[0]
        rows.append(
            {
                "panel": "2c",
                "variant": variant,
                "n_surplus_reduction_pct": fmt(float(endpoint["pct_reduction_n_surplus"]), 3),
                "realized_staple_replacement_pct": fmt(float(endpoint["realized_staple_replacement_pct"]), 3),
            }
        )

    return pd.DataFrame(rows)


def build_figure2d_summary() -> pd.DataFrame:
    capped = pd.read_csv(DATA_DIR / "figure2d" / "figure2d_method_consistent_crop_summary.csv")
    capped = capped.rename(
        columns={
            "original_total_ha": "original_ha",
            "optimized_total_ha": "optimized_ha",
        }
    )
    no_cap = compute_no_cap_figure2d_summary()

    rows: list[dict[str, object]] = []
    for variant, frame in [("clean_capped", capped), ("clean_no_caps", no_cap)]:
        for crop in ["rice", "wheat"]:
            record = frame.loc[frame["Crop"] == crop].iloc[0]
            rows.append(
                {
                    "panel": "2d",
                    "variant": variant,
                    "crop": crop,
                    "original_mha": fmt(float(record["original_ha"]) / 1e6, 3),
                    "optimized_mha": fmt(float(record["optimized_ha"]) / 1e6, 3),
                    "pct_change": fmt(float(record["pct_change"]), 3),
                }
            )

    legacy_text_rows = [
        {
            "panel": "2d",
            "variant": "legacy_reported_text",
            "crop": "rice",
            "original_mha": "",
            "optimized_mha": "",
            "pct_change": "-38.000",
        },
        {
            "panel": "2d",
            "variant": "legacy_reported_text",
            "crop": "wheat",
            "original_mha": "",
            "optimized_mha": "",
            "pct_change": "-22.600",
        },
    ]
    return pd.concat([pd.DataFrame(rows), pd.DataFrame(legacy_text_rows)], ignore_index=True)


def main() -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    head = git_head("HEAD")
    origin = git_head("origin/main")
    diff_lines = git_diff_name_status(head, origin)

    no_cap_2b = compute_no_cap_figure2b_table()
    figure2a_summary = build_figure2a_summary(no_cap_2b)
    figure2b_summary = build_figure2b_summary(no_cap_2b)
    figure2c_summary = build_figure2c_summary()
    figure2d_summary = build_figure2d_summary()

    long_rows: list[dict[str, object]] = []
    for _, record in figure2a_summary.iterrows():
        long_rows.append(
            {
                "panel": "2a",
                "variant": record["variant"],
                "scenario_or_crop": record["scenario"],
                "metric": "nitrogen_tg",
                "value": record["nitrogen_tg"],
            }
        )
        long_rows.append(
            {
                "panel": "2a",
                "variant": record["variant"],
                "scenario_or_crop": record["scenario"],
                "metric": "water_bcm",
                "value": record["water_bcm"],
            }
        )
    for _, record in figure2b_summary.iterrows():
        long_rows.append(
            {
                "panel": "2b",
                "variant": record["variant"],
                "scenario_or_crop": record["scenario"],
                "metric": record["metric"],
                "value": record["pct_reduction"],
            }
        )
    for _, record in figure2c_summary.iterrows():
        long_rows.append(
            {
                "panel": "2c",
                "variant": record["variant"],
                "scenario_or_crop": "combined endpoint",
                "metric": "n_surplus_reduction_pct",
                "value": record["n_surplus_reduction_pct"],
            }
        )
        long_rows.append(
            {
                "panel": "2c",
                "variant": record["variant"],
                "scenario_or_crop": "combined endpoint",
                "metric": "realized_staple_replacement_pct",
                "value": record["realized_staple_replacement_pct"],
            }
        )
    for _, record in figure2d_summary.iterrows():
        long_rows.append(
            {
                "panel": "2d",
                "variant": record["variant"],
                "scenario_or_crop": record["crop"],
                "metric": "pct_change",
                "value": record["pct_change"],
            }
        )

    pd.DataFrame(long_rows).to_csv(OUT_CSV, index=False)

    diff_text = "\n".join(f"- `{line}`" for line in diff_lines) if diff_lines else "- No remote file differences detected."
    note = f"""# Figure 2 cap-variant audit

This note compares two coherent Figure 2 branches:

1. `clean_capped`: the strict method-consistent rebuild with unchanged district cropped area, locally grown crops only, state calorie and profit constraints, and district-crop historical maximum area caps.
2. `clean_no_caps`: the same optimization but with the district-crop historical maximum area caps removed.

The GitHub audit root currently resolves to:

- local HEAD: `{head}`
- `origin/main`: `{origin}`

Remote diff relative to the local audit checkout:

{diff_text}

The comparisons below show that the historical maximum area caps are the dominant driver of the magnitude gap between the strict rebuild and the legacy Figure 2 outputs.

## Figure 2(a) endpoint comparison

`legacy_plotted` refers to the archived combined frontier CSV used for the old panel. `clean_no_caps` uses annual sums from the no-cap endpoint solves rather than the old plotting-stage averaging.

{markdown_table(figure2a_summary, ['scenario', 'variant', 'nitrogen_tg', 'water_bcm'])}

## Figure 2(b) percentage changes

Values are annual percentage reductions relative to the 2017 baseline. Negative values for `Profit` or `Calorie` indicate increases rather than declines.

{markdown_table(figure2b_summary, ['scenario', 'variant', 'metric', 'pct_reduction'])}

Removing the historical caps pulls the clean endpoint bars close to the legacy export-centered bars:

- water-based water-demand reduction: `11.519%` with caps versus `44.493%` without caps, compared with the legacy `43.377%`;
- nitrogen-based nitrogen-surplus reduction: `3.362%` with caps versus `21.408%` without caps, compared with the legacy `21.243%`;
- nitrogen-based water-demand co-benefit: `-0.637%` with caps versus `36.257%` without caps, compared with the legacy `35.340%`.

## Figure 2(c) combined endpoint comparison

The endpoint reported here is the `gamma = 0` case, which corresponds to the strongest relaxation of the staple-retention parameter.

{markdown_table(figure2c_summary, ['variant', 'n_surplus_reduction_pct', 'realized_staple_replacement_pct'])}

For Figure 2(c), the no-cap branch nearly restores the legacy nitrogen-surplus reduction magnitude. The difference between the state-retention and district-retention variants is much smaller than the difference caused by switching the historical caps on or off.

## Figure 2(d) rice and wheat area shifts

`legacy_reported_text` is the crop-area change described in the old main-text narrative, included here only as a reference point.

{markdown_table(figure2d_summary, ['variant', 'crop', 'original_mha', 'optimized_mha', 'pct_change'])}

For Figure 2(d), the no-cap branch moves the transition magnitudes materially toward the legacy narrative, especially for rice, but it does not fully recover the previously reported wheat shift. This means the historical caps explain most of the gap, but the old alluvial panel also depended on additional legacy transition-accounting choices.

## Working conclusion

There are now two internally coherent options:

1. Keep the paper methods summary as currently written, retain the historical caps, and use the strict `clean_capped` Figure 2 panels with smaller but fully aligned effect sizes.
2. Revise the Methods explicitly so that the main Figure 2 optimization does not impose district-crop historical maximum area caps, then use annual summed endpoints for Figure 2(a) and the corresponding no-cap versions of Figure 2(b), Figure 2(c), and Figure 2(d).

The important point is that the legacy magnitudes are not being reproduced by a hidden bug hunt anymore; they are being reproduced when the cap assumption is relaxed in a controlled and transparent way.
"""
    OUT_MD.write_text(note)
    print(f"wrote_markdown: {OUT_MD}")
    print(f"wrote_csv: {OUT_CSV}")


if __name__ == "__main__":
    main()
