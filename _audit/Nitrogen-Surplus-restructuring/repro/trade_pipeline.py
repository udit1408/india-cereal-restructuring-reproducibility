from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import RepoLayout, default_layout
from .io import prepare_trade_flows, read_generated_csv, read_repo_csv, strip_unnamed_columns, write_csv


STATE_MAPPING = {
    "Andhra(excluding ports)": "ANDHRA PRADESH",
    "Andhra(excluding ports) ": "ANDHRA PRADESH",
    "ANDHRA PRADESH & TELANGANA": "TELANGANA",
    "Other ports of Andhra": "ANDHRA PRADESH",
    "Gujarat(excluding ports)": "GUJARAT",
    "Other ports of Gujarat": "GUJARAT",
    "Karnataka(excluding ports": "KARNATAKA",
    "Other ports of Karnataka": "KARNATAKA",
    "Kerala(excluding ports)": "KERALA",
    "Other ports of Kerala": "KERALA",
    "Maharashtra(excluding ports)": "MAHARASHTRA",
    "Other ports of Maharashtra": "MAHARASHTRA",
    "Tamil Nadu(excluding ports)": "TAMIL NADU",
    "Other ports of Tamil Nadu": "TAMIL NADU",
    "West Bengal(excluding ports) ": "WEST BENGAL",
    "Other ports of West Bengal": "WEST BENGAL",
    "Chattishgarh": "CHATTISGARH",
    "RAJASTHAN": "RAJASHTHAN",
    "Arunachal Pradesh": "ARUNACHAL PRADESH",
    "Assam": "ASSAM",
    "Bihar": "BIHAR",
    "Chandigarh": "CHANDIGARH",
    "Delhi": "DELHI",
    "Goa": "GOA",
    "Haryana": "HARYANA",
    "Himachal Pradesh": "HIMACHAL PRADESH",
    "Jammu": "JAMMU & KASHMIR",
    "Jharkhand": "JHARKHAND",
    "Madhya Pradesh": "MADHYA PRADESH",
    "Manipur": "MANIPUR",
    "Meghalaya": "MEGHALAYA",
    "Mizoram": "MIZORAM",
    "Nagaland": "NAGALAND",
    "Odisha": "ODISHA",
    "Orissa": "ODISHA",
    "Pondicheri and Karikal": "PUDUCHERRY",
    "Puducherry": "PUDUCHERRY",
    "Punjab": "PUNJAB",
    "Rajasthan": "RAJASHTHAN",
    "Tripura": "TRIPURA",
    "Uttar Pradesh": "UTTAR PRADESH",
    "Uttaranchal": "UTTARAKHAND",
}

DROP_TARGET_VALUES = {"T  O  T  A  L", "OUTWARD -->", "OUTWARD TOTAL -->"}
DROP_SOURCE_VALUES = {"nan"}

YEARS_FOR_AVERAGE = (2016, 2017, 2018)
MILLET_MAIZE_KCAL_PER_QTL = 331500
JOWAR_BAJRA_KCAL_PER_QTL = 341000


def normalize_alternative_trade(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized["Target"] = normalized["Target"].replace(STATE_MAPPING)
    normalized["Source"] = normalized["Source"].replace(STATE_MAPPING)
    grouped = normalized.groupby(["Target", "Source", "year"], as_index=False)["quantity"].sum()
    grouped = grouped[~grouped["Target"].isin(DROP_TARGET_VALUES)]
    grouped = grouped[~grouped["Source"].isin(DROP_SOURCE_VALUES)]
    grouped["year"] = grouped["year"].astype(int)
    grouped.loc[grouped["year"] == 2020, "quantity"] *= 10
    return grouped


def mean_trade_over_years(df: pd.DataFrame, years: tuple[int, ...] = YEARS_FOR_AVERAGE) -> pd.DataFrame:
    filtered = df[df["year"].isin(years)].copy()
    return filtered.groupby(["Target", "Source"], as_index=False)["quantity"].mean()


def quantity_to_kcal(df: pd.DataFrame, kcal_per_qtl: float) -> pd.DataFrame:
    result = df.copy()
    result["quantity_kcal"] = result["quantity"] * kcal_per_qtl
    return result


def load_baseline_production_2017(layout: RepoLayout | None = None) -> pd.DataFrame:
    active_layout = layout or default_layout()
    prod_kharif = strip_unnamed_columns(read_repo_csv("kharif_df.csv", layout=active_layout))
    prod_rabi = strip_unnamed_columns(read_repo_csv("rabi_df.csv", layout=active_layout))
    prod_kharif_2017 = prod_kharif[prod_kharif["Year"] == 2017]
    prod_rabi_2017 = prod_rabi[prod_rabi["Year"] == 2017]
    combined = pd.concat([prod_kharif_2017, prod_rabi_2017], ignore_index=True)
    combined = combined.groupby(["state", "crop", "Year"], as_index=False).sum()
    combined = combined[combined["crop"] != "barley"].copy()
    combined["crop"] = combined["crop"].str.lower()
    return combined


def load_optimized_production(layout: RepoLayout | None = None) -> pd.DataFrame:
    active_layout = layout or default_layout()
    kharif_opt = strip_unnamed_columns(read_generated_csv("nutrient_based_opt_cop_kharif.csv", layout=active_layout))
    rabi_opt = strip_unnamed_columns(
        read_generated_csv("nitrogen_surplus_rbased_opt_cop_rabi.csv", layout=active_layout)
    )
    combined = pd.concat([kharif_opt, rabi_opt], ignore_index=True)
    return combined.groupby(["State", "Crop"], as_index=False).sum()


def generated_dependency_status(layout: RepoLayout | None = None) -> pd.DataFrame:
    active_layout = layout or default_layout()
    required = [
        "nutrient_based_opt_cop_kharif.csv",
        "nitrogen_surplus_rbased_opt_cop_rabi.csv",
    ]
    rows: list[dict[str, str | bool]] = []
    for name in required:
        try:
            read_generated_csv(name, layout=active_layout, nrows=1)
            rows.append({"filename": name, "available": True, "status": "found"})
        except FileNotFoundError:
            rows.append({"filename": name, "available": False, "status": "missing"})
    return pd.DataFrame(rows)


def build_trade_stage_inputs(layout: RepoLayout | None = None) -> dict[str, pd.DataFrame]:
    active_layout = layout or default_layout()

    rice_trade = prepare_trade_flows("rice_trade_quintal.csv", "rice_avg_qtl_2009_19.csv", layout=active_layout)
    wheat_trade = prepare_trade_flows("wheat_trade_quintal.csv", "wheat_avg_qtl_2009_19.csv", layout=active_layout)

    jowar_bajra_raw = read_repo_csv("jowar_bajra_2009_2019.csv", layout=active_layout)
    millet_maize_raw = read_repo_csv("maize_millet_2009_2019.csv", layout=active_layout)

    jowar_bajra_grouped = normalize_alternative_trade(jowar_bajra_raw)
    millet_maize_grouped = normalize_alternative_trade(millet_maize_raw)

    jowar_bajra_mean = mean_trade_over_years(jowar_bajra_grouped)
    millet_maize_mean = mean_trade_over_years(millet_maize_grouped)

    outputs = {
        "rice_trade_normalized": rice_trade,
        "wheat_trade_normalized": wheat_trade,
        "jowar_bajra_grouped": jowar_bajra_grouped,
        "millet_maize_grouped": millet_maize_grouped,
        "jowar_bajra_mean_qtl_2016_2018": jowar_bajra_mean,
        "millet_maize_mean_qtl_2016_2018": millet_maize_mean,
        "jowar_bajra_mean_kcal_2016_2018": quantity_to_kcal(jowar_bajra_mean, JOWAR_BAJRA_KCAL_PER_QTL),
        "millet_maize_mean_kcal_2016_2018": quantity_to_kcal(millet_maize_mean, MILLET_MAIZE_KCAL_PER_QTL),
        "baseline_production_2017": load_baseline_production_2017(layout=active_layout),
        "generated_dependency_status": generated_dependency_status(layout=active_layout),
    }
    if outputs["generated_dependency_status"]["available"].all():
        outputs["optimized_production_total"] = load_optimized_production(layout=active_layout)
    return outputs


def export_trade_stage_inputs(
    output_dir: Path | None = None,
    layout: RepoLayout | None = None,
) -> dict[str, Path]:
    active_layout = layout or default_layout()
    target_dir = output_dir or active_layout.outputs_dir / "generated" / "trade_stage"
    outputs = build_trade_stage_inputs(layout=active_layout)
    written: dict[str, Path] = {}
    for name, df in outputs.items():
        written[name] = write_csv(df, target_dir / f"{name}.csv")
    return written
