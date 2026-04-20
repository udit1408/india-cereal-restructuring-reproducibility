#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "submission_assets" / "audited_html_report"
ASSET_DIR = OUT_DIR / "assets"
MANIFEST_PATH = OUT_DIR / "repro_manifest.json"
HTML_PATH = OUT_DIR / "index.html"
RUN_CONTEXT_PATH = OUT_DIR / "run_context.json"


def relpath(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_record(label: str, path: Path, category: str, kind: str, *, preview_name: str | None = None) -> dict[str, object]:
    exists = path.exists()
    record: dict[str, object] = {
        "label": label,
        "category": category,
        "kind": kind,
        "path": relpath(path),
        "exists": exists,
    }
    if exists:
        stat = path.stat()
        record.update(
            {
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "sha256": sha256(path),
            }
        )
    if preview_name is not None:
        record["preview_name"] = preview_name
    return record


def copy_preview(src: Path, name: str) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    dst = ASSET_DIR / name
    shutil.copy2(src, dst)
    return dst


def load_run_context() -> dict[str, object]:
    if RUN_CONTEXT_PATH.exists():
        return json.loads(RUN_CONTEXT_PATH.read_text(encoding="utf-8"))
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "unknown",
        "runner": "unknown",
    }


def build_manifest() -> dict[str, object]:
    preview_specs = [
        ("Figure 1 reproduced render", ROOT / "_audit" / "Nitrogen-Surplus-restructuring" / "outputs" / "generated" / "figure1" / "figure1_reproduced.png", "main_figures", "png", "figure1_reproduced.png"),
        ("Figure 2 primary realized-price composite", ROOT / "figures" / "manuscript_final" / "fig2_main_revision2.png", "main_figures", "png", "fig2_main_revision2.png"),
        ("Figure 3 primary realized-price composite", ROOT / "figures" / "manuscript_final" / "fig3_main_revision2.png", "main_figures", "png", "fig3_main_revision2.png"),
        ("SI revenue robustness", ROOT / "figures" / "manuscript_final" / "si_revenue_benchmark_robustness.png", "si_figures", "png", "si_revenue_benchmark_robustness.png"),
        ("SI Figure 2a frontier envelope", ROOT / "figures" / "manuscript_final" / "si_figure2a_frontier_bootstrap.png", "si_figures", "png", "si_figure2a_frontier_bootstrap.png"),
    ]
    copied_previews: dict[str, str] = {}
    for _label, src, _category, _kind, preview_name in preview_specs:
        if src.exists():
            copied_previews[str(src)] = str(copy_preview(src, preview_name))

    main_outputs = [
        path_record("Figure 1 reproduced PDF", ROOT / "_audit" / "Nitrogen-Surplus-restructuring" / "outputs" / "generated" / "figure1" / "figure1_reproduced.pdf", "main_figures", "pdf"),
        path_record("Figure 2 primary realized-price composite PDF", ROOT / "figures" / "manuscript_final" / "fig2_main_revision2.pdf", "main_figures", "pdf"),
        path_record("Figure 2 primary realized-price composite PNG", ROOT / "figures" / "manuscript_final" / "fig2_main_revision2.png", "main_figures", "png", preview_name="fig2_main_revision2.png"),
        path_record("Figure 2a realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure2_main_panel_a.pdf", "main_figures", "pdf"),
        path_record("Figure 2b realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure2_main_panel_b.pdf", "main_figures", "pdf"),
        path_record("Figure 2c realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure2_main_panel_c.pdf", "main_figures", "pdf"),
        path_record("Figure 2d realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure2_main_panel_d.pdf", "main_figures", "pdf"),
        path_record("Figure 3a realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure3_main_panel_a.pdf", "main_figures", "pdf"),
        path_record("Figure 3b realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure3_main_panel_b.pdf", "main_figures", "pdf"),
        path_record("Figure 3c realized-price panel PDF", ROOT / "figures" / "working_variants" / "figure3_main_panel_c.pdf", "main_figures", "pdf"),
        path_record("Figure 3 primary realized-price composite PDF", ROOT / "figures" / "manuscript_final" / "fig3_main_revision2.pdf", "main_figures", "pdf"),
    ]

    si_outputs = [
        path_record("SI revenue robustness PDF", ROOT / "figures" / "manuscript_final" / "si_revenue_benchmark_robustness.pdf", "si_figures", "pdf", preview_name="si_revenue_benchmark_robustness.png"),
        path_record("SI revenue endpoint sensitivity PDF", ROOT / "figures" / "manuscript_final" / "si_revenue_benchmark_endpoint_sensitivity.pdf", "si_figures", "pdf"),
        path_record("SI revenue-profit sensitivity PDF", ROOT / "figures" / "manuscript_final" / "si_revenue_profit_sensitivity.pdf", "si_figures", "pdf"),
        path_record("SI Figure 2a frontier bootstrap PDF", ROOT / "figures" / "manuscript_final" / "si_figure2a_frontier_bootstrap.pdf", "si_figures", "pdf", preview_name="si_figure2a_frontier_bootstrap.png"),
        path_record("SI seasonal substitution audit PDF", ROOT / "figures" / "manuscript_final" / "si_s21_seasonal_substitution_audit.pdf", "si_figures", "pdf"),
    ]

    source_data = [
        path_record("Source Data workbook", ROOT / "submission_assets" / "source_data" / "Source Data.xlsx", "source_data", "xlsx"),
        path_record("Source Data zip", ROOT / "submission_assets" / "source_data" / "Source_Data_package.zip", "source_data", "zip"),
        path_record("Source Data README", ROOT / "submission_assets" / "source_data" / "README.md", "source_data", "md"),
    ]

    audits = [
        path_record("Figure 1 reproduction summary", ROOT / "_audit" / "Nitrogen-Surplus-restructuring" / "outputs" / "generated" / "figure1" / "figure1_reproduction_summary.md", "audit_notes", "md"),
        path_record("Figure 2 cap-variant audit", ROOT / "data" / "generated" / "figure2_cap_variant_audit.md", "audit_notes", "md"),
        path_record("Figure 2 legacy-faithful audit", ROOT / "data" / "generated" / "figure2_legacy_faithful_audit.md", "audit_notes", "md"),
        path_record("Release-figure verification report (Markdown)", ROOT / "data" / "generated" / "release_figure_sync" / "release_figure_sync_report.md", "audit_notes", "md"),
        path_record("Release-figure verification report (JSON)", ROOT / "data" / "generated" / "release_figure_sync" / "release_figure_sync_report.json", "audit_notes", "json"),
    ]

    workflow_files = [
        path_record("Container Dockerfile", ROOT / "container" / "Dockerfile", "workflow", "txt"),
        path_record("Container requirements", ROOT / "container" / "requirements.txt", "workflow", "txt"),
        path_record("Container entrypoint", ROOT / "container" / "entrypoint.sh", "workflow", "txt"),
        path_record("Final code README", ROOT / "code_final" / "README.md", "workflow", "md"),
        path_record("Final code manifest", ROOT / "code_final" / "FINAL_CODE_MANIFEST.md", "workflow", "md"),
        path_record("Method notation map", ROOT / "code_final" / "METHOD_NOTATION_MAP.md", "workflow", "md"),
        path_record("Final batch runner", ROOT / "code_final" / "run_final_revision2_batch.sh", "workflow", "txt"),
        path_record("Final Docker runner", ROOT / "code_final" / "run_final_revision2_container.sh", "workflow", "txt"),
        path_record("Docker runner wrapper", ROOT / "scripts" / "docker_run_audited_revision2.sh", "workflow", "txt"),
        path_record("Audited batch runner", ROOT / "scripts" / "run_audited_revision2_batch.sh", "workflow", "txt"),
        path_record("HTML report generator", ROOT / "scripts" / "generate_audited_html_report.py", "workflow", "txt"),
        path_record("Release-figure verifier", ROOT / "scripts" / "verify_release_figures.py", "workflow", "txt"),
    ]

    run_context = load_run_context()
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "root": ".",
        "run_context": run_context,
        "previews": [
            {
                "label": label,
                "source_path": relpath(src),
                "copied_preview": relpath(Path(copied_previews[str(src)])) if str(src) in copied_previews else None,
                "category": category,
                "kind": kind,
            }
            for label, src, category, kind, _preview_name in preview_specs
        ],
        "sections": {
            "main_outputs": main_outputs,
            "si_outputs": si_outputs,
            "source_data": source_data,
            "audits": audits,
            "workflow_files": workflow_files,
        },
    }


def status_badge(exists: bool) -> str:
    color = "#138d3c" if exists else "#b42318"
    text = "present" if exists else "missing"
    return f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:{color};color:white;font-size:12px">{text}</span>'


def table_rows(records: list[dict[str, object]]) -> str:
    rows = []
    for record in records:
        path = Path(str(record["path"]))
        link = html.escape(path.name)
        if record["exists"]:
            href = relative_from_report(path)
            link = f'<a href="{href}">{html.escape(path.name)}</a>'
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(record['label']))}</td>"
            f"<td>{status_badge(bool(record['exists']))}</td>"
            f"<td>{link}</td>"
            f"<td>{html.escape(record.get('kind', ''))}</td>"
            f"<td>{html.escape(str(record.get('size_bytes', '')))}</td>"
            f"<td><code>{html.escape(str(record.get('sha256', ''))[:16])}</code></td>"
            "</tr>"
        )
    return "\n".join(rows)


def relative_from_report(path: Path) -> str:
    if not path.is_absolute():
        return quote(Path("../..").joinpath(path).as_posix())
    return quote(path.relative_to(OUT_DIR).as_posix()) if path.is_relative_to(OUT_DIR) else quote(Path("../..").joinpath(path.relative_to(ROOT)).as_posix())


def build_html(manifest: dict[str, object]) -> str:
    previews = []
    for preview in manifest["previews"]:
        copied = preview.get("copied_preview")
        if not copied:
            continue
        copied_path = Path(str(copied))
        previews.append(
            f"""
            <div class="card">
              <div class="card-title">{html.escape(str(preview['label']))}</div>
              <img src="{relative_from_report(copied_path)}" alt="{html.escape(str(preview['label']))}">
            </div>
            """
        )

    run_context = manifest["run_context"]
    sections = manifest["sections"]
    latest_log = OUT_DIR / str(run_context.get("log_file", ""))
    log_link = ""
    if latest_log.exists():
        log_link = f'<p><a href="{relative_from_report(latest_log)}">Latest container/batch log</a></p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audited Reproducibility Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      margin: 0;
      background: #ffffff;
      color: #111827;
      font-size: 16px;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 28px 24px 56px;
    }}
    h1, h2 {{
      margin: 0 0 14px;
      font-weight: 650;
    }}
    p {{
      line-height: 1.6;
      margin: 0 0 12px;
    }}
    .band {{
      background: white;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 18px;
      box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    .card {{
      background: white;
      border: 1px solid #dde3eb;
      border-radius: 8px;
      padding: 12px;
    }}
    .card-title {{
      font-weight: 600;
      margin-bottom: 8px;
    }}
    img {{
      width: 100%;
      height: auto;
      border: 1px solid #dde3eb;
      border-radius: 6px;
      background: white;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      background: white;
    }}
    th, td {{
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid #e7ebf1;
      vertical-align: top;
    }}
    th {{
      background: #f6f8fb;
      font-weight: 600;
    }}
    code {{
      font-family: Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    .mono {{
      font-family: Menlo, Consolas, monospace;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <main>
    <section class="band">
      <h1>Audited Reproducibility Report</h1>
      <p>This HTML report tracks the current audited workflow, generated figure assets, the source-data package, and the containerized rerun path.</p>
      <p class="mono">Generated UTC: {html.escape(str(manifest['generated_utc']))}</p>
      <p class="mono">Runner: {html.escape(str(run_context.get('runner', 'unknown')))}</p>
      <p class="mono">Run mode: {html.escape(str(run_context.get('mode', 'unknown')))}</p>
      <p class="mono">Repository root: {html.escape(str(manifest['root']))}</p>
      {log_link}
      <p><a href="repro_manifest.json">Machine-readable manifest</a></p>
    </section>

    <section class="band">
      <h2>Preview Panels</h2>
      <div class="grid">
        {''.join(previews)}
      </div>
    </section>

    <section class="band">
      <h2>Main Outputs</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>File</th><th>Type</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{table_rows(sections['main_outputs'])}</tbody>
      </table>
    </section>

    <section class="band">
      <h2>Supplementary Outputs</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>File</th><th>Type</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{table_rows(sections['si_outputs'])}</tbody>
      </table>
    </section>

    <section class="band">
      <h2>Source Data Package</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>File</th><th>Type</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{table_rows(sections['source_data'])}</tbody>
      </table>
    </section>

    <section class="band">
      <h2>Audit Notes</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>File</th><th>Type</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{table_rows(sections['audits'])}</tbody>
      </table>
    </section>

    <section class="band">
      <h2>Workflow Files</h2>
      <table>
        <thead><tr><th>Artifact</th><th>Status</th><th>File</th><th>Type</th><th>Size</th><th>SHA-256</th></tr></thead>
        <tbody>{table_rows(sections['workflow_files'])}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    HTML_PATH.write_text(build_html(manifest), encoding="utf-8")
    print(f"html: {HTML_PATH}")
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
