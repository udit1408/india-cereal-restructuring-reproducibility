#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
FIG_DIR = ROOT / "figures" / "manuscript_final"
DATA_DIR = ROOT / "data" / "generated"


def _ensure_geopandas_stub() -> None:
    if "geopandas" not in sys.modules:
        sys.modules["geopandas"] = types.ModuleType("geopandas")


def main() -> None:
    _ensure_geopandas_stub()
    sys.path.insert(0, str(AUDIT_ROOT))

    from repro.figure2a_clean_rebuild import export_figure2a_clean_rebuild

    output_dir = AUDIT_ROOT / "outputs" / "generated" / "figure2a_no_historical_cap_core"
    written = export_figure2a_clean_rebuild(
        output_dir=output_dir,
        solver_name="highs",
        income_mode="profit",
        objective_mode="normalized",
        use_historical_caps=False,
    )

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    copy_map = {
        "figure2a_no_historical_cap_core_pct_2017_baseline.pdf": output_dir / "figure2a_clean_rebuild_pct_2017_baseline.pdf",
        "figure2a_no_historical_cap_core_pct_2017_baseline.png": output_dir / "figure2a_clean_rebuild_pct_2017_baseline.png",
        "figure2a_no_historical_cap_core.pdf": output_dir / "figure2a_clean_rebuild.pdf",
        "figure2a_no_historical_cap_core.png": output_dir / "figure2a_clean_rebuild.png",
    }
    for name, source in copy_map.items():
        shutil.copy2(source, FIG_DIR / name)

    shutil.copy2(output_dir / "combined_by_alpha.csv", DATA_DIR / "figure2a_no_historical_cap_core_combined_by_alpha.csv")
    shutil.copy2(
        output_dir / "figure2a_clean_rebuild_summary.md",
        DATA_DIR / "figure2a_no_historical_cap_core_summary.md",
    )

    for key, value in written.items():
        print(f"{key}: {value}")
    print(f"copied_pct_pdf: {FIG_DIR / 'figure2a_no_historical_cap_core_pct_2017_baseline.pdf'}")
    print(f"copied_pct_png: {FIG_DIR / 'figure2a_no_historical_cap_core_pct_2017_baseline.png'}")


if __name__ == "__main__":
    main()
