# Invoked by build_material_library.py --audit-blend
# Scans materials for pink textures, unsupported nodes, disconnected shaders,
# and expensive settings.

import json
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy

rules = data.get("audit_rules") or {}
unsupported = set(rules.get("unsupported_nodes") or [])
expensive = rules.get("expensive_settings") or {}
pink_thresh = rules.get("pink_rgb_threshold") or [0.9, 0.0, 0.9]
findings = []


def is_pink(col):
    if not col or len(col) < 3:
        return False
    r, g, b = float(col[0]), float(col[1]), float(col[2])
    return r >= pink_thresh[0] and g <= 0.15 and b >= pink_thresh[2]


for mat in bpy.data.materials:
    if not mat.use_nodes or not mat.node_tree:
        findings.append(
            {
                "category": "disconnected_shaders",
                "material": mat.name,
                "detail": "Material has no node tree",
                "severity": "warn",
            }
        )
        continue

    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links

    output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
    if output is None:
        findings.append(
            {
                "category": "disconnected_shaders",
                "material": mat.name,
                "detail": "No Material Output node",
                "severity": "fail",
            }
        )
        continue

    surface_in = output.inputs.get("Surface")
    if surface_in and not surface_in.is_linked:
        findings.append(
            {
                "category": "disconnected_shaders",
                "material": mat.name,
                "detail": "Material Output Surface input disconnected",
                "severity": "fail",
            }
        )

    for node in nodes:
        bl_id = getattr(node, "bl_idname", "") or ""
        if bl_id in unsupported or node.type in {"SCRIPT"}:
            findings.append(
                {
                    "category": "unsupported_nodes",
                    "material": mat.name,
                    "detail": f"Unsupported or risky node: {bl_id or node.type}",
                    "severity": "fail",
                }
            )

        if node.type == "TEX_IMAGE":
            img = getattr(node, "image", None)
            if img is None:
                findings.append(
                    {
                        "category": "missing_images",
                        "material": mat.name,
                        "detail": f"Image Texture '{node.name}' has no image",
                        "severity": "fail",
                    }
                )
            else:
                fp = bpy.path.abspath(img.filepath) if img.filepath else ""
                if img.filepath and not Path(fp).is_file() and not img.packed_file:
                    findings.append(
                        {
                            "category": "missing_images",
                            "material": mat.name,
                            "detail": f"Missing file for '{img.name}': {img.filepath}",
                            "severity": "fail",
                        }
                    )
                # Pink / magenta missing-texture heuristic on generated solid colors
                if hasattr(img, "generated_color") and is_pink(img.generated_color):
                    findings.append(
                        {
                            "category": "pink_textures",
                            "material": mat.name,
                            "detail": f"Generated pink/magenta color on '{img.name}'",
                            "severity": "fail",
                        }
                    )
                if "pink" in (img.name or "").lower() or "missing" in (img.name or "").lower():
                    findings.append(
                        {
                            "category": "pink_textures",
                            "material": mat.name,
                            "detail": f"Suspicious placeholder name '{img.name}'",
                            "severity": "fail",
                        }
                    )

        if node.type == "BSDF_PRINCIPLED":
            # Expensive watches
            def sock(name, default=0.0):
                s = node.inputs.get(name)
                if s is None:
                    return default
                try:
                    return float(s.default_value)
                except (TypeError, ValueError):
                    return default

            trans = sock("Transmission Weight", sock("Transmission", 0.0))
            sss = sock("Subsurface Weight", sock("Subsurface", 0.0))
            sheen = sock("Sheen Weight", sock("Sheen", 0.0))
            if trans > 0.5:
                findings.append(
                    {
                        "category": "expensive_settings",
                        "material": mat.name,
                        "detail": f"High transmission ({trans:.2f}) on Principled",
                        "severity": "info",
                    }
                )
            sss_warn = float(expensive.get("max_sss_warn_if_eevee_and_scale_gt") or 1.0)
            if sss > 0.2:
                findings.append(
                    {
                        "category": "expensive_settings",
                        "material": mat.name,
                        "detail": f"Subsurface weight {sss:.2f} (EEVEE cost watch; scale warn>{sss_warn})",
                        "severity": "info",
                    }
                )
            sheen_lim = float(expensive.get("sheen_weight_warn_gt") or 0.85)
            if sheen > sheen_lim:
                findings.append(
                    {
                        "category": "expensive_settings",
                        "material": mat.name,
                        "detail": f"Sheen weight {sheen:.2f} > {sheen_lim}",
                        "severity": "info",
                    }
                )

        # Disconnected shader sockets that look like incomplete graphs
        if node.type in {"BSDF_PRINCIPLED", "MIX_SHADER", "ADD_SHADER", "EMISSION"}:
            for out in node.outputs:
                if out.is_linked:
                    break
            else:
                if node != output:
                    findings.append(
                        {
                            "category": "disconnected_shaders",
                            "material": mat.name,
                            "detail": f"Shader node '{node.name}' has no output links",
                            "severity": "warn",
                        }
                    )

# Scene-level expensive render settings
for scene in bpy.data.scenes:
    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        samples = getattr(eevee, "taa_render_samples", None) or getattr(
            eevee, "gi_diffuse_bounces", None
        )
        vol = getattr(eevee, "volumetric_samples", None)
        vol_warn = int(expensive.get("volumetric_high_samples_warn") or 64)
        if vol is not None and int(vol) >= vol_warn:
            findings.append(
                {
                    "category": "expensive_settings",
                    "material": f"SCENE:{scene.name}",
                    "detail": f"volumetric_samples={vol} >= {vol_warn}",
                    "severity": "info",
                }
            )

out = {
    "status": "ok",
    "findings": findings,
    "counts": {
        "missing_images": sum(1 for f in findings if f["category"] == "missing_images"),
        "pink_textures": sum(1 for f in findings if f["category"] == "pink_textures"),
        "unsupported_nodes": sum(1 for f in findings if f["category"] == "unsupported_nodes"),
        "disconnected_shaders": sum(
            1 for f in findings if f["category"] == "disconnected_shaders"
        ),
        "expensive_settings": sum(1 for f in findings if f["category"] == "expensive_settings"),
    },
}
Path(data["report_out"]).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"OINO_MATERIAL_AUDIT_OK {data['report_out']}")
print(json.dumps(out["counts"]))
