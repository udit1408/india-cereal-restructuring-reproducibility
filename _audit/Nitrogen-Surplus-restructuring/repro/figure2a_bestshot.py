from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .config import RepoLayout, default_layout
from .io import ensure_directory, write_csv
from .legacy_notebook_runner import NotebookRunConfig, _rewrite_source, extract_archive_if_needed


SEASON_NOTEBOOKS = {
    "kharif": "kharif_perito_cop.ipynb",
    "rabi": "rabi_perito_cop.ipynb",
}

DEFAULT_ALPHAS = [round(i / 100, 2) for i in range(0, 101)]
SUMMARY_COLUMNS = [
    "Alpha",
    "rows",
    "objective_nitrogen",
    "objective_water",
    "solve_status",
    "solve_status_code",
    "objective_nitrogen_nunique",
    "objective_water_nunique",
    "solve_status_nunique",
    "is_optimal",
    "is_consistent",
    "is_valid",
]

ALPHA_ASSIGN_RE = re.compile(
    r"^(?P<indent>\s*)alpha_values\s*=\s*\[i/100\s+for\s+i\s+in\s+range\(0,\s*101\)\].*$",
    re.MULTILINE,
)
PROB_SOLVE_RE = re.compile(r"^(?P<indent>\s*)prob\.solve\(\)\s*$", re.MULTILINE)
RESULTS_APPEND_RE = re.compile(r"^(?P<indent>\s*)results\.append\(\{\s*$", re.MULTILINE)


def _format_alpha_assignment(alphas: Iterable[float]) -> str:
    rendered = ", ".join(f"{float(alpha):.2f}" for alpha in alphas)
    return f"alpha_values = [{rendered}]"


def _solver_expr(solver_name: str) -> str:
    if solver_name == "highs":
        return "pulp.HiGHS(msg=False)"
    if solver_name == "cbc":
        return "pulp.PULP_CBC_CMD(msg=False)"
    raise ValueError(f"Unsupported solver: {solver_name}")


def _rewrite_bestshot_source(source: str, config: NotebookRunConfig, alphas: list[float], solver_name: str) -> str:
    rewritten = _rewrite_source(source, config)
    rewritten = ALPHA_ASSIGN_RE.sub(_format_alpha_assignment(alphas), rewritten)

    solve_replacement = (
        "{indent}solver = {solver}\n"
        "{indent}solve_status_code = prob.solve(solver)\n"
        "{indent}solve_status = pulp.LpStatus.get(prob.status, str(prob.status))"
    ).format(indent=r"\g<indent>", solver=_solver_expr(solver_name))
    rewritten = PROB_SOLVE_RE.sub(solve_replacement, rewritten)

    results_replacement = (
        "{indent}results.append({{\n"
        "{indent}    'Solve Status': solve_status,\n"
        "{indent}    'Solve Status Code': solve_status_code,"
    ).format(indent=r"\g<indent>")
    rewritten = RESULTS_APPEND_RE.sub(results_replacement, rewritten)
    return rewritten


def _execute_notebook_bestshot(
    notebook: Path,
    data_dir: Path,
    generated_dir: Path,
    alphas: list[float],
    solver_name: str,
) -> dict[str, object]:
    raw = json.loads(notebook.read_text())
    namespace: dict[str, object] = {"__name__": "__main__"}

    import pandas as pd  # local import to mirror legacy runner behavior

    pd.options.mode.copy_on_write = False
    namespace["pd"] = pd

    config = NotebookRunConfig(
        notebook=notebook,
        data_dir=data_dir,
        generated_dir=generated_dir,
        use_cbc=(solver_name == "cbc"),
    )
    generated_dir.mkdir(parents=True, exist_ok=True)

    for idx, cell in enumerate(raw.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue

        rewritten = _rewrite_bestshot_source(source, config, alphas, solver_name)
        try:
            parsed = ast.parse(rewritten, mode="exec")
        except SyntaxError:
            parsed = None

        if (
            parsed is not None
            and len(parsed.body) == 1
            and isinstance(parsed.body[0], ast.Expr)
            and isinstance(parsed.body[0].value, ast.Name)
            and parsed.body[0].value.id not in namespace
        ):
            continue

        exec(compile(rewritten, f"{notebook.name}:cell_{idx}", "exec"), namespace, namespace)
    return namespace


def _summarize_raw_results(raw: pd.DataFrame) -> pd.DataFrame:
    expected = ["Alpha", "Objective Nitrogen", "Objective Water", "Solve Status", "Solve Status Code"]
    missing = [column for column in expected if column not in raw.columns]
    if missing:
        raise RuntimeError(f"Notebook output is missing expected columns: {missing}")

    frame = raw[expected].copy()
    frame["Alpha"] = pd.to_numeric(frame["Alpha"], errors="coerce").round(4)
    frame["Objective Nitrogen"] = pd.to_numeric(frame["Objective Nitrogen"], errors="coerce")
    frame["Objective Water"] = pd.to_numeric(frame["Objective Water"], errors="coerce")
    frame["Solve Status"] = frame["Solve Status"].astype(str)
    frame["Solve Status Code"] = pd.to_numeric(frame["Solve Status Code"], errors="coerce")

    summary = (
        frame.groupby("Alpha", as_index=False)
        .agg(
            rows=("Alpha", "size"),
            objective_nitrogen=("Objective Nitrogen", "first"),
            objective_water=("Objective Water", "first"),
            solve_status=("Solve Status", "first"),
            solve_status_code=("Solve Status Code", "first"),
            objective_nitrogen_nunique=("Objective Nitrogen", pd.Series.nunique),
            objective_water_nunique=("Objective Water", pd.Series.nunique),
            solve_status_nunique=("Solve Status", pd.Series.nunique),
        )
        .sort_values("Alpha")
        .reset_index(drop=True)
    )
    summary["is_optimal"] = summary["solve_status"].eq("Optimal")
    summary["is_consistent"] = (
        summary["objective_nitrogen_nunique"].eq(1)
        & summary["objective_water_nunique"].eq(1)
        & summary["solve_status_nunique"].eq(1)
    )
    summary["is_valid"] = summary["is_optimal"] & summary["is_consistent"]
    return summary[SUMMARY_COLUMNS].copy()


def _run_season(
    season: str,
    notebook_name: str,
    layout: RepoLayout,
    alphas: list[float],
    solver_name: str,
    target_dir: Path,
) -> pd.DataFrame:
    data_dir = extract_archive_if_needed(layout.root).resolve()
    notebook = (layout.root / notebook_name).resolve()
    namespace = _execute_notebook_bestshot(
        notebook=notebook,
        data_dir=data_dir,
        generated_dir=layout.generated_dir.resolve(),
        alphas=alphas,
        solver_name=solver_name,
    )
    raw = namespace.get("df_results")
    if not isinstance(raw, pd.DataFrame):
        raise RuntimeError(f"{notebook_name} did not expose a df_results DataFrame.")
    summary = _summarize_raw_results(raw)
    return summary.assign(season=season)


def build_figure2a_bestshot(
    layout: RepoLayout | None = None,
    alphas: list[float] | None = None,
    solver_name: str = "highs",
) -> dict[str, pd.DataFrame]:
    active_layout = layout or default_layout()
    active_alphas = [round(float(alpha), 4) for alpha in (alphas or DEFAULT_ALPHAS)]

    season_summaries: dict[str, pd.DataFrame] = {}
    for season, notebook_name in SEASON_NOTEBOOKS.items():
        season_summaries[season] = _run_season(
            season=season,
            notebook_name=notebook_name,
            layout=active_layout,
            alphas=active_alphas,
            solver_name=solver_name,
            target_dir=active_layout.outputs_dir / "generated" / "figure2a_bestshot",
        )

    kharif = season_summaries["kharif"].drop(columns=["season"])
    rabi = season_summaries["rabi"].drop(columns=["season"])
    combined = kharif.merge(rabi, on="Alpha", suffixes=("_kharif", "_rabi"), how="inner")
    combined["objective_nitrogen"] = combined["objective_nitrogen_kharif"] + combined["objective_nitrogen_rabi"]
    combined["objective_water"] = combined["objective_water_kharif"] + combined["objective_water_rabi"]
    combined["nitrogen_mt"] = combined["objective_nitrogen"] / 1e9
    combined["water_bcm"] = combined["objective_water"] / 1e9
    combined["is_valid"] = combined["is_valid_kharif"] & combined["is_valid_rabi"]
    combined["valid_reason"] = "valid"
    combined.loc[~combined["is_optimal_kharif"], "valid_reason"] = "kharif_not_optimal"
    combined.loc[~combined["is_optimal_rabi"], "valid_reason"] = "rabi_not_optimal"
    combined.loc[
        combined["is_optimal_kharif"] & ~combined["is_consistent_kharif"],
        "valid_reason",
    ] = "kharif_inconsistent"
    combined.loc[
        combined["is_optimal_rabi"] & ~combined["is_consistent_rabi"],
        "valid_reason",
    ] = "rabi_inconsistent"
    combined = combined.sort_values("Alpha").reset_index(drop=True)
    return {"kharif": season_summaries["kharif"], "rabi": season_summaries["rabi"], "combined": combined}


def _plot_bestshot(frame: pd.DataFrame, target_dir: Path) -> dict[str, Path]:
    valid = frame[frame["is_valid"]].copy()
    invalid = frame[~frame["is_valid"]].copy()

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    cmap = plt.get_cmap("viridis")

    if not invalid.empty:
        ax.scatter(
            invalid["nitrogen_mt"],
            invalid["water_bcm"],
            color="#b3b3b3",
            marker="x",
            s=42,
            linewidths=1.0,
            label="Excluded (non-optimal/inconsistent)",
            zorder=2,
        )

    for row in valid.itertuples(index=False):
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
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        deduped: dict[str, object] = {}
        for handle, label in zip(handles, labels, strict=False):
            deduped.setdefault(label, handle)
        ax.legend(
            deduped.values(),
            deduped.keys(),
            loc="upper right",
            frameon=True,
            facecolor="white",
            edgecolor="#c8c8c8",
        )
    fig.tight_layout()

    png_path = target_dir / "figure2a_bestshot.png"
    pdf_path = target_dir / "figure2a_bestshot.pdf"
    fig.savefig(png_path, dpi=600)
    fig.savefig(pdf_path)
    plt.close(fig)
    return {"figure2a_bestshot_png": png_path, "figure2a_bestshot_pdf": pdf_path}


def _status_counts(frame: pd.DataFrame) -> list[str]:
    counts = frame["solve_status"].value_counts(dropna=False)
    return [f"- `{status}`: {count}" for status, count in counts.items()]


def _write_summary(
    results: dict[str, pd.DataFrame],
    target_dir: Path,
    solver_name: str,
    alphas: list[float],
) -> Path:
    kharif = results["kharif"]
    rabi = results["rabi"]
    combined = results["combined"]
    valid = combined[combined["is_valid"]].copy()

    lines = [
        "# Figure 2(a) best-shot reconstruction",
        "",
        "This reconstruction follows the reference-paper definition of Fig. 2(a):",
        "the weighted multi-objective sweep is executed separately for kharif and rabi,",
        "solver status is recorded for each alpha, and the all-season frontier is formed by",
        "summing national nitrogen surplus and water demand across the two seasons.",
        "",
        f"Solver: `{solver_name}`",
        f"Alpha count: {len(alphas)}",
        f"Alpha range: {min(alphas):.2f} to {max(alphas):.2f}",
        "",
        "Season status counts:",
        "Kharif:",
        *_status_counts(kharif),
        "Rabi:",
        *_status_counts(rabi),
        "",
        "Consistency checks:",
        f"- kharif valid alphas: {int(kharif['is_valid'].sum())}/{len(kharif)}",
        f"- rabi valid alphas: {int(rabi['is_valid'].sum())}/{len(rabi)}",
        f"- combined valid alphas: {int(valid.shape[0])}/{len(combined)}",
    ]

    if not valid.empty:
        first = valid.iloc[0]
        last = valid.iloc[-1]
        lines.extend(
            [
                "",
                "Combined valid frontier endpoints:",
                f"- alpha={first['Alpha']:.2f}: nitrogen={first['objective_nitrogen']:.6e}, water={first['objective_water']:.6e}",
                f"- alpha={last['Alpha']:.2f}: nitrogen={last['objective_nitrogen']:.6e}, water={last['objective_water']:.6e}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "No scientifically admissible combined frontier was obtained from the current code/data",
                "under this status-gated reconstruction. Any paper-facing redraw would therefore require",
                "either recovery of the original season Pareto outputs or a method-level reformulation.",
            ]
        )

    lines.extend(
        [
            "",
            "Method note:",
            "The earlier notebook-based draft reproduction averaged kharif and rabi objective values by alpha.",
            "This best-shot export instead uses kharif+rabi sums because the paper methods describe",
            "Fig. 2(a) in terms of total national water demand and nitrogen surplus for combined seasons.",
        ]
    )

    summary_path = target_dir / "figure2a_bestshot_summary.md"
    summary_path.write_text("\n".join(lines) + "\n")
    return summary_path


def export_figure2a_bestshot(
    output_dir: Path | None = None,
    layout: RepoLayout | None = None,
    alphas: list[float] | None = None,
    solver_name: str = "highs",
) -> dict[str, Path]:
    active_layout = layout or default_layout()
    active_alphas = [round(float(alpha), 4) for alpha in (alphas or DEFAULT_ALPHAS)]
    target_dir = ensure_directory(output_dir or active_layout.outputs_dir / "generated" / "figure2a_bestshot")

    results = build_figure2a_bestshot(layout=active_layout, alphas=active_alphas, solver_name=solver_name)
    written = {
        "kharif_by_alpha_csv": write_csv(results["kharif"], target_dir / "kharif_by_alpha.csv"),
        "rabi_by_alpha_csv": write_csv(results["rabi"], target_dir / "rabi_by_alpha.csv"),
        "combined_by_alpha_csv": write_csv(results["combined"], target_dir / "combined_by_alpha.csv"),
    }
    written.update(_plot_bestshot(results["combined"], target_dir))
    written["summary_md"] = _write_summary(results, target_dir, solver_name=solver_name, alphas=active_alphas)
    return written
