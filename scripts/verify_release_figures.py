#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "generated" / "release_figure_sync"
OUT_JSON = OUT_DIR / "release_figure_sync_report.json"
OUT_MD = OUT_DIR / "release_figure_sync_report.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sync_one(name: str, source: Path, targets: list[Path]) -> dict[str, object]:
    if not source.exists():
        raise FileNotFoundError(f"Missing canonical figure for {name}: {source}")

    source_sha = sha256(source)
    source_size = source.stat().st_size
    target_rows: list[dict[str, object]] = []

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target_sha = sha256(target)
        target_size = target.stat().st_size
        matched = source_sha == target_sha and source_size == target_size
        if not matched:
            raise RuntimeError(f"{name}: target does not match source after copy: {target}")
        target_rows.append(
            {
                "target": str(target),
                "target_sha256": target_sha,
                "target_size_bytes": target_size,
                "matches_source": matched,
            }
        )

    return {
        "figure": name,
        "canonical_source": str(source),
        "canonical_sha256": source_sha,
        "canonical_size_bytes": source_size,
        "targets": target_rows,
    }


def build_report() -> dict[str, object]:
    specs = [
        (
            "Figure 1",
            ROOT / "_audit" / "Nitrogen-Surplus-restructuring" / "outputs" / "generated" / "figure1" / "figure1_reproduced.pdf",
            [],
        ),
        (
            "Figure 2",
            ROOT / "figures" / "working_variants" / "figure2_main.pdf",
            [
                ROOT / "figures" / "manuscript_final" / "fig2_main_revision2.pdf",
            ],
        ),
        (
            "Figure 2 PNG",
            ROOT / "figures" / "working_variants" / "figure2_main.png",
            [ROOT / "figures" / "manuscript_final" / "fig2_main_revision2.png"],
        ),
        (
            "Figure 3",
            ROOT / "figures" / "working_variants" / "figure3_main.pdf",
            [
                ROOT / "figures" / "manuscript_final" / "fig3_main_revision2.pdf",
            ],
        ),
        (
            "Figure 3 PNG",
            ROOT / "figures" / "working_variants" / "figure3_main.png",
            [ROOT / "figures" / "manuscript_final" / "fig3_main_revision2.png"],
        ),
    ]

    records = [sync_one(name, source, targets) for name, source, targets in specs]
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "records": records,
    }


def write_markdown(report: dict[str, object]) -> None:
    lines = [
        "# Release Figure Verification",
        "",
        "The reproducibility workflow copies canonical regenerated figure outputs into the",
        "public release figure targets bundled in the repository and verifies exact byte-level equality",
        "by SHA-256 and file size.",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
    ]
    for record in report["records"]:
        lines.append(f"## {record['figure']}")
        lines.append("")
        lines.append(f"- Canonical source: `{record['canonical_source']}`")
        lines.append(f"- Canonical SHA-256: `{record['canonical_sha256']}`")
        lines.append(f"- Canonical size (bytes): `{record['canonical_size_bytes']}`")
        for target in record["targets"]:
            lines.append(f"- Target: `{target['target']}`")
            lines.append(f"  - SHA-256: `{target['target_sha256']}`")
            lines.append(f"  - Size (bytes): `{target['target_size_bytes']}`")
            lines.append(f"  - Exact match: `{target['matches_source']}`")
        lines.append("")
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report)
    print(f"json: {OUT_JSON}")
    print(f"markdown: {OUT_MD}")
    for record in report["records"]:
        for target in record["targets"]:
            print(f"{record['figure']}\t{target['target']}\tmatch={target['matches_source']}")


if __name__ == "__main__":
    main()
