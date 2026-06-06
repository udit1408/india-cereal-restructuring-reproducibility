#!/usr/bin/env python3
from __future__ import annotations

import re
import zipfile
from functools import lru_cache
from io import TextIOWrapper
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRICE_CSV = ROOT / "data" / "input" / "statewise_realized_price_vs_msp_2014_15_to_2018_19.csv"
DEFAULT_COST_SOURCE = ROOT / "data" / "input" / "costofproductiondataandcode.zip"
DEFAULT_COST_MEMBER = "cost_of_cultivation_data_raw.csv"
DEFAULT_SCENARIO_YEAR = "2017-18"
CANON_RE = re.compile(r"[^a-z0-9]+")

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

COST_CROP_MAP = {
    "Paddy": "rice",
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


def load_stateprice_csv(price_csv: Path = DEFAULT_PRICE_CSV) -> pd.DataFrame:
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
    return df[df["crop_key"].notna() & df["is_modeled_state"]].copy()


def load_cost_cultivation_csv(
    cost_source: Path = DEFAULT_COST_SOURCE,
    member_name: str = DEFAULT_COST_MEMBER,
) -> pd.DataFrame:
    cost_source = Path(cost_source)
    if cost_source.suffix.lower() == ".zip":
        with zipfile.ZipFile(cost_source) as archive:
            with archive.open(member_name) as handle:
                df = pd.read_csv(TextIOWrapper(handle, encoding="utf-8"))
    else:
        df = pd.read_csv(cost_source)

    df["year"] = df["year"].astype(str).str.strip()
    df["crop_name"] = df["crop_name"].astype(str).str.strip()
    df["state_name"] = df["state_name"].astype(str).str.strip()
    df["crop_key"] = df["crop_name"].map(COST_CROP_MAP)
    df["state_key"] = df["state_name"].map(canon)
    df["prod_cost_c2rev"] = pd.to_numeric(df["prod_cost_c2rev"], errors="coerce")
    df["prod_cost_c2rev"] = df["prod_cost_c2rev"].where(np.isfinite(df["prod_cost_c2rev"]), np.nan)
    df["is_modeled_state"] = (
        df["state_key"].ne("") & ~df["state_key"].isin(UNION_TERRITORY_KEYS)
    )
    return df[df["crop_key"].notna() & df["is_modeled_state"]].copy()


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
        if (
            pd.notna(row.output_lakh_sum)
            and pd.notna(row.production_tonne_sum)
            and row.output_lakh_sum > 0
            and row.production_tonne_sum > 0
        ):
            state_lookup[key] = (
                float(row.output_lakh_sum) * 100.0 / float(row.production_tonne_sum) * 100.0
            )
        elif pd.notna(row.mean_rupee_per_kg) and row.mean_rupee_per_kg > 0:
            state_lookup[key] = float(row.mean_rupee_per_kg) * 100.0
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
        if (
            pd.notna(row.output_lakh_sum)
            and pd.notna(row.production_tonne_sum)
            and row.output_lakh_sum > 0
            and row.production_tonne_sum > 0
        ):
            national_lookup[(str(row.Year), str(row.crop_key))] = (
                float(row.output_lakh_sum) * 100.0 / float(row.production_tonne_sum) * 100.0
            )

    return state_lookup, national_lookup, unusable_state_keys


def build_cost_inputs(
    df: pd.DataFrame,
) -> tuple[
    dict[tuple[str, str, str], float],
    dict[tuple[str, str], float],
]:
    grouped = (
        df[df["state_key"].ne("") & df["crop_key"].notna()]
        .groupby(["year", "state_key", "crop_key"], as_index=False)
        .agg(prod_cost_c2rev=("prod_cost_c2rev", "mean"))
        .reset_index(drop=True)
    )
    state_lookup: dict[tuple[str, str, str], float] = {}
    for row in grouped.itertuples(index=False):
        if pd.notna(row.prod_cost_c2rev) and row.prod_cost_c2rev > 0:
            state_lookup[(str(row.year), str(row.state_key), str(row.crop_key))] = float(
                row.prod_cost_c2rev
            )

    national_grouped = (
        df[df["crop_key"].notna()]
        .groupby(["year", "crop_key"], as_index=False)
        .agg(prod_cost_c2rev=("prod_cost_c2rev", "mean"))
        .reset_index(drop=True)
    )
    national_lookup: dict[tuple[str, str], float] = {}
    for row in national_grouped.itertuples(index=False):
        if pd.notna(row.prod_cost_c2rev) and row.prod_cost_c2rev > 0:
            national_lookup[(str(row.year), str(row.crop_key))] = float(row.prod_cost_c2rev)

    return state_lookup, national_lookup


@lru_cache(maxsize=1)
def load_price_bundle(
    price_csv: str | Path = DEFAULT_PRICE_CSV,
) -> tuple[
    pd.DataFrame,
    dict[str, dict[str, float]],
    dict[tuple[str, str, str], float],
    dict[tuple[str, str], float],
    set[tuple[str, str, str]],
]:
    price_df = load_stateprice_csv(Path(price_csv))
    ratio_scenarios = build_ratio_scenarios_from_stateprice(price_df)
    state_price_lookup, national_price_lookup, unusable_state_keys = build_stateprice_inputs(price_df)
    return price_df, ratio_scenarios, state_price_lookup, national_price_lookup, unusable_state_keys


@lru_cache(maxsize=1)
def load_cost_bundle(
    cost_source: str | Path = DEFAULT_COST_SOURCE,
    member_name: str = DEFAULT_COST_MEMBER,
) -> tuple[
    pd.DataFrame,
    dict[tuple[str, str, str], float],
    dict[tuple[str, str], float],
]:
    cost_df = load_cost_cultivation_csv(Path(cost_source), member_name=member_name)
    state_cost_lookup, national_cost_lookup = build_cost_inputs(cost_df)
    return cost_df, state_cost_lookup, national_cost_lookup


def load_ratio_scenarios() -> dict[str, dict[str, float]]:
    return load_price_bundle()[1]


def load_state_price_lookup() -> dict[tuple[str, str, str], float]:
    return load_price_bundle()[2]


def load_national_price_lookup() -> dict[tuple[str, str], float]:
    return load_price_bundle()[3]


def load_unusable_direct_price_keys() -> set[tuple[str, str, str]]:
    return load_price_bundle()[4]


def load_state_cost_lookup() -> dict[tuple[str, str, str], float]:
    return load_cost_bundle()[1]


def load_national_cost_lookup() -> dict[tuple[str, str], float]:
    return load_cost_bundle()[2]
