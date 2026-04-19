from __future__ import annotations

import argparse
from pathlib import Path

from .figure2a_bestshot import export_figure2a_bestshot
from .figure2a_clean_rebuild import export_figure2a_clean_rebuild
from .figure2a_pipeline import export_figure2a
from .figure1_pipeline import export_figure1
from .trade_pipeline import export_trade_stage_inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reproducibility utilities for Nitrogen-Surplus-Focused-Restructuring."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    trade_stage = subparsers.add_parser(
        "trade-stage",
        help="Export normalized trade-stage inputs and derived tables outside the notebooks.",
    )
    trade_stage.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for generated CSV files. Defaults to outputs/generated/trade_stage.",
    )

    figure1 = subparsers.add_parser(
        "figure1",
        help="Export panel tables and a draft reproduction of manuscript Figure 1.",
    )
    figure1.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for Figure 1 artifacts. Defaults to outputs/generated/figure1.",
    )
    figure1.add_argument(
        "--boundary-file",
        type=Path,
        default=None,
        help="Optional path to the India district boundary topojson/geojson file.",
    )

    figure2a = subparsers.add_parser(
        "figure2a",
        help="Export season Pareto tables and a draft reproduction of manuscript Figure 2(a).",
    )
    figure2a.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for Figure 2(a) artifacts. Defaults to outputs/generated/figure2a.",
    )

    figure2a_bestshot = subparsers.add_parser(
        "figure2a-bestshot",
        help="Export a status-gated, manuscript-consistent reconstruction of Figure 2(a).",
    )
    figure2a_bestshot.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for best-shot Figure 2(a) artifacts. Defaults to outputs/generated/figure2a_bestshot.",
    )
    figure2a_bestshot.add_argument(
        "--solver",
        choices=("highs", "cbc"),
        default="highs",
        help="MILP solver used for the alpha sweep.",
    )
    figure2a_bestshot.add_argument(
        "--alphas",
        type=str,
        default=None,
        help="Comma-separated alpha values, e.g. 0,0.25,0.5,0.75,1. Defaults to 0.00..1.00 by 0.01.",
    )

    figure2a_clean = subparsers.add_parser(
        "figure2a-clean",
        help="Export a clean, state-district-consistent rebuild of Figure 2(a).",
    )
    figure2a_clean.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for clean Figure 2(a) artifacts. Defaults to outputs/generated/figure2a_clean_rebuild.",
    )
    figure2a_clean.add_argument(
        "--solver",
        choices=("highs", "cbc", "glpk"),
        default="highs",
        help="MILP solver used for the alpha sweep.",
    )
    figure2a_clean.add_argument(
        "--income-mode",
        choices=("profit", "msp", "legacy_mixed"),
        default="profit",
        help="State-level income floor used in the clean rebuild.",
    )
    figure2a_clean.add_argument(
        "--objective-mode",
        choices=("raw", "normalized"),
        default="raw",
        help="Objective aggregation used in the alpha sweep. `raw` matches the manuscript weighted sum.",
    )
    figure2a_clean.add_argument(
        "--alphas",
        type=str,
        default=None,
        help="Comma-separated alpha values, e.g. 0,0.25,0.5,0.75,1. Defaults to 0.00..1.00 by 0.01.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "trade-stage":
        written = export_trade_stage_inputs(output_dir=args.output)
        for name, path in written.items():
            print(f"{name}\t{path}")
        return 0

    if args.command == "figure1":
        written = export_figure1(output_dir=args.output, boundary_file=args.boundary_file)
        for name, path in written.items():
            print(f"{name}\t{path}")
        return 0

    if args.command == "figure2a":
        written = export_figure2a(output_dir=args.output)
        for name, path in written.items():
            print(f"{name}\t{path}")
        return 0

    if args.command == "figure2a-bestshot":
        alphas = None
        if args.alphas:
            alphas = [float(value.strip()) for value in args.alphas.split(",") if value.strip()]
        written = export_figure2a_bestshot(output_dir=args.output, solver_name=args.solver, alphas=alphas)
        for name, path in written.items():
            print(f"{name}\t{path}")
        return 0

    if args.command == "figure2a-clean":
        alphas = None
        if args.alphas:
            alphas = [float(value.strip()) for value in args.alphas.split(",") if value.strip()]
        written = export_figure2a_clean_rebuild(
            output_dir=args.output,
            solver_name=args.solver,
            income_mode=args.income_mode,
            objective_mode=args.objective_mode,
            alphas=alphas,
        )
        for name, path in written.items():
            print(f"{name}\t{path}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
