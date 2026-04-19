from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from .config import RepoLayout, default_layout


def strip_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns.astype(str)
    keep = ~(cols.str.startswith("Unnamed") | (cols == ""))
    return df.loc[:, keep].copy()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _iter_candidate_paths(filename: str, layout: RepoLayout) -> list[Path]:
    candidate = Path(filename)
    if candidate.is_absolute():
        return [candidate]

    results: list[Path] = []
    for root in layout.search_dirs:
        results.append(root / filename)
        results.append(root / candidate.name)
    return results


def _read_from_archive(filename: str, layout: RepoLayout, **kwargs) -> pd.DataFrame:
    if not layout.archive.exists():
        raise FileNotFoundError(filename)

    candidate = Path(filename)
    member_candidates = [
        filename.replace("\\", "/"),
        candidate.name,
        f"code_data/{candidate.name}",
        f"generated/{candidate.name}",
        f"outputs/generated/{candidate.name}",
    ]

    with ZipFile(layout.archive) as archive:
        members = {member.lower(): member for member in archive.namelist()}
        for member_name in member_candidates:
            normalized = member_name.lower()
            if normalized in members:
                with archive.open(members[normalized]) as handle:
                    return pd.read_csv(handle, **kwargs)

    raise FileNotFoundError(filename)


def read_repo_csv(filename: str, layout: RepoLayout | None = None, **kwargs) -> pd.DataFrame:
    active_layout = layout or default_layout()
    for path in _iter_candidate_paths(filename, active_layout):
        if path.exists():
            return pd.read_csv(path, **kwargs)
    return _read_from_archive(filename, active_layout, **kwargs)


def read_generated_csv(filename: str, layout: RepoLayout | None = None, **kwargs) -> pd.DataFrame:
    active_layout = layout or default_layout()
    generated_candidates = [
        filename,
        f"generated/{Path(filename).name}",
        f"outputs/generated/{Path(filename).name}",
        f"outputs/{Path(filename).name}",
    ]
    last_error: FileNotFoundError | None = None
    for candidate in generated_candidates:
        try:
            return read_repo_csv(candidate, layout=active_layout, **kwargs)
        except FileNotFoundError as exc:
            last_error = exc
    raise last_error or FileNotFoundError(filename)


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    ensure_directory(path.parent)
    df.to_csv(path, index=False)
    return path


def prepare_trade_flows(
    raw_filename: str,
    avg_filename: str,
    layout: RepoLayout | None = None,
) -> pd.DataFrame:
    active_layout = layout or default_layout()
    try:
        trade = read_repo_csv(raw_filename, layout=active_layout)
    except FileNotFoundError:
        trade = read_repo_csv(avg_filename, layout=active_layout)

    trade = strip_unnamed_columns(trade)

    for column in ("source", "target"):
        if column in trade.columns:
            trade[column] = trade[column].astype(str).str.title()

    year_columns = [str(year) for year in range(2020, 2008, -1) if str(year) in trade.columns]
    for column in ("2019", "2020"):
        if column in trade.columns:
            trade[column] = pd.to_numeric(trade[column], errors="coerce") * 10

    if {"2018", "2017", "2016"}.issubset(trade.columns):
        averaged = trade[["2018", "2017", "2016"]].apply(pd.to_numeric, errors="coerce")
        trade["avg_trade_qt_2017"] = averaged.mean(axis=1)
    elif "avg_trade_qtl" in trade.columns:
        trade["avg_trade_qt_2017"] = pd.to_numeric(trade["avg_trade_qtl"], errors="coerce")
    elif year_columns:
        averaged = trade[year_columns].apply(pd.to_numeric, errors="coerce")
        trade["avg_trade_qt_2017"] = averaged.mean(axis=1)
    else:
        raise KeyError(
            f"Could not find yearly trade columns or avg_trade_qtl in {raw_filename} / {avg_filename}."
        )

    drop_columns = {
        "ID",
        "source_ab",
        "target_ab",
        "con",
        "source_id",
        "target_id",
        "avg_trade_qtl",
        *year_columns,
    }
    trade = trade.drop(columns=[col for col in drop_columns if col in trade.columns], errors="ignore")
    return trade[["target", "source", "avg_trade_qt_2017"]].copy()
