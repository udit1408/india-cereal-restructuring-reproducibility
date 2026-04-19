from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoLayout:
    root: Path
    archive: Path
    generated_dir: Path
    outputs_dir: Path
    search_dirs: tuple[Path, ...]


def default_layout(root: Path | None = None) -> RepoLayout:
    repo_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    generated_dir = repo_root / "generated"
    outputs_dir = repo_root / "outputs"
    search_dirs = (
        repo_root,
        repo_root / "code_data",
        repo_root / "data",
        repo_root / "data" / "processed",
        generated_dir,
        outputs_dir,
        outputs_dir / "generated",
    )
    return RepoLayout(
        root=repo_root,
        archive=repo_root / "code_data.zip",
        generated_dir=generated_dir,
        outputs_dir=outputs_dir,
        search_dirs=search_dirs,
    )
