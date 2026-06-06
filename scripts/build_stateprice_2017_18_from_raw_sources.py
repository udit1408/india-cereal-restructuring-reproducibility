#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GVO_XLSX: Path | None = None
DEFAULT_PRODUCTION_CSV: Path | None = None
DEFAULT_OUTPUT_CSV = ROOT / "data" / "generated" / "derived_inputs" / "stateprice_2017_18_from_raw_sources.csv"
DEFAULT_COMPARE_CSV = ROOT / "data" / "input" / "statewise_realized_price_vs_msp_2014_15_to_2018_19.csv"
YEAR = "2017-18"
VALUE_YEAR_COL = 8

CANON_RE = re.compile(r"[^a-z0-9]+")
STATE_ALIASES = {
    "andaman and nicobar islands": "andaman and nicobar",
    "andaman and nicobar": "andaman and nicobar",
    "a and n islands": "andaman and nicobar",
    "a n islands": "andaman and nicobar",
    "jammu and kashmir": "jammu and kashmir",
    "dadra and nagar haveli": "dadra and nagar haveli",
    "daman and diu": "daman and diu",
    "pondicherry": "puducherry",
}

CROP_BLOCKS = {
    "धान": "Rice",
    "गेहूं": "Wheat",
    "गेहूँ": "Wheat",
    "ज्वार": "Jowar",
    "बाजरा": "Bajra",
    "मक्का": "Maize",
    "रागी": "Ragi",
}


def canon(text: object) -> str:
    value = "" if pd.isna(text) else str(text).strip().lower()
    value = value.replace("&", "and")
    value = CANON_RE.sub(" ", value).strip()
    value = re.sub(r"\s+", " ", value)
    return STATE_ALIASES.get(value, value)


def read_gvo_blocks(path: Path) -> pd.DataFrame:
    sheet = pd.read_excel(path, sheet_name="Statewise estimates", header=None)
    rows: list[dict[str, object]] = []

    for idx, cell in sheet[0].items():
        crop = CROP_BLOCKS.get(str(cell).strip())
        if crop is None:
            continue
        header_row = idx + 2
        data_row = header_row + 1
        while data_row < len(sheet):
            english_state = sheet.iat[data_row, 31]
            value_lakh = sheet.iat[data_row, VALUE_YEAR_COL]
            serial = sheet.iat[data_row, 0]
            if pd.isna(english_state):
                break
            if str(english_state).strip().lower() == "all india":
                break
            if pd.isna(serial):
                break
            rows.append(
                {
                    "Crop": crop,
                    "State": str(english_state).strip(),
                    "Year": YEAR,
                    "Output_lakh": float(value_lakh) if pd.notna(value_lakh) else 0.0,
                }
            )
            data_row += 1

    out = pd.DataFrame(rows)
    out["state_key"] = out["State"].map(canon)
    return out


def read_production(path: Path) -> pd.DataFrame:
    prod = pd.read_csv(path)
    prod = prod[prod["Season"].astype(str).str.strip().str.lower() == "total"].copy()
    prod = prod[prod["Crop"].isin(sorted(set(CROP_BLOCKS.values())))]
    prod["state_key"] = prod["State"].map(canon)
    prod["Production_tonne"] = pd.to_numeric(prod["Production-2017-18"], errors="coerce")
    prod = prod[["Crop", "State", "state_key", "Production_tonne"]].copy()
    return prod


def build_price_table(gvo: pd.DataFrame, production: pd.DataFrame) -> pd.DataFrame:
    merged = gvo.merge(
        production[["Crop", "state_key", "Production_tonne"]],
        on=["Crop", "state_key"],
        how="left",
    )
    merged["rupee_per_kg"] = (merged["Output_lakh"] * 100.0) / merged["Production_tonne"]
    merged.loc[merged["Production_tonne"].fillna(0).le(0), "rupee_per_kg"] = pd.NA
    national = (
        merged.groupby("Crop", as_index=False)[["Output_lakh", "Production_tonne"]]
        .sum(min_count=1)
        .rename(columns={"Output_lakh": "national_output_lakh", "Production_tonne": "national_production_tonne"})
    )
    national["national_mean_rupee_per_kg"] = (
        national["national_output_lakh"] * 100.0 / national["national_production_tonne"]
    )
    merged = merged.merge(national[["Crop", "national_mean_rupee_per_kg"]], on="Crop", how="left")
    merged["price_source"] = merged["rupee_per_kg"].apply(
        lambda x: "state_positive" if pd.notna(x) and float(x) > 0 else "national_mean_fill"
    )
    merged["rupee_per_kg_filled"] = merged["rupee_per_kg"]
    mask = merged["rupee_per_kg_filled"].isna() | merged["rupee_per_kg_filled"].le(0)
    merged.loc[mask, "rupee_per_kg_filled"] = merged.loc[mask, "national_mean_rupee_per_kg"]
    return merged[
        [
            "Crop",
            "State",
            "Year",
            "Output_lakh",
            "Production_tonne",
            "rupee_per_kg",
            "national_mean_rupee_per_kg",
            "rupee_per_kg_filled",
            "price_source",
            "state_key",
        ]
    ].sort_values(["Crop", "State"]).reset_index(drop=True)


def compare_against_existing(raw_df: pd.DataFrame, compare_csv: Path) -> pd.DataFrame:
    existing = pd.read_csv(compare_csv)
    existing = existing[existing["Year"].astype(str) == YEAR].copy()
    existing["state_key"] = existing["State"].map(canon)
    merged = raw_df.merge(
        existing[["Crop", "state_key", "rupee_per_kg"]],
        on=["Crop", "state_key"],
        how="left",
        suffixes=("_raw", "_existing"),
    )
    merged["delta_rupee_per_kg"] = merged["rupee_per_kg_raw"] - merged["rupee_per_kg_existing"]
    return merged.sort_values(["Crop", "State"]).reset_index(drop=True)


def main(gvo_xlsx: Path, production_csv: Path, output_csv: Path, compare_csv: Path | None) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    gvo = read_gvo_blocks(gvo_xlsx)
    production = read_production(production_csv)
    derived = build_price_table(gvo, production)
    derived.to_csv(output_csv, index=False)
    print(f"output_csv: {output_csv}")
    print(f"rows: {len(derived)}")
    print(derived.groupby('Crop')['price_source'].value_counts().to_string())
    if compare_csv is not None and compare_csv.exists():
        cmp = compare_against_existing(derived, compare_csv)
        cmp_csv = output_csv.with_name(output_csv.stem + "_vs_existing.csv")
        cmp.to_csv(cmp_csv, index=False)
        print(f"compare_csv: {cmp_csv}")
        summary = (
            cmp.groupby("Crop", as_index=False)["delta_rupee_per_kg"]
            .agg(["count", "max", "min", "mean"])
            .reset_index()
        )
        print(summary.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Build a 2017-18 statewise realized-price table from raw official GVO and "
            "production files downloaded from MoSPI and UPAg."
        )
    )
    parser.add_argument("--gvo-xlsx", type=Path, default=DEFAULT_GVO_XLSX)
    parser.add_argument("--production-csv", type=Path, default=DEFAULT_PRODUCTION_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--compare-csv", type=Path, default=DEFAULT_COMPARE_CSV)
    args = parser.parse_args()
    if args.gvo_xlsx is None or args.production_csv is None:
        parser.error(
            "--gvo-xlsx and --production-csv are required. Download the raw official files "
            "first, then pass their paths explicitly."
        )
    main(args.gvo_xlsx, args.production_csv, args.output_csv, args.compare_csv)
