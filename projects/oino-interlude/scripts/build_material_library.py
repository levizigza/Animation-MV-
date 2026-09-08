"""Build Oino material library and run craft audits.

Materials: worn wood, wet stone, rust, oxidized metal, old paper, film,
black glass, monitor surfaces, translucent synthetic, cloth, ceramic,
skin, vine/leaf, water.

Audit: missing images, pink textures, unsupported nodes, disconnected
shaders, expensive settings.

Usage:
  python scripts/build_material_library.py
  python scripts/build_material_library.py --audit-blend path/to/scene.blend
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402
from show_config import load_show_config, resolve_render_engine  # noqa: E402

LIBRARY_JSON = DOCS_DIR / "material_library.json"
STATUS_MD = DOCS_DIR / "material_library.md"
AUDIT_MD = DOCS_DIR / "material_audit_report.md"
AUDIT_JSON = DOCS_DIR / "material_audit_report.json"
MARKERS_JSON = DOCS_DIR / "material_library_markers.json"
HELPER = SCRIPTS_DIR / "_blender_material_audit.py"

REQUIRED_MATERIAL_IDS = (
    "MAT_WornWood",
    "MAT_WetStone",
    "MAT_Rust",
    "MAT_OxidizedMetal",
    "MAT_OldPaper",
    "MAT_Film",
    "MAT_BlackGlass",
    "MAT_MonitorSurface",
    "MAT_TranslucentSynthetic",
    "MAT_Cloth",
    "MAT_Ceramic",
    "MAT_Skin",
    "MAT_VineLeaf",
    "MAT_Water",
)

REQUIRED_LABELS = (
    "worn wood",
    "wet stone",
    "rust",
    "oxidized metal",
    "old paper",
    "film",
    "black glass",
    "monitor surfaces",
    "translucent synthetic materials",
    "cloth",
    "ceramic",
    "skin",
    "vine and leaf",
    "water",
)


def load() -> dict[str, Any]:
    if not LIBRARY_JSON.is_file():
        raise FileNotFoundError(f"Missing {LIBRARY_JSON}")
    return json.loads(LIBRARY_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("allow_pink_placeholders") is not False:
        errors.append("policy.allow_pink_placeholders must be false")
    if policy.get("dionysian_not_every_surface_red") is not True:
        errors.append("policy.dionysian_not_every_surface_red must be true")

    rules = data.get("audit_rules") or {}
    for key in (
        "missing_images",
        "pink_textures",
        "disconnected_shaders",
    ):
        if rules.get(key) is not True:
            errors.append(f"audit_rules.{key} must be true")
    if not rules.get("unsupported_nodes"):
        errors.append("audit_rules.unsupported_nodes required")
    if not isinstance(rules.get("expensive_settings"), dict):
        errors.append("audit_rules.expensive_settings object required")

    mats = data.get("materials") or []
    ids = [m.get("id") for m in mats]
    labels = [(m.get("label") or "").strip().lower() for m in mats]
    if len(ids) != len(set(ids)):
        errors.append("material ids must be unique")
    for req in REQUIRED_MATERIAL_IDS:
        if req not in ids:
            errors.append(f"Missing material: {req}")
    for lab in REQUIRED_LABELS:
        if lab not in labels:
            errors.append(f"Missing material label: {lab}")
    if len(mats) != len(REQUIRED_MATERIAL_IDS):
        errors.append(
            f"Expected exactly {len(REQUIRED_MATERIAL_IDS)} materials, "
            f"found {len(mats)}"
        )

    for m in mats:
        mid = m.get("id", "?")
        pr = m.get("principled") or {}
        if "base_color" not in pr or "roughness" not in pr:
            errors.append(f"{mid}: principled.base_color and roughness required")
        if not isinstance(m.get("expected_images"), list):
            errors.append(f"{mid}: expected_images list required")
        if not (m.get("staging") or m.get("links") or m.get("note") is not None):
            if not m.get("links"):
                errors.append(f"{mid}: links required for craft continuity")

    return errors


def audit_filesystem(data: dict[str, Any]) -> dict[str, Any]:
    """Audit expected image paths and library-defined expensive watches."""
    findings: list[dict[str, Any]] = []
    missing_images: list[str] = []
    pink_risks: list[str] = []
    expensive: list[str] = []

    for m in data.get("materials") or []:
        mid = m["id"]
        for rel in m.get("expected_images") or []:
            path = PROJECT_ROOT / rel
            if not path.is_file():
                missing_images.append(rel)
                findings.append(
                    {
                        "severity": "missing_images",
                        "material": mid,
                        "path": rel,
                        "detail": "Expected image not on disk (placeholder ok until authored)",
                        "severity": "warn",
                    }
                )
            else:
                # crude pink-file probe: tiny solid magenta PNG often used as missing
                try:
                    raw = path.read_bytes()[:64]
                    # Not a full decode — flag known magenta placeholder filenames
                    if "pink" in path.name.lower() or "missing" in path.name.lower():
                        pink_risks.append(rel)
                        findings.append(
                            {
                                "severity": "pink_textures",
                                "material": mid,
                                "path": rel,
                                "detail": "Filename suggests pink/missing placeholder",
                                "severity": "fail",
                            }
                        )
                except OSError as exc:
                    findings.append(
                        {
                            "severity": "missing_images",
                            "material": mid,
                            "path": rel,
                            "detail": str(exc),
                            "severity": "warn",
                        }
                    )

        for watch in m.get("expensive_watch") or []:
            expensive.append(f"{mid}:{watch}")
            findings.append(
                {
                    "severity": "expensive_settings",
                    "material": mid,
                    "path": None,
                    "detail": f"Watch expensive feature in EEVEE: {watch}",
                    "severity": "info",
                }
            )

        # Library-level: transmission + high SSS flagged as expensive candidates
        pr = m.get("principled") or {}
        if float(pr.get("transmission_weight") or 0) > 0.5:
            findings.append(
                {
                    "severity": "expensive_settings",
                    "material": mid,
                    "path": None,
                    "detail": f"transmission_weight={pr.get('transmission_weight')} — keep samples modest in EEVEE",
                    "severity": "info",
                }
            )
        if float(pr.get("subsurface_weight") or 0) > 0.2:
            findings.append(
                {
                    "severity": "expensive_settings",
                    "material": mid,
                    "path": None,
                    "detail": f"subsurface_weight={pr.get('subsurface_weight')} — preview with low radius",
                    "severity": "info",
                }
            )

    # Unsupported / disconnected are blend-time; record pending if no blend audit
    findings.append(
        {
            "severity": "unsupported_nodes",
            "material": None,
            "path": None,
            "detail": "Pass --audit-blend <file.blend> to scan node trees",
            "severity": "info",
        }
    )
    findings.append(
        {
            "severity": "disconnected_shaders",
            "material": None,
            "path": None,
            "detail": "Pass --audit-blend <file.blend> to scan Material Output links",
            "severity": "info",
        }
    )

    return {
        "missing_images": missing_images,
        "pink_textures": pink_risks,
        "expensive_watches": expensive,
        "findings": findings,
        "blend_audit": None,
    }


def run_blend_audit(blend_path: Path, data: dict[str, Any], report: RunReport) -> dict[str, Any]:
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed — blend material audit deferred")
        return {"status": "deferred", "findings": []}
    if not blend_path.is_file():
        report.fail("audit-blend", f"Missing blend {blend_path}")
        return {"status": "failed", "findings": []}
    if not HELPER.is_file():
        report.fail("helper", f"Missing {HELPER}")
        return {"status": "failed", "findings": []}

    payload = {
        "blend": str(blend_path.resolve()),
        "audit_rules": data.get("audit_rules"),
        "material_ids": [m["id"] for m in data.get("materials") or []],
        "report_out": str((PROJECT_ROOT / "cache" / "material_blend_audit.json").resolve()),
    }
    payload_path = PROJECT_ROOT / "cache" / "material_blend_audit_payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [str(blender), "--background", str(blend_path), "--python", str(HELPER), "--", str(payload_path)],
        capture_output=True,
        text=True,
    )
    out_path = Path(payload["report_out"])
    if proc.returncode != 0 or not out_path.is_file():
        err = (proc.stderr or proc.stdout or "")[-2000:]
        report.fail("blend-audit", err or f"exit {proc.returncode}")
        return {"status": "failed", "findings": [], "detail": err}

    result = json.loads(out_path.read_text(encoding="utf-8"))
    report.mark("created", "cache/material_blend_audit.json")
    return {"status": "ok", **result}


def write_audit(
    data: dict[str, Any], audit: dict[str, Any], report: RunReport
) -> tuple[Path, Path]:
    AUDIT_JSON.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/material_audit_report.json")

    findings = audit.get("findings") or []
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        by_cat.setdefault(f.get("category") or "other", []).append(f)

    lines = [
        "# Material audit report — Oino (Interlude)",
        "",
        f"**Library:** `{data.get('system_id')}`  ",
        f"**Missing images:** {len(audit.get('missing_images') or [])}  ",
        f"**Pink texture flags:** {len(audit.get('pink_textures') or [])}  ",
        f"**Blend audit:** {(audit.get('blend_audit') or {}).get('status', 'not run')}",
        "",
        "## Categories",
        "",
    ]
    for cat in (
        "missing_images",
        "pink_textures",
        "unsupported_nodes",
        "disconnected_shaders",
        "expensive_settings",
        "other",
    ):
        items = by_cat.get(cat) or []
        lines.append(f"### {cat} ({len(items)})")
        lines.append("")
        if not items:
            lines.append("_None._")
            lines.append("")
            continue
        lines.append("| Severity | Material | Detail |")
        lines.append("|----------|----------|--------|")
        for it in items:
            lines.append(
                f"| `{it.get('severity')}` | `{it.get('material') or '—'}` | "
                f"{it.get('detail')} |"
            )
        lines.append("")

    blend = audit.get("blend_audit") or {}
    if blend.get("findings"):
        lines += ["## Blend node findings", ""]
        for it in blend["findings"]:
            lines.append(
                f"- `{it.get('severity')}` / `{it.get('material')}`: {it.get('detail')}"
            )
        lines.append("")

    lines += [
        "## Rebuild",
        "",
        "```text",
        "python scripts/build_material_library.py",
        "python scripts/build_material_library.py --audit-blend scenes/SCN_08_TABLE_ROOM.blend",
        "```",
        "",
    ]
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/material_audit_report.md")
    return AUDIT_MD, AUDIT_JSON


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = [
        {
            "name": m["id"],
            "label": m.get("label"),
            "category": m.get("category"),
            "links": m.get("links") or [],
            "expected_images": m.get("expected_images") or [],
        }
        for m in data.get("materials") or []
    ]
    out = {
        "schema_version": 1,
        "system_id": data.get("system_id"),
        "editable": True,
        "allow_pink_placeholders": False,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/material_library_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], audit: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    lines = [
        "# Material library — Oino (Interlude)",
        "",
        f"**System:** `{data.get('system_id')}`  ",
        f"**Engine target:** `{policy.get('engine_target')}`  ",
        f"**Pink placeholders allowed:** `{policy.get('allow_pink_placeholders')}`  ",
        f"**Dionysian not every surface red:** `{policy.get('dionysian_not_every_surface_red')}`",
        "",
        "## Audit summary",
        "",
        f"- Missing images: **{len(audit.get('missing_images') or [])}** "
        "(expected until textures are authored)",
        f"- Pink texture flags: **{len(audit.get('pink_textures') or [])}**",
        f"- Expensive watches: **{len(audit.get('expensive_watches') or [])}**",
        "",
        "## Materials",
        "",
        "| Id | Label | Roughness | Images expected | Missing |",
        "|----|-------|-----------|-----------------|---------|",
    ]
    missing_set = set(audit.get("missing_images") or [])
    for m in data.get("materials") or []:
        pr = m.get("principled") or {}
        exp = m.get("expected_images") or []
        miss = sum(1 for p in exp if p in missing_set)
        lines.append(
            f"| `{m['id']}` | {m.get('label')} | {pr.get('roughness')} | "
            f"{len(exp)} | {miss} |"
        )

    lines += ["", "## Material recipes", ""]
    for m in data.get("materials") or []:
        pr = m.get("principled") or {}
        lines += [
            f"### `{m['id']}` — {m.get('label')}",
            "",
            f"- **Category:** {m.get('category')}",
            f"- **Base color:** `{pr.get('base_color')}`",
            f"- **Roughness / metallic:** {pr.get('roughness')} / {pr.get('metallic', 0)}",
            f"- **Links:** " + ", ".join(f"`{x}`" for x in (m.get("links") or [])),
        ]
        if m.get("note"):
            lines.append(f"- **Note:** {m['note']}")
        if exp := m.get("expected_images"):
            lines.append("- **Expected images:**")
            for p in exp:
                status = "missing" if p in missing_set else "present"
                lines.append(f"  - `{p}` ({status})")
        lines.append("")

    lines += [
        "## Rebuild",
        "",
        "```text",
        "python scripts/build_material_library.py",
        "```",
        "",
        "Audit detail: [`material_audit_report.md`](material_audit_report.md)",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/material_library.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Oino material library + audit")
    parser.add_argument(
        "--audit-blend",
        type=str,
        default=None,
        help="Optional .blend path for node-tree audit",
    )
    args = parser.parse_args()

    report = RunReport(script="build_material_library", seed=20261210)
    try:
        data = load()
        report.mark("reused", "docs/material_library.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("brief", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    audit = audit_filesystem(data)
    if args.audit_blend:
        blend_result = run_blend_audit(Path(args.audit_blend), data, report)
        audit["blend_audit"] = blend_result
        for f in blend_result.get("findings") or []:
            audit.setdefault("findings", []).append(f)
            if f.get("severity") == "fail":
                report.fail(
                    f.get("category") or "blend",
                    f"{f.get('material')}: {f.get('detail')}",
                )

    n_missing = len(audit.get("missing_images") or [])
    n_pink = len(audit.get("pink_textures") or [])
    report.note(f"Audit: missing_images={n_missing} pink={n_pink}")

    write_markers(data, report)
    write_audit(data, audit, report)
    write_status(data, audit, report)
    report.note(
        "14 materials catalogued; pink placeholders forbidden; "
        "Dionysian colour not every surface"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} materials={len(data['materials'])} "
        f"missing_images={n_missing} pink={n_pink}"
    )
    # Missing images are expected until authored — do not fail the build
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
