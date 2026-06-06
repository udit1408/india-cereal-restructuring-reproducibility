#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
BOUNDARY_FILE = ROOT / "_audit" / "external" / "indian-district-boundaries" / "shapefile" / "india-districts-2019-734.shp"
OUTPUT_DIR = ROOT / "figures" / "manuscript_final"
OUTPUT_PDF = OUTPUT_DIR / "si_s6_state_boundaries.pdf"
OUTPUT_PNG = OUTPUT_DIR / "si_s6_state_boundaries.png"

if str(AUDIT_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIT_ROOT))

from repro.figure1_pipeline import normalize_name  # noqa: E402


def load_boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    districts = gpd.read_file(BOUNDARY_FILE)
    if districts.crs is None:
        districts = districts.set_crs("EPSG:4326")
    try:
        districts["geometry"] = districts.geometry.make_valid()
    except AttributeError:
        districts["geometry"] = districts.geometry.buffer(0)

    districts["state_key"] = districts["st_nm"].map(normalize_name)
    districts = districts[districts["state_key"].ne("")].copy()

    states = districts.dissolve(by="state_key", as_index=False, aggfunc={"st_nm": "first"})
    states = states.sort_values("st_nm").reset_index(drop=True)
    return districts, states


def plot_state_boundaries(districts: gpd.GeoDataFrame, states: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 9.0))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    states.plot(ax=ax, color="#fbfaf7", edgecolor="none")
    districts.boundary.plot(ax=ax, color="#d2d7dc", linewidth=0.10, alpha=0.50)
    states.boundary.plot(ax=ax, color="#414b55", linewidth=0.60)

    xmin, ymin, xmax, ymax = states.total_bounds
    dx = xmax - xmin
    dy = ymax - ymin
    ax.set_xlim(xmin - 0.04 * dx, xmax + 0.04 * dx)
    ax.set_ylim(ymin - 0.03 * dy, ymax + 0.03 * dy)
    ax.set_aspect("equal")
    ax.margins(0)
    ax.axis("off")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PDF, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main() -> int:
    districts, states = load_boundaries()
    plot_state_boundaries(districts, states)
    print(f"Wrote {OUTPUT_PDF}")
    print(f"Wrote {OUTPUT_PNG}")
    print(f"Boundary source: {BOUNDARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
