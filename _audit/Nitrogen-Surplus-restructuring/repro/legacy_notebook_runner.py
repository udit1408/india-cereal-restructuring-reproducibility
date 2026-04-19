from __future__ import annotations

import argparse
import ast
import json
import re
import traceback
from dataclasses import dataclass
from pathlib import Path

from .config import default_layout


WINDOWS_PATH_RE = re.compile(r'r"([A-Z]:\\[^"]+)"')
CHAINED_FILLNA_RE = re.compile(
    r"^(?P<indent>\s*)(?P<lhs>[A-Za-z_][A-Za-z0-9_]*\[[^\n]+?\])\.(?P<method>fillna|replace)\((?P<args>.*),\s*inplace=True\)\s*$",
    re.MULTILINE,
)
CALORIE_PER_KG_RE = re.compile(
    r"(?P<line>calorie_per_kg\s*=\s*\{cereal:\s*value\s*\*\s*10\s+for\s+cereal,\s*value\s+in\s+calorie_per_100g\.items\(\)\}[^\n]*\n)"
)


@dataclass(frozen=True)
class NotebookRunConfig:
    notebook: Path
    data_dir: Path
    generated_dir: Path
    use_cbc: bool = True


def extract_archive_if_needed(root: Path) -> Path:
    layout = default_layout(root)
    data_dir = layout.root / "code_data"

    import zipfile

    if not layout.archive.exists():
        return data_dir

    with zipfile.ZipFile(layout.archive) as archive:
        members = [member for member in archive.namelist() if member.startswith("code_data/") and not member.endswith("/")]
        if not data_dir.exists():
            archive.extractall(layout.root)
            return data_dir

        for member in members:
            target = layout.root / member
            if not target.exists():
                archive.extract(member, layout.root)
    return data_dir


def _rewrite_windows_path(path_text: str, generated_dir: Path, data_dir: Path) -> str:
    normalized = path_text.replace("\\", "/")
    name = Path(normalized).name
    generated_candidate = (generated_dir / name).resolve()
    data_candidate = (data_dir / name).resolve()
    if "code_final_cop" in normalized or normalized.endswith("/state_kharif_nitrogen.csv") or normalized.endswith("/state_rabi_nitrogen.csv"):
        if generated_candidate.exists():
            return str(generated_candidate)
        if data_candidate.exists():
            return str(data_candidate)
        return str(generated_candidate)
    if data_candidate.exists():
        return str(data_candidate)
    if generated_candidate.exists():
        return str(generated_candidate)
    return str(data_candidate)


def _rewrite_source(source: str, config: NotebookRunConfig) -> str:
    def replace_path(match: re.Match[str]) -> str:
        rewritten = _rewrite_windows_path(match.group(1), config.generated_dir, config.data_dir)
        return f'r"{rewritten}"'

    rewritten = WINDOWS_PATH_RE.sub(replace_path, source)
    if config.use_cbc:
        rewritten = re.sub(
            r'solver\s*=\s*pulp\.GLPK_CMD\(path=r"[^"]+"\)',
            'solver = pulp.PULP_CBC_CMD(msg=True)',
            rewritten,
        )

    def replace_chained_method(match: re.Match[str]) -> str:
        indent = match.group("indent")
        lhs = match.group("lhs")
        method = match.group("method")
        args = match.group("args")
        return f"{indent}{lhs} = {lhs}.{method}({args})"

    rewritten = CHAINED_FILLNA_RE.sub(replace_chained_method, rewritten)
    rewritten = CALORIE_PER_KG_RE.sub(r"\g<line>calorie_per_kg.setdefault('wheat', 3460)\n", rewritten, count=1)
    return rewritten


def execute_notebook(config: NotebookRunConfig) -> dict[str, object]:
    raw = json.loads(config.notebook.read_text())
    namespace: dict[str, object] = {"__name__": "__main__"}

    import pandas as pd

    pd.options.mode.copy_on_write = False
    namespace["pd"] = pd

    config.generated_dir.mkdir(parents=True, exist_ok=True)

    for idx, cell in enumerate(raw.get("cells", []), start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue

        rewritten = _rewrite_source(source, config)
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

        try:
            exec(compile(rewritten, f"{config.notebook.name}:cell_{idx}", "exec"), namespace, namespace)
        except Exception as exc:  # pragma: no cover - failure reporting path
            snippet = "\n".join(rewritten.splitlines()[:20])
            raise RuntimeError(
                f"Notebook execution failed in {config.notebook.name} at code cell {idx}.\n"
                f"First lines:\n{snippet}\n"
                f"Original error: {exc}"
            ) from exc
    return namespace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute a legacy notebook with local path and solver rewrites.")
    parser.add_argument("notebook", type=Path, help="Path to the .ipynb file to execute.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the parent of the repro package.",
    )
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=None,
        help="Directory where generated CSV outputs should be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root or default_layout().root
    data_dir = extract_archive_if_needed(root)
    generated_dir = args.generated_dir or (root / "generated")
    config = NotebookRunConfig(
        notebook=args.notebook.resolve(),
        data_dir=data_dir.resolve(),
        generated_dir=generated_dir.resolve(),
    )
    try:
        execute_notebook(config)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
