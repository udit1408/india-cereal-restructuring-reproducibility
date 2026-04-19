from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from .config import RepoLayout, default_layout
from .io import ensure_directory, read_generated_csv, read_repo_csv, strip_unnamed_columns, write_csv

matplotlib.use("Agg")


BOUNDARY_RELATIVE = Path("external/indian-district-boundaries/shapefile/india-districts-2019-734.shp")

CROP_ORDER = ["maize", "bajra", "jowar", "ragi", "rice", "wheat"]
CROP_COLORS = {
    "maize": "#3d0a4d",
    "bajra": "#4c4e91",
    "jowar": "#1e6f84",
    "ragi": "#44a3a5",
    "rice": "#7cd34d",
    "wheat": "#ffe31a",
}
HISTORICAL_STATE_SPLITS = (
    ("andhra pradesh", "telangana"),
    ("madhya pradesh", "chhattisgarh"),
    ("bihar", "jharkhand"),
    ("uttar pradesh", "uttarakhand"),
)
STATE_ABBREVIATIONS = [
    ("andaman and nicobar", "AN"),
    ("andhra pradesh", "AP"),
    ("arunachal pradesh", "AR"),
    ("assam", "AS"),
    ("bihar", "BR"),
    ("chhattisgarh", "CH"),
    ("chandigarh", "CN"),
    ("daman and diu", "DD"),
    ("dadra and nagar haveli", "DN"),
    ("gujarat", "GJ"),
    ("himachal pradesh", "HP"),
    ("haryana", "HR"),
    ("jharkhand", "JH"),
    ("jammu and kashmir", "JK"),
    ("karnataka", "KA"),
    ("kerala", "KL"),
    ("maharashtra", "MH"),
    ("meghalaya", "ML"),
    ("manipur", "MN"),
    ("madhya pradesh", "MP"),
    ("mizoram", "MZ"),
    ("nagaland", "NL"),
    ("odisha", "OD"),
    ("puducherry", "PD"),
    ("punjab", "PN"),
    ("rajasthan", "RJ"),
    ("sikkim", "SK"),
    ("telangana", "TE"),
    ("tamil nadu", "TN"),
    ("tripura", "TR"),
    ("uttar pradesh", "UP"),
    ("uttarakhand", "UR"),
    ("west bengal", "WB"),
]

DATA_TO_GEO = {
    ("andaman and nicobar", "south andamans"): ("andaman and nicobar", "south andaman"),
    ("andhra pradesh", "kadapa"): ("andhra pradesh", "y s r"),
    ("andhra pradesh", "nellore"): ("andhra pradesh", "s p s nellore"),
    ("andhra pradesh", "spsr nellore"): ("andhra pradesh", "s p s nellore"),
    ("andhra pradesh", "visakhapatanam"): ("andhra pradesh", "visakhapatnam"),
    ("arunachal pradesh", "dibang valley"): ("arunachal pradesh", "upper dibang valley"),
    ("assam", "kamrup metro"): ("assam", "kamrup metropolitan"),
    ("assam", "marigaon"): ("assam", "morigaon"),
    ("bihar", "kaimur"): ("bihar", "kaimur bhabhua"),
    ("bihar", "kaimur bhabua"): ("bihar", "kaimur bhabhua"),
    ("bihar", "pashchim champaran"): ("bihar", "west champaran"),
    ("bihar", "purbi champaran"): ("bihar", "east champaran"),
    ("chhattisgarh", "bemetara"): ("chhattisgarh", "bametara"),
    ("chhattisgarh", "dantewada"): ("chhattisgarh", "dakshin bastar dantewada"),
    ("chhattisgarh", "gariyaband"): ("chhattisgarh", "gariaband"),
    ("chhattisgarh", "janjgirchampa"): ("chhattisgarh", "janjgir champa"),
    ("chhattisgarh", "kabirdham"): ("chhattisgarh", "kabeerdham"),
    ("chhattisgarh", "kanker"): ("chhattisgarh", "uttar bastar kanker"),
    ("chhattisgarh", "korea"): ("chhattisgarh", "koriya"),
    ("gujarat", "arvalli"): ("gujarat", "aravalli"),
    ("gujarat", "chhotaudepur"): ("gujarat", "chota udaipur"),
    ("gujarat", "dang"): ("gujarat", "dangs"),
    ("haryana", "gurgaon"): ("haryana", "gurugram"),
    ("haryana", "mewat"): ("haryana", "nuh"),
    ("jammu and kashmir", "bandipora"): ("jammu and kashmir", "bandipore"),
    ("jammu and kashmir", "baramulla"): ("jammu and kashmir", "baramula"),
    ("jammu and kashmir", "kargil"): ("ladakh", "kargil"),
    ("jammu and kashmir", "leh ladakh"): ("ladakh", "leh"),
    ("jammu and kashmir", "poonch"): ("jammu and kashmir", "punch"),
    ("jammu and kashmir", "rajauri"): ("jammu and kashmir", "rajouri"),
    ("jammu and kashmir", "shopian"): ("jammu and kashmir", "shupiyan"),
    ("jharkhand", "east singhbum"): ("jharkhand", "purbi singhbhum"),
    ("jharkhand", "koderma"): ("jharkhand", "kodarma"),
    ("jharkhand", "sahebganj"): ("jharkhand", "sahibganj"),
    ("jharkhand", "saraikelakharsawan"): ("jharkhand", "saraikela kharsawan"),
    ("jharkhand", "west singhbhum"): ("jharkhand", "pashchimi singhbhum"),
    ("karnataka", "bagalkot"): ("karnataka", "bagalkote"),
    ("karnataka", "bangalore rural"): ("karnataka", "bengaluru rural"),
    ("karnataka", "bengaluru urban"): ("karnataka", "bengaluru"),
    ("karnataka", "chamrajnagar"): ("karnataka", "chamarajanagara"),
    ("karnataka", "chikballapura"): ("karnataka", "chikkaballapura"),
    ("karnataka", "chikmagalur"): ("karnataka", "chikkamagaluru"),
    ("karnataka", "davangere"): ("karnataka", "davanagere"),
    ("karnataka", "tumkur"): ("karnataka", "tumakuru"),
    ("karnataka", "yadagiri"): ("karnataka", "yadgir"),
    ("madhya pradesh", "khandwa"): ("madhya pradesh", "east nimar"),
    ("madhya pradesh", "khargone"): ("madhya pradesh", "west nimar"),
    ("madhya pradesh", "narsinghpur"): ("madhya pradesh", "narsimhapur"),
    ("maharashtra", "ahmednagar"): ("maharashtra", "ahmadnagar"),
    ("maharashtra", "beed"): ("maharashtra", "bid"),
    ("maharashtra", "buldhana"): ("maharashtra", "buldana"),
    ("maharashtra", "gondia"): ("maharashtra", "gondiya"),
    ("maharashtra", "raigad"): ("maharashtra", "raigarh"),
    ("meghalaya", "ri bhoi"): ("meghalaya", "ribhoi"),
    ("mizoram", "aizawl"): ("mizoram", "aizawal"),
    ("odisha", "boudh"): ("odisha", "baudh"),
    ("odisha", "deogarh"): ("odisha", "debagarh"),
    ("odisha", "nabarangpur"): ("odisha", "nabarangapur"),
    ("odisha", "sonepur"): ("odisha", "subarnapur"),
    ("puducherry", "pondicherry"): ("puducherry", "puducherry"),
    ("punjab", "muktsar"): ("punjab", "sri muktsar sahib"),
    ("rajasthan", "chittorgarh"): ("rajasthan", "chittaurgarh"),
    ("rajasthan", "dholpur"): ("rajasthan", "dhaulpur"),
    ("rajasthan", "jalore"): ("rajasthan", "jalor"),
    ("rajasthan", "jhunjhunun"): ("rajasthan", "jhunjhunu"),
    ("tamil nadu", "kanchipuram"): ("tamil nadu", "kancheepuram"),
    ("tamil nadu", "nagappattinam"): ("tamil nadu", "nagapattinam"),
    ("tamil nadu", "tuticorin"): ("tamil nadu", "thoothukkudi"),
    ("tamil nadu", "villupuram"): ("tamil nadu", "viluppuram"),
    ("tamil nadu", "virudunagar"): ("tamil nadu", "virudhunagar"),
    ("telangana", "bhadradri"): ("telangana", "bhadradri kothagudem"),
    ("telangana", "hanumakonda"): ("telangana", "warangal urban"),
    ("telangana", "jogulamba"): ("telangana", "jogulamba gadwal"),
    ("telangana", "komaram bheem asifabad"): ("telangana", "kumuram bheem asifabad"),
    ("telangana", "mahbubnagar"): ("telangana", "mahabubnagar"),
    ("telangana", "rajanna"): ("telangana", "rajanna sircilla"),
    ("telangana", "rangareddi"): ("telangana", "ranga reddy"),
    ("telangana", "warangal"): ("telangana", "warangal rural"),
    ("telangana", "yadadri"): ("telangana", "yadadri bhuvanagiri"),
    ("tripura", "sepahijala"): ("tripura", "sipahijala"),
    ("tripura", "unakoti"): ("tripura", "unokoti"),
    ("uttar pradesh", "allahabad"): ("uttar pradesh", "prayagraj"),
    ("uttar pradesh", "barabanki"): ("uttar pradesh", "bara banki"),
    ("uttar pradesh", "kushi nagar"): ("uttar pradesh", "kushinagar"),
    ("uttar pradesh", "lakhimpur kheri"): ("uttar pradesh", "kheri"),
    ("uttar pradesh", "maharajganj"): ("uttar pradesh", "mahrajganj"),
    ("uttar pradesh", "sant kabeer nagar"): ("uttar pradesh", "sant kabir nagar"),
    ("uttar pradesh", "sant ravi das nagar"): ("uttar pradesh", "bhadohi"),
    ("uttar pradesh", "sant ravidas nagar"): ("uttar pradesh", "bhadohi"),
    ("uttar pradesh", "shahajahanpur"): ("uttar pradesh", "shahjahanpur"),
    ("uttar pradesh", "shravasti"): ("uttar pradesh", "shrawasti"),
    ("uttar pradesh", "siddharth nagar"): ("uttar pradesh", "siddharthnagar"),
    ("uttarakhand", "hardwar"): ("uttarakhand", "haridwar"),
    ("uttarakhand", "rudra prayag"): ("uttarakhand", "rudraprayag"),
    ("uttarakhand", "udam singh nagar"): ("uttarakhand", "udham singh nagar"),
    ("uttarakhand", "uttar kashi"): ("uttarakhand", "uttarkashi"),
    ("west bengal", "coochbehar"): ("west bengal", "cooch behar"),
    ("west bengal", "dinajpur dakshin"): ("west bengal", "dakshin dinajpur"),
    ("west bengal", "dinajpur uttar"): ("west bengal", "uttar dinajpur"),
    ("west bengal", "paraganas north"): ("west bengal", "north 24 parganas"),
    ("west bengal", "paraganas south"): ("west bengal", "south 24 parganas"),
    ("west bengal", "puruliya"): ("west bengal", "purulia"),
}
UNRESOLVED_KEYS = {("west bengal", "barddhaman")}

PANEL_SCALES = {
    "nitrogen_surplus_ggn": ("Nitrogen Surplus\nGgN", 1e6, ["#fff0d3", "#fcd9a6", "#f9b970", "#f68b45", "#ef6030", "#df311c", "#b80d0a"]),
    "calorie_bkcal": ("Calorie\nBKcal", 1e9, ["#eef7fb", "#d8eee9", "#c0e2d6", "#92cfb4", "#5fba80", "#2f9953", "#0a6e29"]),
    "water_bcm": ("Total Water Demand\nBCM", 1e9, ["#fffbd5", "#edf3c1", "#d1e7b9", "#9cd4d1", "#5db8d7", "#2584d6", "#093e9f"]),
}


def normalize_name(value: object) -> str:
    if pd.isna(value):
        return ""
    normalized = str(value).lower().strip().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\bthe\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def resolve_boundary_path(layout: RepoLayout, boundary_file: Path | None = None) -> Path:
    if boundary_file is not None:
        return boundary_file

    candidate = layout.root.parent / BOUNDARY_RELATIVE
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Could not find district boundary file at {candidate}. "
        "Clone the boundary repo or pass --boundary-file."
    )


def load_baseline_panel_abc(layout: RepoLayout) -> tuple[pd.DataFrame, pd.DataFrame]:
    kharif = strip_unnamed_columns(read_generated_csv("nutrient_based_opt_cop_kharif.csv", layout=layout))
    rabi = strip_unnamed_columns(read_generated_csv("nitrogen_surplus_rbased_opt_cop_rabi.csv", layout=layout))
    combined = pd.concat([kharif, rabi], ignore_index=True)
    combined = combined[combined["Original Area (Hectare)"].fillna(0) > 0].copy()

    district_metrics = (
        combined.groupby(["State", "District"], as_index=False)[
            ["Original Total N surplus", "Original Calorie", "Original water"]
        ]
        .sum()
        .rename(
            columns={
                "Original Total N surplus": "nitrogen_surplus_kg",
                "Original Calorie": "calorie_kcal",
                "Original water": "water_m3",
            }
        )
    )
    district_metrics["state_key"] = district_metrics["State"].map(normalize_name)
    district_metrics["district_key"] = district_metrics["District"].map(normalize_name)
    mapped = district_metrics.apply(
        lambda row: pd.Series(
            DATA_TO_GEO.get((row["state_key"], row["district_key"]), (row["state_key"], row["district_key"]))
        ),
        axis=1,
    )
    mapped.columns = ["map_state", "map_district"]
    district_metrics = pd.concat([district_metrics, mapped], axis=1)

    panel_metrics = (
        district_metrics.groupby(["map_state", "map_district"], as_index=False)[
            ["nitrogen_surplus_kg", "calorie_kcal", "water_m3"]
        ]
        .sum()
    )
    panel_metrics["nitrogen_surplus_ggn"] = panel_metrics["nitrogen_surplus_kg"] / PANEL_SCALES["nitrogen_surplus_ggn"][1]
    panel_metrics["calorie_bkcal"] = panel_metrics["calorie_kcal"] / PANEL_SCALES["calorie_bkcal"][1]
    panel_metrics["water_bcm"] = panel_metrics["water_m3"] / PANEL_SCALES["water_bcm"][1]
    return panel_metrics, district_metrics


def load_panel_d_state_area(layout: RepoLayout) -> pd.DataFrame:
    kharif = strip_unnamed_columns(read_repo_csv("kharif_df.csv", layout=layout))
    rabi = strip_unnamed_columns(read_repo_csv("rabi_df.csv", layout=layout))
    combined = pd.concat([kharif, rabi], ignore_index=True)
    combined["state"] = combined["state"].astype(str).str.lower().str.strip()
    combined["district"] = combined["district"].astype(str).str.lower().str.strip()
    combined["crop"] = combined["crop"].astype(str).str.lower().str.strip()
    combined = combined[combined["crop"].isin(CROP_ORDER)].copy()
    combined["Area (Hectare)"] = pd.to_numeric(combined["Area (Hectare)"], errors="coerce").fillna(0)
    combined["state_panel_d"] = combined["state"]

    # The raw historical repo keeps pre-bifurcation districts under their former parent state.
    # For the published Figure 1d state panel, aggregate those districts to their current states.
    for parent_state, child_state in HISTORICAL_STATE_SPLITS:
        parent_districts = set(combined.loc[combined["state"] == parent_state, "district"])
        child_districts = set(combined.loc[combined["state"] == child_state, "district"])
        moved_districts = parent_districts & child_districts
        combined.loc[
            (combined["state"] == parent_state) & (combined["district"].isin(moved_districts)),
            "state_panel_d",
        ] = child_state

    state_crop = combined.groupby(["state_panel_d", "crop"], as_index=False)["Area (Hectare)"].sum()
    state_crop = state_crop.rename(columns={"state_panel_d": "state"})
    state_crop["area_plot_units"] = state_crop["Area (Hectare)"] / 1e6

    order = pd.DataFrame(STATE_ABBREVIATIONS, columns=["state", "state_abbrev"])
    state_crop = order.merge(state_crop, on="state", how="left")
    state_crop["crop"] = state_crop["crop"].fillna("")
    state_crop["Area (Hectare)"] = state_crop["Area (Hectare)"].fillna(0)
    state_crop["area_plot_units"] = state_crop["area_plot_units"].fillna(0)
    return state_crop


def load_geometries(boundary_file: Path) -> gpd.GeoDataFrame:
    geometry = gpd.read_file(boundary_file)
    geometry["state_key"] = geometry["st_nm"].map(normalize_name)
    geometry["district_key"] = geometry["district"].map(normalize_name)
    return geometry


def build_map_frame(layout: RepoLayout, boundary_file: Path) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    geometry = load_geometries(boundary_file)
    metrics, detail = load_baseline_panel_abc(layout)
    merged = geometry.merge(
        metrics,
        left_on=["state_key", "district_key"],
        right_on=["map_state", "map_district"],
        how="left",
    )

    geo_keys = set(zip(geometry["state_key"], geometry["district_key"]))
    coverage = detail[["State", "District", "state_key", "district_key", "map_state", "map_district"]].drop_duplicates()
    coverage["matched"] = coverage.apply(
        lambda row: (row["map_state"], row["map_district"]) in geo_keys and (row["state_key"], row["district_key"]) not in UNRESOLVED_KEYS,
        axis=1,
    )
    return merged, coverage


def _quantile_bins(series: pd.Series, classes: int = 7) -> np.ndarray:
    clean = series.dropna().clip(lower=0)
    if clean.empty:
        return np.array([0.0, 1.0])

    raw = np.quantile(clean, np.linspace(0, 1, classes + 1))
    bins = np.unique(np.round(raw, 3))
    if bins[0] > 0:
        bins[0] = 0.0
    if len(bins) < 2:
        bins = np.array([0.0, float(clean.max()) or 1.0])
    return bins


def _draw_north_arrow(ax: plt.Axes) -> None:
    ax.annotate(
        "N",
        xy=(0.78, 0.84),
        xytext=(0.78, 0.72),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="bottom",
        color="white",
        fontsize=10,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "facecolor": "white", "edgecolor": "white", "lw": 0.8},
    )


def _draw_legend(ax: plt.Axes, title: str, bins: np.ndarray, colors: list[str]) -> None:
    legend_ax = ax.inset_axes([0.54, 0.06, 0.24, 0.29])
    legend_ax.set_facecolor("#2e3136")
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)
    legend_ax.axis("off")
    legend_ax.text(0.0, 0.98, title, va="top", ha="left", color="white", fontsize=7, fontweight="bold")

    n_bins = len(bins) - 1
    if n_bins <= 0:
        return

    top = 0.82
    step = 0.72 / max(n_bins, 1)
    for idx in range(n_bins):
        y = top - (idx + 1) * step
        legend_ax.add_patch(
            Rectangle((0.0, y), 0.18, step * 0.68, facecolor=colors[idx], edgecolor="#dadada", linewidth=0.25)
        )
        label = f"{bins[idx]:.2f} - {bins[idx + 1]:.2f}"
        legend_ax.text(0.24, y + step * 0.34, label, va="center", ha="left", color="white", fontsize=6)


def plot_metric_map(ax: plt.Axes, map_frame: gpd.GeoDataFrame, value_column: str, panel_label: str) -> None:
    title, _, colors = PANEL_SCALES[value_column]
    ax.set_facecolor("#2e3136")

    missing = map_frame[map_frame[value_column].isna()]
    if not missing.empty:
        missing.plot(ax=ax, color="#f7ecd7", edgecolor="#8f867a", linewidth=0.28)

    data = map_frame[map_frame[value_column].notna()].copy()
    if not data.empty:
        bins = _quantile_bins(data[value_column])
        interval_count = len(bins) - 1
        palette = colors[:interval_count]
        if interval_count > len(colors):
            palette = list(plt.cm.get_cmap("viridis", interval_count).colors)

        categories = pd.cut(
            data[value_column].clip(lower=0),
            bins=bins,
            include_lowest=True,
            labels=False,
            duplicates="drop",
        )
        data["bin_id"] = categories.fillna(0).astype(int)
        data["fill"] = data["bin_id"].map(dict(enumerate(palette)))
        data.plot(ax=ax, color=data["fill"], edgecolor="#8f867a", linewidth=0.28)
        _draw_legend(ax, title, bins, palette)

    map_frame.boundary.plot(ax=ax, color="#8f867a", linewidth=0.22)
    xmin, ymin, xmax, ymax = map_frame.total_bounds
    dx = xmax - xmin
    dy = ymax - ymin
    ax.set_xlim(xmin - 0.05 * dx, xmax + 0.03 * dx)
    ax.set_ylim(ymin - 0.07 * dy, ymax + 0.03 * dy)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(0.02, 0.95, panel_label, transform=ax.transAxes, ha="left", va="top", color="white", fontsize=18)
    _draw_north_arrow(ax)


def plot_panel_d(ax: plt.Axes, state_crop: pd.DataFrame) -> None:
    ax.set_facecolor("#f3f3f3")
    state_order = [abbrev for _, abbrev in STATE_ABBREVIATIONS]
    state_lookup = {state: abbrev for state, abbrev in STATE_ABBREVIATIONS}
    state_crop = state_crop.copy()
    state_crop["state_abbrev"] = state_crop["state"].map(state_lookup).fillna(state_crop["state_abbrev"])

    pivot = (
        state_crop[state_crop["crop"].isin(CROP_ORDER)]
        .pivot_table(index="state_abbrev", columns="crop", values="area_plot_units", aggfunc="sum", fill_value=0)
        .reindex(state_order, fill_value=0)
    )

    x = np.arange(len(pivot.index))
    bottom = np.zeros(len(pivot.index))
    for crop in CROP_ORDER:
        values = pivot[crop].to_numpy() if crop in pivot.columns else np.zeros(len(pivot.index))
        ax.bar(
            x,
            values,
            bottom=bottom,
            width=0.52,
            color=CROP_COLORS[crop],
            edgecolor="none",
            label=crop,
        )
        bottom += values

    ax.set_title("State-wise Distribution of Cropland Area (Mha)", fontsize=16, fontweight="bold", pad=2)
    ax.set_ylabel("Cropland Area (Mha)", fontsize=10, fontweight="bold")
    ax.set_xlabel("State", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index.tolist(), rotation=90, fontsize=8, fontweight="bold")
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(axis="y", linestyle="--", linewidth=0.45, color="#bfbfbf")
    ax.grid(axis="x", linestyle=":", linewidth=0.35, color="#d0d0d0")
    ax.legend(
        handles=[Patch(facecolor=CROP_COLORS[crop], edgecolor="none", label=crop) for crop in CROP_ORDER],
        title="Crop",
        loc="upper left",
        frameon=False,
        fontsize=8,
        title_fontsize=8,
    )
    ax.text(0.01, 1.01, "d", transform=ax.transAxes, ha="left", va="bottom", fontsize=18, color="black")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def build_figure(map_frame: gpd.GeoDataFrame, state_crop: pd.DataFrame) -> plt.Figure:
    figure = plt.figure(figsize=(14, 9), constrained_layout=False)
    grid = figure.add_gridspec(2, 3, height_ratios=[1.0, 0.76], hspace=0.10, wspace=0.03)
    ax_a = figure.add_subplot(grid[0, 0])
    ax_b = figure.add_subplot(grid[0, 1])
    ax_c = figure.add_subplot(grid[0, 2])
    ax_d = figure.add_subplot(grid[1, :])

    plot_metric_map(ax_a, map_frame, "nitrogen_surplus_ggn", "a")
    plot_metric_map(ax_b, map_frame, "calorie_bkcal", "b")
    plot_metric_map(ax_c, map_frame, "water_bcm", "c")
    plot_panel_d(ax_d, state_crop)
    return figure


def write_summary(output_dir: Path, boundary_file: Path, coverage: pd.DataFrame) -> Path:
    matched = int(coverage["matched"].sum())
    total = int(len(coverage))
    unresolved = coverage[~coverage["matched"]][["State", "District"]].drop_duplicates()
    unresolved_lines = "\n".join(f"- {row.State} / {row.District}" for row in unresolved.itertuples())
    summary = (
        "# Figure 1 reproduction audit\n\n"
        f"- Boundary source: `{boundary_file}`\n"
        f"- District-key coverage for panels a-c: {matched}/{total}\n"
        "- Panels a-c use 2017 baseline metrics from the generated optimization exports, filtered to observed baseline area.\n"
        "- Panel d uses the all-years sum of raw crop areas from `kharif_df.csv` and `rabi_df.csv`, scaled by `1e6`, so the plotted values are in million hectares.\n"
        "- Panel d reassigns districts affected by historical state bifurcations to their current states before aggregation (Andhra Pradesh/Telangana, Madhya Pradesh/Chhattisgarh, Bihar/Jharkhand, Uttar Pradesh/Uttarakhand).\n"
    )
    if unresolved_lines:
        summary += "\n## Unresolved district names\n\n" + unresolved_lines + "\n"

    path = output_dir / "figure1_reproduction_summary.md"
    path.write_text(summary)
    return path


def export_figure1(
    output_dir: Path | None = None,
    boundary_file: Path | None = None,
    layout: RepoLayout | None = None,
) -> dict[str, Path]:
    active_layout = layout or default_layout()
    target_dir = output_dir or active_layout.outputs_dir / "generated" / "figure1"
    ensure_directory(target_dir)

    resolved_boundary = resolve_boundary_path(active_layout, boundary_file)
    map_frame, coverage = build_map_frame(active_layout, resolved_boundary)
    state_crop = load_panel_d_state_area(active_layout)

    panel_abc_table = map_frame.drop(columns="geometry").copy()
    figure = build_figure(map_frame, state_crop)

    png_path = target_dir / "figure1_reproduced.png"
    pdf_path = target_dir / "figure1_reproduced.pdf"
    figure.savefig(png_path, dpi=300, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)

    written = {
        "figure1_png": png_path,
        "figure1_pdf": pdf_path,
        "panel_abc_joined": write_csv(panel_abc_table, target_dir / "figure1_panel_abc_joined.csv"),
        "panel_d_state_area": write_csv(state_crop, target_dir / "figure1_panel_d_state_area.csv"),
        "district_coverage": write_csv(coverage, target_dir / "figure1_district_coverage.csv"),
        "summary": write_summary(target_dir, resolved_boundary, coverage),
    }
    return written
