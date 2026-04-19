from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from .config import RepoLayout, default_layout
from .io import ensure_directory, read_generated_csv, strip_unnamed_columns, write_csv
from .legacy_notebook_runner import NotebookRunConfig, execute_notebook, extract_archive_if_needed


matplotlib.use("Agg")


SEASON_NOTEBOOKS = {
    "kharif_perito_cop.ipynb": "kharif_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv",
    "rabi_perito_cop.ipynb": "rabi_perito_saving_rice_culture_new_nested_result_alpha_value_no_gamma.csv",
}
COMBINED_NOTEBOOK = "rabi_kharif_plot_perito_combined.ipynb"

OUTPUT_COLUMNS = ["Alpha", "Objective Nitrogen", "Objective Water"]
CACHED_ROW_RE = re.compile(
    r"^\s*(?P<idx>0|100)\s+(?P<alpha>\d+\.\d+)\s+(?P<nitrogen>[0-9.eE+-]+)\s+(?P<water>[0-9.eE+-]+)\s*$",
    re.MULTILINE,
)


def _load_or_generate_season_frontier(
    notebook_name: str,
    output_name: str,
    layout: RepoLayout,
) -> tuple[pd.DataFrame, str]:
    try:
        frame = strip_unnamed_columns(read_generated_csv(output_name, layout=layout))
        return frame[OUTPUT_COLUMNS].copy(), "loaded existing generated CSV"
    except FileNotFoundError:
        pass

    data_dir = extract_archive_if_needed(layout.root).resolve()
    notebook = (layout.root / notebook_name).resolve()
    namespace = execute_notebook(
        NotebookRunConfig(
            notebook=notebook,
            data_dir=data_dir,
            generated_dir=layout.generated_dir.resolve(),
        )
    )
    frame = namespace.get("df_results")
    if not isinstance(frame, pd.DataFrame):
        raise RuntimeError(f"{notebook_name} did not expose a df_results DataFrame.")

    frame = strip_unnamed_columns(frame)
    missing = [column for column in OUTPUT_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"{notebook_name} is missing expected columns: {missing}")

    frame = frame[OUTPUT_COLUMNS].copy()
    write_csv(frame, layout.generated_dir / output_name)
    return frame, "executed notebook and exported df_results"


def build_figure2a_data(layout: RepoLayout | None = None) -> tuple[pd.DataFrame, dict[str, str]]:
    active_layout = layout or default_layout()
    season_frames: list[pd.DataFrame] = []
    provenance: dict[str, str] = {}

    for notebook_name, output_name in SEASON_NOTEBOOKS.items():
        frame, source = _load_or_generate_season_frontier(notebook_name, output_name, active_layout)
        season_frames.append(frame)
        provenance[output_name] = source

    combined = pd.concat(season_frames, ignore_index=True)
    combined = (
        combined.groupby("Alpha", as_index=False)[["Objective Nitrogen", "Objective Water"]]
        .mean()
        .sort_values("Alpha")
        .reset_index(drop=True)
    )
    combined["nitrogen_mt"] = combined["Objective Nitrogen"] / 1e9
    combined["water_bcm"] = combined["Objective Water"] / 1e9
    return combined, provenance


def _plot_figure2a(frame: pd.DataFrame, target_dir: Path) -> dict[str, Path]:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    cmap = plt.get_cmap("viridis")

    for row in frame.itertuples(index=False):
        alpha_value = float(row.Alpha)
        if alpha_value == 0.0:
            ax.scatter(
                row.nitrogen_mt,
                row.water_bcm,
                color="#5b2a86",
                edgecolors="black",
                linewidths=0.8,
                marker="*",
                s=170,
                zorder=4,
                label="Water optimization",
            )
        elif alpha_value == 1.0:
            ax.scatter(
                row.nitrogen_mt,
                row.water_bcm,
                color="#d89216",
                edgecolors="black",
                linewidths=0.8,
                marker="*",
                s=170,
                zorder=4,
                label="Nitrogen surplus optimization",
            )
        else:
            ax.scatter(
                row.nitrogen_mt,
                row.water_bcm,
                color=cmap(alpha_value),
                edgecolors="white",
                linewidths=0.25,
                s=34,
                zorder=3,
            )

    ax.set_xlabel("Optimal Nitrogen surplus generation (Mt)", fontweight="bold")
    ax.set_ylabel("Optimal Water demand (BCM)", fontweight="bold")
    ax.set_title("Pareto Front: Nitrogen Surplus vs. Consumptive Water Demand", fontweight="bold")
    ax.grid(True, linestyle="-", linewidth=0.5, color="#d7d7d7", alpha=0.9)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#c8c8c8")
    fig.tight_layout()

    png_path = target_dir / "figure2a_reproduced.png"
    pdf_path = target_dir / "figure2a_reproduced.pdf"
    fig.savefig(png_path, dpi=600)
    fig.savefig(pdf_path)
    plt.close(fig)
    return {"figure2a_png": png_path, "figure2a_pdf": pdf_path}


def _cached_combined_endpoints(layout: RepoLayout) -> dict[str, dict[str, float]]:
    notebook = layout.root / COMBINED_NOTEBOOK
    if not notebook.exists():
        return {}

    raw = json.loads(notebook.read_text())
    for cell in raw.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs", []):
            data = output.get("data", {}) or {}
            plain = data.get("text/plain")
            if not plain:
                continue
            if isinstance(plain, list):
                plain = "".join(plain)
            if "Objective Nitrogen" not in plain or "Objective Water" not in plain:
                continue

            rows: dict[str, dict[str, float]] = {}
            for match in CACHED_ROW_RE.finditer(plain):
                label = "first" if match.group("idx") == "0" else "last"
                rows[label] = {
                    "alpha": float(match.group("alpha")),
                    "objective_nitrogen": float(match.group("nitrogen")),
                    "objective_water": float(match.group("water")),
                }
            return rows
    return {}


def export_figure2a(
    output_dir: Path | None = None,
    layout: RepoLayout | None = None,
) -> dict[str, Path]:
    active_layout = layout or default_layout()
    target_dir = ensure_directory(output_dir or active_layout.outputs_dir / "generated" / "figure2a")

    combined, provenance = build_figure2a_data(layout=active_layout)
    written = {
        "combined_pareto_csv": write_csv(combined, target_dir / "figure2a_combined_frontier.csv"),
    }
    written.update(_plot_figure2a(combined, target_dir))

    generated_first = combined.iloc[0]
    generated_last = combined.iloc[-1]
    cached = _cached_combined_endpoints(active_layout)

    summary_lines = [
        "# Figure 2(a) reproduction summary",
        "",
        "The combined frontier follows the legacy notebook logic in `rabi_kharif_plot_perito_combined.ipynb`,",
        "which concatenates the kharif and rabi season Pareto tables and averages `Objective Nitrogen` and",
        "`Objective Water` by alpha before converting them to Mt and BCM, respectively.",
        "",
        "Season-level provenance:",
        *[f"- `{name}`: {status}" for name, status in sorted(provenance.items())],
        "",
        "Generated frontier endpoints:",
        f"- alpha={generated_first['Alpha']:.2f}: nitrogen={generated_first['Objective Nitrogen']:.6e}, water={generated_first['Objective Water']:.6e}",
        f"- alpha={generated_last['Alpha']:.2f}: nitrogen={generated_last['Objective Nitrogen']:.6e}, water={generated_last['Objective Water']:.6e}",
    ]
    if cached:
        summary_lines.extend(
            [
                "",
                "Cached notebook output endpoints:",
                f"- alpha={cached['first']['alpha']:.2f}: nitrogen={cached['first']['objective_nitrogen']:.6e}, water={cached['first']['objective_water']:.6e}",
                f"- alpha={cached['last']['alpha']:.2f}: nitrogen={cached['last']['objective_nitrogen']:.6e}, water={cached['last']['objective_water']:.6e}",
            ]
        )

    summary = target_dir / "figure2a_reproduction_summary.md"
    summary.write_text("\n".join(summary_lines) + "\n")
    written["summary_md"] = summary
    return written
