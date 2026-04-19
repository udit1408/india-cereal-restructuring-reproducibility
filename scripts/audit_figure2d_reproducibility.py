from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path("/Users/udit/Documents/Shekhar_Nature")
AUDIT_ROOT = ROOT / "revision_2" / "_audit" / "Nitrogen-Surplus-restructuring"
CODE_DATA = AUDIT_ROOT / "code_data"
GENERATED = AUDIT_ROOT / "generated"
OUTPUT = ROOT / "revision_2" / "_audit" / "figure2d_reproducibility"

SOURCE_FILES = {
    "kharif": CODE_DATA / "kharif_waterdemand.csv",
    "rabi": CODE_DATA / "rabi_waterdemand.csv",
}

GENERATED_FILES = {
    "kharif": GENERATED / "nutrient_based_opt_cop_kharif.csv",
    "rabi": GENERATED / "nitrogen_surplus_rbased_opt_cop_rabi.csv",
}

KEYS = ["State", "District", "Crop"]


def load_source_duplicates() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for season, path in SOURCE_FILES.items():
        df = pd.read_csv(path)
        df = df.loc[df["Year"] == 2017, ["state", "district", "crop"]].copy()
        dup = (
            df.groupby(["state", "district", "crop"])
            .size()
            .reset_index(name="row_count")
            .query("row_count > 1")
            .sort_values(["state", "district", "crop"])
        )
        dup.insert(0, "season", season)
        frames.append(dup)
    return pd.concat(frames, ignore_index=True)


def load_generated_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_frames: list[pd.DataFrame] = []
    dedup_frames: list[pd.DataFrame] = []
    for season, path in GENERATED_FILES.items():
        df = pd.read_csv(path)
        df.insert(0, "season", season)
        raw_frames.append(df)
        dedup_frames.append(df.drop_duplicates(subset=["season", *KEYS]).copy())
    return pd.concat(raw_frames, ignore_index=True), pd.concat(dedup_frames, ignore_index=True)


def build_generated_duplicate_summary(raw: pd.DataFrame, dedup: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for season in ["kharif", "rabi"]:
        season_raw = raw.loc[raw["season"] == season].copy()
        season_dedup = dedup.loc[dedup["season"] == season].copy()
        group_counts = (
            season_raw.groupby(KEYS)
            .size()
            .reset_index(name="row_count")
        )
        duplicate_groups = int((group_counts["row_count"] > 1).sum())
        duplicate_rows = int(
            group_counts.loc[group_counts["row_count"] > 1, "row_count"].sum() - duplicate_groups
        )
        rows.append(
            {
                "season": season,
                "raw_rows": int(len(season_raw)),
                "dedup_rows": int(len(season_dedup)),
                "duplicate_groups": duplicate_groups,
                "duplicate_rows": duplicate_rows,
                "raw_original_total_ha": season_raw["Original Area (Hectare)"].sum(),
                "raw_optimized_total_ha": season_raw["Optimized Area (Hectare)"].sum(),
                "dedup_original_total_ha": season_dedup["Original Area (Hectare)"].sum(),
                "dedup_optimized_total_ha": season_dedup["Optimized Area (Hectare)"].sum(),
                "raw_minus_dedup_original_ha": season_raw["Original Area (Hectare)"].sum()
                - season_dedup["Original Area (Hectare)"].sum(),
                "raw_minus_dedup_optimized_ha": season_raw["Optimized Area (Hectare)"].sum()
                - season_dedup["Optimized Area (Hectare)"].sum(),
            }
        )
    return pd.DataFrame(rows)


def build_district_balance(dedup: pd.DataFrame) -> pd.DataFrame:
    district_balance = (
        dedup.groupby(["season", "State", "District"], as_index=False)[
            ["Original Area (Hectare)", "Optimized Area (Hectare)"]
        ]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_total_ha",
                "Optimized Area (Hectare)": "optimized_total_ha",
            }
        )
    )
    district_balance["delta_ha"] = (
        district_balance["optimized_total_ha"] - district_balance["original_total_ha"]
    )
    district_balance["abs_delta_ha"] = district_balance["delta_ha"].abs()
    return district_balance.sort_values("abs_delta_ha", ascending=False)


def build_crop_totals(dedup: pd.DataFrame) -> pd.DataFrame:
    crop_totals = (
        dedup.groupby("Crop", as_index=False)[["Original Area (Hectare)", "Optimized Area (Hectare)"]]
        .sum()
        .rename(
            columns={
                "Original Area (Hectare)": "original_total_ha",
                "Optimized Area (Hectare)": "optimized_total_ha",
            }
        )
    )
    crop_totals["delta_ha"] = crop_totals["optimized_total_ha"] - crop_totals["original_total_ha"]
    return crop_totals.sort_values("Crop")


def format_table(df: pd.DataFrame, float_cols: list[str]) -> str:
    display = df.copy()
    for col in float_cols:
        if col in display.columns:
            display[col] = display[col].map(lambda x: f"{x:,.4f}")
    return display.to_csv(index=False)


def write_report(
    source_duplicates: pd.DataFrame,
    duplicate_summary: pd.DataFrame,
    district_balance: pd.DataFrame,
    crop_totals: pd.DataFrame,
) -> None:
    overall_original = duplicate_summary["dedup_original_total_ha"].sum()
    overall_optimized = duplicate_summary["dedup_optimized_total_ha"].sum()
    overall_delta = overall_optimized - overall_original
    imbalanced = district_balance.loc[district_balance["abs_delta_ha"] > 1e-6].copy()

    report = f"""# Figure 2(d) reproducibility audit

This audit checks whether the currently available nitrogen-minimization outputs can support a defensible reconstruction of Figure 2(d), the before/after cropland-area transformation panel.

The short answer is no. A conserved transformation plot requires internally consistent area accounting. The current exported optimization tables do not satisfy that condition even after duplicate rows are removed.

Using the deduplicated exported files, total original area across kharif and rabi is {overall_original:,.4f} ha, whereas total optimized area is {overall_optimized:,.4f} ha. The implied net gain is {overall_delta:,.4f} ha. That should not happen in a valid area-preserving reallocation.

The issue is upstream, not just cosmetic. The 2017 source tables contain duplicated district-crop rows, and the legacy notebooks construct crop-level dictionaries using repeated assignment on the same `(state, district, crop)` key while district totals are built from grouped sums. The exported result tables are then merged back to the duplicated source rows, which duplicates some records again.

Because of this, the current artifacts are not sufficient to claim full reproducibility of Figure 2(d). A corrected rebuild would need to aggregate duplicate source rows before optimization, rerun the nitrogen-focused kharif and rabi models, export clean district-crop optimized areas, and only then construct a transition panel.

There is an additional modeling-to-visualization gap that should be handled explicitly. The optimization outputs pre- and post-optimization crop areas, but it does not optimize crop-to-crop transition flows directly. A Sankey-style panel therefore requires a deterministic allocation rule to map crop losses onto crop gains within each district-season. That rule needs to be documented if Figure 2(d) is regenerated.

## Exported file summary

{format_table(duplicate_summary, [c for c in duplicate_summary.columns if c.endswith('_ha')])}

## Source duplicates in 2017 inputs

{format_table(source_duplicates, [])}

## Largest district-season balance violations after deduplicating exported files

{format_table(imbalanced.head(15), ['original_total_ha', 'optimized_total_ha', 'delta_ha', 'abs_delta_ha'])}

There are {len(imbalanced)} district-season groups with non-zero balance error after deduplication.

## Deduplicated national crop totals

{format_table(crop_totals, ['original_total_ha', 'optimized_total_ha', 'delta_ha'])}
"""
    (OUTPUT / "figure2d_reproducibility_audit.md").write_text(report)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    source_duplicates = load_source_duplicates()
    raw, dedup = load_generated_frames()
    duplicate_summary = build_generated_duplicate_summary(raw, dedup)
    district_balance = build_district_balance(dedup)
    crop_totals = build_crop_totals(dedup)

    source_duplicates.to_csv(OUTPUT / "source_2017_duplicate_groups.csv", index=False)
    duplicate_summary.to_csv(OUTPUT / "generated_export_duplicate_summary.csv", index=False)
    district_balance.to_csv(OUTPUT / "district_season_area_balance.csv", index=False)
    crop_totals.to_csv(OUTPUT / "deduplicated_crop_area_totals.csv", index=False)
    write_report(source_duplicates, duplicate_summary, district_balance, crop_totals)


if __name__ == "__main__":
    main()
